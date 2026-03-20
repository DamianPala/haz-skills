---
name: pr-create
description: "Create and update Pull Requests with structured descriptions from git diff and commit history. Detects forks/upstream automatically, selects description pattern (pitch, problem/solution, standard) by change type. Supports GitHub (gh) and GitLab (glab). Triggers: 'create/open/write/make/update pr', 'submit to upstream', 'push for review', 'contribute back', 'create mr', 'zrob pr', 'otworz pr', 'zaktualizuj pr', 'wyslij do review', 'pull request', 'merge request'. Also trigger for fork-to-upstream submissions. DO NOT TRIGGER for commits, reviewing existing PRs, rebase, or cherry-pick."
---

# PR Create

## Rules

- Never force-push, never auto-merge, never auto-approve
- Never create PRs to main/master from another person's branch without asking
- Draft by default, ready only when explicitly requested
- No AI attribution trailers (Co-Authored-By, etc.)
- Use ALL commits since base, not just the latest
- PR template over default structure when template exists
- Summary = user/maintainer perspective (no file names, no implementation). Changes = reviewer perspective (files, architecture, details)
- Focus on intent and impact, not obvious code changes
- Specific test plans (`pytest -k test_auth`) not generic ("run the tests")
- Trivial changes get trivial descriptions, not 3 paragraphs
- Blocking prompt: find and use a user-prompting tool (AskUserQuestion, ask_user, prompt). Plain text only if none exists

## Platform detection

Run `scripts/detect-platform.py` from the skill directory. Returns JSON: `{"cli": "gh"|"glab", "host": "...", "method": "..."}`. Abort if detection fails (neither CLI authenticated).

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **create** (default) | "create", "open", "write", "make", "zrob", "otworz" | New PR, draft by default |
| **update** | "update", "refresh", "zaktualizuj", "popraw" | Edit existing PR description |

## Workflow

**Blocking prompt**: one per call, one question. Never batch multiple questions. Never embed a prompt inside longer output.

### Step 1: Validate state

- Current branch from `git branch --show-current`. Abort if on main/master/develop
- Base branch: check `branch.<name>.merge-base` git config, then remote default branch (`gh repo view` / `glab repo view` / `git remote show origin`), fallback to `main`
- Fork detection: `git remote get-url upstream 2>/dev/null`
  - If upstream exists: `git fetch upstream <base> --quiet` (if fetch fails, skip fork detection)
  - Then `git rev-list --count <base>..upstream/<base>`. If upstream ahead: effective_base = `upstream/<base>`
  - Otherwise (no upstream, fetch failed, or upstream even/behind): effective_base = `<base>`
- **Blocking prompt** (target + context):
  - If fork detected (upstream ahead): "Fork detected: <base> is N commits behind upstream/<base>. Looks like an external contribution to [upstream-owner/repo]. Correct? Any context to highlight for the maintainer? (external / internal)"
  - Otherwise: "Internal PR or external contribution? If external: any context to highlight? (impact, affected users, why it matters)"
  - User says internal → effective_base = local `<base>`, target = internal
  - User says external → keep effective_base (upstream if available), target = external
- Count commits ahead: `git rev-list --count <effective_base>..HEAD`. If 0, abort: "No commits ahead of <effective_base>"
- **Update mode**: find existing PR (`gh pr list --head <branch>` / `glab mr list --source-branch <branch>`). If none found: **Blocking prompt**: "No existing PR for this branch. Create a new one? (y/cancel)"

### Step 2: Gather context

Run in parallel (using effective_base from Step 1):

- `git diff --stat <effective_base>...HEAD` — changed files summary (file count, total lines)
- Commit count: already known from Step 1
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/pull_request_template.md`, `docs/pull_request_template.md`
- `git status --porcelain` — uncommitted changes

If uncommitted changes exist, warn: "You have uncommitted changes that won't be included in the PR."

**Complexity check** (from diff stat and commit count):

| Condition | Data source |
|-----------|-------------|
| >5 commits OR >500 changed lines | **change-summary** (sub-skill) |
| ≤5 commits AND ≤500 lines | **raw diff** (inline analysis) |

**change-summary path:** invoke via Skill tool with sub-skill mode:

```
Skill: 'change-summary'
Args: "Analyze changes between <effective_base> and HEAD. --platform <cli> --host <host>"
```

Pass `--platform` and `--host` from platform detection when available. Returns structured changes with types, descriptions (user-facing), details (technical), files, confidence, breaking flags, and migration info.

**Raw diff path** (below threshold or change-summary unavailable): gather directly:

- `git diff <effective_base>...HEAD` — full diff
- `git log --format='### %s%n%n%b' <effective_base>..HEAD` — commits with bodies

### Step 3: Analyze and generate

**Data source:** when change-summary was used (Step 2), its structured output is the primary input:
- `description` fields → Summary sections (user perspective, no jargon)
- `detail` + `files` fields → Changes sections (reviewer perspective, architecture)
- `type` distribution → PR type (dominant: most impactful, not most frequent)
- `breaking` + `migration` → Breaking changes section
- `confidence` → weight high-confidence changes in summary, mention low-confidence as "likely"

When raw diff was used, analyze directly from diff and commit messages as before.

**Title**: CC format, ≤70 chars. Type from change-summary's dominant type when available, otherwise from diff content: `feat` (new files/exports/routes), `fix` (incorrect behavior), `refactor` (structural, no behavior change), `docs` (only .md/docs), `test` (only tests), `chore`/`ci`/`build` (config/CI/build), `perf`, `style`. Scope from primary directory/module, omit if broad.

**Body**: If repo has a PR template (from Step 2), fill it in:
- Check applicable checkboxes (`- [x]`), leave others unchecked
- For sections that don't apply, write `N/A` rather than deleting
- For yes/no fields ("Security impact?", "Breaking change?"), answer from diff
- Keep the template's structure intact

Otherwise, select a description pattern:

| Type | Target | Pattern |
|------|--------|---------|
| feat | external | **Pitch** |
| fix, refactor, perf | any | **Problem → Solution** |
| everything else | any | **Standard** |

#### Pattern A: Pitch (feat + external)

Goal: convince the maintainer this PR is worth merging. Lead with value, not implementation.

```markdown
## Summary

