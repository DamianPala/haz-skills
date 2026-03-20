---
name: change-summary
description: "Analyze code changes between git refs (tags, branches, commits). Runs a Python script for deterministic file classification and metrics, then interprets changes from user perspective. Multi-source: commit messages, MR/PR descriptions, per-file diffs. Produces structured change list with types (feat/fix/breaking), confidence levels, and type-based classification. Supports GitHub (gh) and GitLab (glab). Triggers: 'analyze changes', 'what changed', 'summarize changes', 'change summary', 'co sie zmienilo', 'podsumuj zmiany', 'przeanalizuj zmiany', 'explain this diff', 'describe changes since'. Also useful before release, merge, or PR creation. DO NOT TRIGGER for code review (quality/security), commit message generation, or CI/CD."
version: 2.1.0
---

# Change Summary

## Rules

- Net diff is source of truth, commit messages are hints only. When uncertain, lower confidence, never fabricate
- Every change must trace to real file paths in the diff. Zero hallucinations
- Correct base ref is critical. Wrong base = wrong diff = wrong output. Detect from context: release uses last tag, PR uses target branch, fork PR uses upstream remote (not origin)
- Blocking prompt (standalone mode): find and use a user-prompting tool (AskUserQuestion, ask_user, prompt). Plain text only if none exists

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **standalone** (default) | user asks about changes | Run full pipeline, present output, ask for feedback |
| **sub-skill** | invoked by another skill via Skill tool | Run full pipeline, return YAML. No user interaction |

**Sub-skill invocation:** `Skill tool: 'change-summary'. Analyze changes between <base> and <head>.`
Returns `changes.yaml` content after Step 9.

## Workflow

```
1. Collect       (Python)  → diff-N.txt + prompts + file→commits map
2. Interpret     (acpc)    → raw YAML per chunk (type, description, detail, files)
3. Post-process  (Python)  → schema fix, category fill, commits fill, cross-check
4. Orphan detect (Python)  → find uncovered files from diff
5. Orphan fill   (acpc)    → interpret only orphan files → orphan YAML
6. Verify        (acpc)    → semantic check (covers both main + orphan items)
7. Merge         (Python)  → concat chunks + orphan chunks, sort, bump
8. Dedup         (inline)  → read merged YAML, deduplicate near-duplicates
9. Deliver
```


### Step 1: Collect (Python)

**Prerequisite:** Your working directory must be inside the target git repository. If the repo is not cloned, clone it first (`git clone <url>`). Then `cd` into the repo before running the script.

```bash
uv run --project <skill-dir>/scripts change-summary [base] [head] --output <workdir> [options]
```

The script detects the repository root from the current working directory. It reads per-repo submodule config from `AGENTS.md` if present (see `references/repo-config.md`).

Uses `git diff base..head --submodule=diff` (net diff, not per-commit). The diff is the source of truth for what changed between two points.

Always use `--output` pointing to a workdir (e.g. `/tmp/change-summary/`). The script writes:
- `diff-N.txt` (one file per chunk, chunked by file boundaries, sorted: source, test, config, docs)
- `file-commits-map.yaml` (mapping of file paths to commit hashes that touched them)
- `interpret-prompt.md` (dispatch: tells you how to run acpc per chunk)
- `interpret-chunk-N-prompt.md` (per-chunk worker prompts with baked-in rules)
- `verify-prompt.md` (dispatch: tells you how to run acpc per chunk)
- `verify-chunk-N-prompt.md` (per-chunk worker prompts with baked-in rules)
- `dedup-prompt.md` (only for multi-chunk: post-merge deduplication prompt)

File headers include hunk count when a file has multiple change regions: `## File: 'path' [file-type, status, +N/-M, K change regions]`. This helps the interpreter notice all changes, not just the largest.

Each chunk is prepended with a commit log sidebar (`git log --oneline base..head`). These are hints only, not structure. LLM may use them for intent but must not trust them as facts.

Token budget: 100k per chunk. If a single file exceeds the budget, it gets its own chunk.

| Argument | When to use |
|----------|-------------|
| `[base] [head]` | Explicit range (tags, branches, commits). Both optional |
| `--since YYYY-MM-DD` | Date-based range instead of ref range |
| `--author "Name"` | Filter commits by author |
| `--output dir` | Output directory (always use) |
| `--max-tokens N` | Token budget per chunk (default: 100000) |
| `--agent NAME` | acpc agent for dispatch. Use the same agent platform you're running on |

If base ref is not provided, the script auto-detects from the latest tag. If no tags exist, analyzes the entire history.

**Choosing the correct base ref is critical.** Wrong base = wrong diff = wrong output. Common scenarios:

| Scenario | Base | Head | How to detect |
|----------|------|------|---------------|
| Release | last tag (auto-detected) | `HEAD` | `git describe --tags --abbrev=0` |
| PR (same repo) | target branch (`main`) | PR branch | `git log --oneline main..HEAD` |
| PR (fork → upstream) | `upstream/main` | PR branch | `git remote -v` shows fork; use upstream remote |
| Date range | omit base | `HEAD` | use `--since` instead |

For PRs from forks: always use the upstream remote as base, not origin. `git remote -v` shows which remote points to the upstream repo.

**Error handling:**
- Script exits non-zero → show error, don't proceed
- No commits in range → script exits with code 2. Report "No changes found"
- Git ref not found → script exits with clear error message

### Step 2: Interpret (acpc)

