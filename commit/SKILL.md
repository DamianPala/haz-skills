---
name: commit
description: "Generate Conventional Commit messages from staged changes. Analyzes diff, detects type/scope, links issues from branch name, suggests splitting large commits. Triggers: 'commit', 'commit this', 'commit all', 'skomituj', 'skomituj wszystko', 'commitnij', 'zrob commit', 'zrob commity'. DO NOT TRIGGER for PR creation, code review, or push operations."
---

# Commit

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **single** (default) | `commit`, `commit this`, `skomituj`, `commitnij`, `zrob commit` | One commit, confirm before executing |
| **batch** | `commit all`, `skomituj wszystko`, `zrob commity` | Plan all atomic commits, confirm once, execute all |
| **autonomous** | repo's AGENTS.md indicates autonomous commits | Full workflow, no confirmation |

## Workflow

### Step 1: Assess and stage

Run `git status --porcelain`, `git diff --cached --stat`, `git diff --stat`, `git branch --show-current`.

Group changes into logical atomic commits:

- Current staging coherent? Use it. Incomplete/mixed? Restage: `git reset HEAD <file>` to unstage, `git add <file>` to add
- Nothing staged? Stage first logical group. Multiple groups? Stage, commit, repeat
- Mixed changes in one file: `git add -p` for relevant hunks
- Always specific files (`git add <file>`), never `git add -A` or `git add .`

### Step 2: Analyze and generate

From `git diff --cached`, determine:

**Type** from diff content: `feat` (new files/exports/routes), `fix` (incorrect behavior), `refactor` (structural, no behavior change), `docs` (only .md/docs), `test` (only tests), `chore`/`ci`/`build` (config/CI/build), `perf` (performance), `style` (formatting only).

**Scope** from `--stat`: primary directory or module. Omit if changes span many areas.

**Subject**: imperative mood, lowercase, no period, ≤72 chars.

**Body**: skip for trivial changes (1-2 files, <30 lines). For 3+ files or 30-300 lines: explain WHY not WHAT, wrap at 72 chars. Over 300 lines: WHY + suggest splitting.

**Footer**: breaking change = `!` after type/scope + `BREAKING CHANGE: <description>`. Issue refs = scan branch name for `#\d+` or `[A-Z]+-\d+`, add `Refs #N` or `Fixes #N`.

### Step 3: Verify

**Grounding (mandatory):** Re-read `git diff --cached`.
- Every file/change in the message must be traceable to actual diff lines
- Type must match diff content, not assumed intent. When unsure, pick safer type
- Issue refs only from branch name or existing commits. Never invent
- Batch mode: each planned commit must map to real files in `git status`
- Can't determine WHY? Describe WHAT accurately instead of guessing

**Sanity:** Can't describe in one sentence, or unrelated changes mixed? Split (autonomous) or suggest splitting (interactive). Secrets in diff (.env, tokens, credentials, API keys)? Abort.

### Step 4: Present for review

**Autonomous mode:** Skip to Step 5.

**Single:** Show message, ask "Commit? (y/edit/cancel)".
**Batch:** Show full plan, ask "Execute all? (y/edit/cancel)".

If **edit**: write to `/tmp/commit-message.md`, tell user path, wait for confirmation, read back and validate CC format.

### Step 5: Commit and confirm

Use heredoc for multi-line messages. Omit empty body/footer (no double blank lines).

If pre-commit hooks modify files, re-stage (`git add -u`) and retry. Hooks fail on content: interactive = show error, let user decide; autonomous = fix, retry once, abort if still failing.

Output: commit hash (short), subject, files changed, insertions/deletions. Do NOT push.

## Rules

- Never `--no-verify`, never force push, never amend pushed commits without asking
- Never commit secrets or add AI attribution trailers (Co-Authored-By, etc.)
- Respect repo's commitlint/husky rules and AGENTS.md commit mode settings
- One logical change per commit
- WHY not WHAT ("support new auth provider" not "add import X"). No generic messages, no hallucinated changes