<Value for users: what this adds, why it matters, proof of quality. No file names.>

## Changes

<Reviewer-facing: files, architecture, design decisions, alternatives.>

## Test plan

<Concrete commands and manual verification steps.>
```

Draft selling points yourself from the diff (new capabilities, performance gains, test coverage).

#### Pattern B: Problem → Solution (fix/refactor/perf)

Goal: show you understand the problem and the fix is deliberate, not accidental.

For **external** repos: frame Problem as impact (who's affected, how badly) not just technical detail. The Problem section is your pitch for why this deserves a merge.

```markdown
## Summary

<1-3 bullets: what was broken/suboptimal and what's fixed now.>

## Problem

<What went wrong, who's affected, reproduction steps. For external: emphasize user-facing impact.>

## Solution

<Approach, alternatives considered, why this over others.>

## Test plan

<Steps to verify the fix works and the original problem is gone.>
```

#### Pattern C: Standard (default)

For internal features, docs, tests, chore, CI, and anything that doesn't fit Pitch or Problem → Solution. Add sections from cross-pattern rules below when applicable.

```markdown
## Summary

<1-3 bullets: WHAT changed and WHY. Focus on the why, the diff shows the what.>

## Changes

<Non-trivial PRs only (>3 files or >100 lines). Approach, design decisions, alternatives. Skip for simple changes.>

## Test plan

<Checkboxes. Concrete commands, manual steps, or "Covered by existing tests".>
- [ ] `make test` passes
- [ ] Manual: verify X works as expected
```

**Cross-pattern rules** (apply to all patterns). Incorporate any context the user provided in Step 1.
- **Breaking changes**: add `## Breaking changes` when change-summary flags `breaking: true` or when diff modifies public APIs, configs, CLI flags, or interfaces. Use change-summary's `migration` field when available. What breaks + migration path
- **Not changed**: add `## Not changed` for large PRs (>300 lines) where scope is ambiguous. 1-2 absolute statements of what's out of scope. No qualifiers ("except", "aside from", "other than"). If something changed even slightly, it belongs in Changes, not here
- **Issue detection**: scan branch name and commit messages for `#\d+` or `[A-Z]+-\d+`. `Fixes` if context says fixes/closes/resolves, otherwise `Refs`
- **Scaling**: trivial (<30 lines) = Summary + Test plan only. Medium (30-300) = pattern-appropriate sections. Large (>300) = all sections. Over 1000 = suggest splitting

### Step 4: Verify

Re-read `git diff --stat <effective_base>...HEAD` and answer every question below. Verify internally, do not output the checklist.

1. Every file in diff stat traceable to the description?
2. Type matches diff content, not assumed intent?
3. Issue refs only from branch name or commit messages (none invented)?
4. Summary: zero file names, function names, acronyms, or internal jargon?
5. Summary matches the pattern's core question? (Pitch: "why merge this?" / Problem→Solution: "what broke and what's fixed?" / Standard: "what and why?")
6. Changes has the implementation detail that is NOT in Summary?
7. Not changed (if present): absolute claims only, no "except/aside from"?
8. No AI trailers (Co-Authored-By, etc.)?
9. No filler phrases ("comprehensive", "robust", "improves the codebase")?
10. No restating what the diff already shows ("Added import X to file Y")?
11. For **external** PRs: does Summary answer "why should a maintainer merge this?"?
12. For **fix/refactor** PRs: is Problem understandable without reading the code?
13. Changes section present only if >3 files or >100 lines?
14. Any section with a single bullet? Use plain text instead of a list.

If any answer is no, fix the description before proceeding. If high-quality CC commit messages exist, lean on them for the summary.

### Step 5: Present for review

Show title, base/branch info, and body:

```
Title: <type>(<scope>): <description>
Base: <effective_base> <- <branch> (<N> commits)
Target: <internal|external>

Body:
## Summary
- <what changed and why>

## Test plan
- [ ] <specific test command>
- [ ] Manual: <concrete verification step>
```

If repo has a test runner (`Makefile`, `package.json` test script, `pytest.ini`, `Cargo.toml`):
**Blocking prompt**: "Run tests before creating? (y/n)"

**Large PRs** (>300 lines diff): write body to a temp file (`tempfile.gettempdir() + '/pr-description.md'`), open for the user, show title, base/branch, target.
**Blocking prompt**: "Editing at [path]. (ready/cancel)"

**Small/medium PRs**: show body inline.
**Blocking prompt**: "Create PR? (y/edit/cancel)"
If **edit**: write to temp file, open for the user, wait for confirmation, read back.

To open a temp file for editing: `xdg-open` (Linux), `open` (macOS), `start` (Windows).

### Step 6: Create and confirm

Push branch if needed (`git push -u origin <branch>`). If remote ahead: `git push --force-with-lease` (never bare `--force`).

Create/update with CLI:
- Always `--draft` unless user explicitly said "ready"
- `gh`: pass body via `--body-file` with heredoc
- `glab`: pass `--target-branch <base>`

Output: PR/MR URL, status (draft/ready), base branch, commit count.

Never force-push. Never auto-merge. Draft by default. No AI trailers. Summary speaks user language, not code.