Read `<workdir>/interpret-prompt.md` and follow its instructions. For single chunk it dispatches one acpc agent, for multi-chunk it dispatches N agents in parallel. Never interpret diffs inline, always dispatch to acpc.

The LLM reads the file-based net diff and identifies logical changes from code. It outputs:

| Field | Purpose | Consumer |
|-------|---------|----------|
| `type` | Change type (feat/fix/refactor/...) | classification |
| `description` | End-user perspective, no technical jargon | release notes, changelog |
| `detail` | Technical specifics, component names, mechanisms | PR descriptions, code review |
| `files` | Affected file paths | PR descriptions, navigation |
| `confidence` | Interpretation quality signal (high/medium/low) | verification, human review |
| `note` | Reason for non-high confidence | verification, human review |
| `breaking` | Breaking change flag | release notes, changelog |
| `migration` | Migration instructions if breaking | release notes, changelog |

The LLM does **not** output `commits` or `category`. Those are filled deterministically by Python in Step 3.

Verify that YAML output was created before proceeding.

### Step 3: Post-process (Python)

```bash
uv run --project <skill-dir>/scripts change-summary validate <workdir>
```

Deterministic post-processing of raw LLM output:
1. **Schema validation** - required fields, valid types, auto-fix defaults
2. **Category fill** - maps `type` to Keep a Changelog section (feat→Added, fix→Fixed, ...)
3. **Commits fill** - maps `files` to commit hashes via `file-commits-map.yaml`
4. **File coverage cross-check** - every file in the diff must have YAML coverage

MISSING_FILE issues from cross-check are expected and will be handled by Steps 4-5 (orphan detection/fill). Do not fix them manually. Only fix EXTRA_FILE issues (files in YAML but not in diff) by removing incorrect paths from the YAML entries, then re-run validate.

### Step 4: Orphan detect (Python)

```bash
uv run --project <skill-dir>/scripts change-summary orphan <workdir>
```

Deterministic detection of files in the diff that are not covered by any YAML entry's `files` list. This catches files the interpreter missed (common in large chunks where the LLM loses attention).

If no orphans found: skip Step 5, proceed to Step 6.

If orphans found, the script writes:
- `orphan-diff-N.txt` (diff sections for orphan files only, per chunk)
- `orphan-fill-chunk-N-prompt.md` (per-chunk fill prompts)
- `orphan-fill-prompt.md` (dispatch: tells you how to run acpc per chunk)

### Step 5: Orphan fill (acpc)

Read `<workdir>/orphan-fill-prompt.md` and follow its instructions. Dispatches acpc agents to interpret only the orphan file diffs. Each agent writes `orphan-changes-chunk-N.yaml`.

After completion, merge orphan entries back into their parent chunk YAMLs and re-validate:

```bash
uv run --project <skill-dir>/scripts change-summary orphan --merge-back <workdir>
uv run --project <skill-dir>/scripts change-summary validate <workdir>
```

The `--merge-back` command appends orphan entries to `changes-chunk-N.yaml` so that verify (Step 6) sees all items.

### Step 6: Verify (acpc)

Read `<workdir>/verify-prompt.md` and follow its instructions. Always dispatch to acpc, never verify inline. The verifier must have fresh context to avoid confirmation bias.

Semantic checks only:
- Missing logical changes (diff shows something, YAML doesn't cover it)
- Hallucinations (YAML describes something not in the diff)
- Type correctness (does the type match what the code actually does)
- Description quality (does the description accurately reflect the change)

Does **not** check: schema, category mapping, file coverage (Python did that in Step 3). One pass, no re-runs.

After reading per-chunk results (`verify-chunk-N-result.txt`), write the aggregated verdict to `<workdir>/verify-result.txt`: "PASS" if all chunks passed, or collected issues (one per line) if any failed.

**If verify reports issues:** apply simple fixes (type changes, confidence adjustments) directly to the chunk YAML. For complex issues (missing logical changes, hallucinations), note them but proceed to Step 7. Do not re-run verify.

### Step 7: Merge (Python)

```bash
uv run --project <skill-dir>/scripts change-summary merge <workdir>
```

Deterministic merge: collects all `changes-chunk-*.yaml` files, performs structural dedup (same commit + similar description), sorts, computes bump. Writes `<workdir>/changes.yaml`.

Note: orphan entries were already merged into chunk YAMLs in Step 5, so merge sees them as part of the regular chunks.

No collapsing needed. Net diff naturally produces net delta, so there are no add-then-revert or add-then-fix sequences to collapse.

### Step 8: Dedup (inline, multi-chunk only)

For multi-chunk runs: read `<workdir>/dedup-prompt.md` and follow its instructions. This is an inline step (you do it yourself, not via acpc) because the input is small (merged YAML, not raw diff).

The dedup step reads `changes.yaml`, merges near-duplicate entries that were created by independent chunk interpreters seeing different files of the same feature, and writes back to `changes.yaml`.

For single-chunk runs: skip this step (no cross-chunk duplicates possible).

### Step 9: Deliver

**Standalone:** present `changes.yaml` content to the user, ask "Does this look correct? Anything to add, remove, or adjust?"

**Sub-skill:** return `changes.yaml` content, no user interaction.

## Constraints

- Net diff is source of truth. Commit messages are hints only. When they conflict, the diff wins
- Every change traces to real file paths in the diff. Zero hallucinations
- `confidence: high` only when the diff clearly shows the intent
- `category` must be a valid Keep a Changelog section. Filled by Python from type mapping, not by LLM
- `commits` filled by Python from file-commits-map, not by LLM
