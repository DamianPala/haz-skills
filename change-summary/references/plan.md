# change-summary: plan

## Baseline

Aktualny rozwój odnosi się do commita `df8cb23` (feat: rewrite skill with deterministic prompts) jako baseline. Porównania i ewaluacje robić względem tego punktu.

## Cel

Standalone skill do analizy zmian w kodzie. Produkuje ustrukturyzowaną listę zmian. Dwa tryby użycia:

1. **Standalone** - user woła `/change-summary` żeby zrozumieć co się zmieniło w repo/branchu/między tagami
2. **Sub-skill** - inne skille (release-create, merge-message, pr-create) odpalają go przez Skill tool

## Aktualny stan: gotowy, przetestowany

### Pipeline (6 kroków)

```
1. Collect    (Python)  → diff-N.txt + prompts
2. Interpret  (acpc)    → YAML per chunk    → validate <workdir>
3. Verify     (acpc)    → semantic check
4. Merge      (Python)  → single changes.yaml
5. Final eval (inline)  → fix issues
6. Deliver
```

### Python package (`scripts/`)

```
scripts/src/change_summary/
├── cli.py          subcommands: collect (default), merge, validate
├── models.py       FileChange, CommitData, ProjectContext, Summary, ChangeSummaryConfig
├── git_ops.py      run_git, collect_commits/files/diffs, submodule expansion (virtual commits)
├── classify.py     file categories, message quality, likely type, breaking flags
├── context.py      README, manifests (package.json/pyproject/Cargo/CMake), changelog, AGENTS.md config
├── mr_fetch.py     MR/PR descriptions via glab/gh API
├── format.py       plain text output: header, commits, files, skipped
├── chunk.py        token estimation, greedy chunking, file writing (diff-N.txt)
├── filter.py       lock/binary/generated file detection
├── prompts.py      generates interpret/verify prompts with baked-in paths, {agent} placeholder
├── validate.py     YAML schema fix + cross-check (validate_workdir combines both)
└── crosscheck.py   structural verification: commit hashes, file coverage, missing commits
```

172 tests passing, ruff clean.

### Prompt templates (`references/prompts/`)

| Template | Generuje | Konsument |
|----------|----------|-----------|
| `interpret-rules.md` | `interpret-prompt.md` (single) lub `interpret-chunk-N-prompt.md` (multi) | acpc worker |
| `interpret-orchestration.md` | `interpret-prompt.md` (multi only, dispatch instructions) | orchestrator LLM |
| `verify-rules.md` | `verify-prompt.md` (single) lub `verify-chunk-N-prompt.md` (multi) | acpc worker |
| `verify-orchestration.md` | `verify-prompt.md` (multi only, dispatch instructions) | orchestrator LLM |
| `final-eval-rules.md` | nie generowany, czytany raw z dysku | orchestrator LLM (Step 5) |

### Kluczowe decyzje architektoniczne

- **acpc dla chunk dispatch** - vendor-agnostic, działa na dowolnej głębokości Agent tool. `--agent` flag (claude/codex)
- **Deterministic prompt generation** - Python bake'uje paths/values do promptów. LLM czyta gotowy plik
- **Cross-check przed verify** - Python łapie structural errors (wrong commit, missing files), LLM verify skupia się na semantyce
- **Capture all, filter later** - skill łapie WSZYSTKIE typy zmian (test/ci/build/docs). Downstream (merge-message, changelog) decyduje co pokazać
- **Virtual commits** - submodule pointer changes rozwijane do per-commit diffów, konfigurowane per-repo w AGENTS.md

### E2E test results (2026-03-18)

| Test | Chunki | Zmiany | Czas | Cross-check | Verify |
|------|--------|--------|------|-------------|--------|
| 5.3.0..5.4.0 (single) | 1 (55KB) | 8 | ~5min | PASS (po fix) | PASS |
| 4.9.10..5.0.0 (multi) | 4 (60+748+172+324 KB) | 68 | 26min | 6 MISSING_FILE → fixed | 10 issues → fixed |

## Output format

### Skill output (YAML)

```yaml
# Change Summary: v1.1.0..v1.2.0
# Project: project-name
# Suggested bump: minor

changes:
  - type: feat
    category: Added
    description: End-user perspective description
    detail: Technical description for developers
    files: [src/module.c, src/module.h]
    commit: abc1234
    confidence: high

  - type: test
    category: Changed
    description: Unit tests added for validation logic
    detail: New test cases covering edge cases
    files: [tests/module_ut.c]
    commit: def5678
    confidence: high

skipped:
  - commit: aaa1111
    reason: merge commit
```

Typy: feat, fix, refactor, perf, docs, chore, revert, style, test, ci, build
Kategorie: Added, Changed, Fixed, Removed, Deprecated, Security
Mapping: feat→Added, fix→Fixed, refactor/perf→Changed, revert→Removed, reszta→Changed. Semantic override: deletion→Removed, deprecation→Deprecated, security→Security

## Integracja z innymi skillami

| Skill | Co robi z outputem |
|-------|-------------------|
| **release-create** | `category` → Keep a Changelog sekcje. `migration` dla breaking changes |
| **merge-message** | `type` + `description` → CC message body. Pomija test/ci/chore |
| **pr-create** | `description` + `category` → PR description |

Invocation: `Skill tool: 'change-summary'. Analyze changes between <base> and <head>.`

## Known issues / future work

### Chunking
- Chunk 2 w teście multi = 748KB (~187k tokenów) vs limit 80k. Przyczyna: commit `e55f481` (GUI refactor, 697KB diff) w submodule jest nierozbijaly (greedy chunker nie dzieli commitów). Rzadki edge case, zostawiamy
- Token estimate: `len(text) // 4`. Wystarczające w praktyce

### Pipeline
- Verify trwa ~9min na 4 chunki. Prawie tyle co interpret. Pole do optymalizacji
- Single commit branch: pełny pipeline i tak przechodzi (jeden commit może mieć wiele logicznych zmian)

### Planowane skille (downstream)
- **release-create** - Keep a Changelog + GitHub/GitLab release z changes.yaml
- **changelog** - generacja/update CHANGELOG.md

## Test repos

| Repo | Co testuje |
|------|-----------|
| dr203-recorder-fw | RC tagi, merge commits, submoduły, GitLab. Baseline dla E2E testów |
| trs-programmer-sw | Custom `[FEAT]`/`[FIX]`/`[DEV]`, GitLab |
| commitizen | Strict CC, duży range |
| got | Lazy commits, needs_analysis |
| openwhispr | Merge PRs, breaking changes |
| synthetic-test-repo | Mix: CC, WIP, custom prefix, merge, breaking |

## Research (archived)

Pełny research z PR-Agent, CodeRabbit, aider, Copilot, Sourcery, Diff-XYZ benchmark.

Zastosowane:
1. Plain text per-file diffs (PR-Agent, Copilot pattern)
2. Strip `@@` line numbers (LLMs bad at line numbers)
3. Token-aware chunking (PR-Agent compression strategy)
4. Diff dla każdego commita (nie ufamy commit messages)

Nie zastosowane (future):
- Dynamic context expansion do enclosing function/class (wymaga AST)
- Two-model pipeline: tani triaguje, drogi interpretuje (zbyt złożone)
- Semantic retrieval / embeddings (wymaga infrastruktury)
