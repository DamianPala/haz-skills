---
name: pr-create
description: "Create and update Pull Requests with structured descriptions from git diff and commit history. Supports GitHub (gh) and GitLab (glab). Triggers: 'create pr', 'create mr', 'write pr', 'make pr', 'open pr', 'update pr', 'zrob pr', 'otworz pr', 'zaktualizuj pr', 'pull request', 'merge request'. DO NOT TRIGGER for commit-only tasks or code review without PR creation."
---

# PR Create

## Rules

- Never force-push, never auto-merge, never auto-approve
- Never create PRs to main/master from another person's branch without asking
- Draft by default, ready only when explicitly requested
- No AI attribution trailers (Co-Authored-By, etc.)
- Use ALL commits since base, not just the latest
- PR template over default structure when template exists
- Focus on intent and impact, not obvious code changes
- Specific test plans (`pytest -k test_auth`) not generic ("run the tests")
- Trivial changes get trivial descriptions, not 3 paragraphs

Create or update Pull/Merge Requests with descriptions generated from diff and commit history.

## Platform detection

Run `scripts/detect-platform.py` from the skill directory. Returns JSON: `{"cli": "gh"|"glab", "host": "...", "method": "..."}`. Abort if detection fails (neither CLI authenticated).

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **create** (default) | "create", "open", "write", "make", "zrob", "otworz" | New PR, draft by default |
| **update** | "update", "refresh", "zaktualizuj", "popraw" | Edit existing PR description |

Default to **create** as **draft** when no explicit mode is given.

## Workflow

### Step 1: Validate state

- Current branch from `git branch --show-current`. Abort if on main/master/develop
- Base branch: check `branch.<name>.merge-base` git config, then remote default branch (`gh repo view` / `glab repo view` / `git remote show origin`), fallback to `main`
- Count commits ahead: `git rev-list --count <base>..HEAD`. If 0, abort: "No commits ahead of <base>"
- **Update mode**: find existing PR (`gh pr list --head <branch>` / `glab mr list --source-branch <branch>`). If none, offer to create instead

### Step 2: Gather context

Run in parallel:

- `git diff <base>...HEAD` — full diff
- `git log --format='### %s%n%n%b' <base>..HEAD` — commits with bodies
- `git diff --stat <base>...HEAD` — changed files summary
- PR template: `.github/PULL_REQUEST_TEMPLATE.md`, `.github/pull_request_template.md`, `docs/pull_request_template.md`
- `git status --porcelain` — uncommitted changes

If uncommitted changes exist, warn: "You have uncommitted changes that won't be included in the PR."

### Step 3: Analyze and generate

**Title**: CC format, ≤70 chars. Type from diff content: `feat` (new files/exports/routes), `fix` (incorrect behavior), `refactor` (structural, no behavior change), `docs` (only .md/docs), `test` (only tests), `chore`/`ci`/`build` (config/CI/build), `perf`, `style`. Scope from primary directory/module, omit if broad.

**Body**: If repo has a PR template (from Step 2), fill it in:
- Check applicable checkboxes (`- [x]`), leave others unchecked
- For sections that don't apply, write `N/A` rather than deleting
- For yes/no fields ("Security impact?", "Breaking change?"), answer from diff
- Keep the template's structure intact

Otherwise, use this structure:

```markdown
## Summary

<1-3 bullet points: WHAT changed and WHY. Focus on the why, the diff shows the what.>

## Changes

<Only for non-trivial PRs (>3 files or >100 lines). Brief description of the approach, design decisions, or alternatives considered. Skip for simple changes.>

## Breaking changes

<Only when PR modifies public APIs, configs, CLI flags, or interfaces. What breaks and how to migrate. Skip if nothing breaks.>

## Not changed

<Only for large PRs (>300 lines) where scope is ambiguous. 1-2 bullets clarifying what is explicitly out of scope. Skip for small/medium changes.>

## Issues

<Auto-detected from branch name and commit messages. Format: "Fixes #123", "Refs #456", "Closes PROJ-789". Omit section if none found.>

## Test plan

<Checklist with checkboxes. Concrete commands, manual steps, or "Covered by existing tests". Always include.>
- [ ] `make test` passes
- [ ] Manual: verify X works as expected
```

**Issue detection**: scan branch name and commit messages for `#\d+` or `[A-Z]+-\d+`. Use `Fixes` if context says fixes/closes/resolves, otherwise `Refs`.

**Scaling**: trivial (<30 lines): Summary + Test plan only. Medium (30-300 lines): add Changes. Large (>300 lines): all sections. Over 1000 lines: suggest splitting into smaller PRs.

### Step 4: Verify

**Grounding (mandatory):** Re-read `git diff --stat <base>...HEAD`.
- Every file/change mentioned in the description must be traceable to actual diff
- Type must match diff content, not assumed intent
- Issue refs only from branch name or commit messages. Never invent
- If high-quality CC commit messages exist, lean on them for the summary

**Sanity:** No AI attribution trailers (Co-Authored-By, etc.) in the body. No filler phrases ("This PR improves the codebase", "comprehensive changes"). No restating obvious code changes ("Added import X to file Y").

### Step 5: Present for review

Show title, base/branch info, and body:

```
Title: <type>(<scope>): <description>
Base: <base> ← <branch> (<N> commits)

Body:
## Summary
- <what changed and why>

## Test plan
- [ ] <specific test command>
- [ ] Manual: <concrete verification step>
```

If repo has a test runner (`Makefile`, `package.json` test script, `pytest.ini`, `Cargo.toml`), offer: "Run tests before creating?" Don't enforce.

Ask "Create PR? (y/edit/cancel)" — use the platform's confirmation tool if available (e.g., `AskUserQuestion`), otherwise present as text and wait for response.

If **edit**: write to a temp file (e.g., `tempfile.gettempdir() + '/pr-description.md'`), tell user path, wait for confirmation, read back.

### Step 6: Create and confirm

Push branch if needed (`git push -u origin <branch>`). If remote ahead: `git push --force-with-lease` (never bare `--force`).

Create/update with CLI:
- Always `--draft` unless user explicitly said "ready"
- `gh`: pass body via `--body-file` with heredoc
- `glab`: pass `--target-branch <base>`

Output: PR/MR URL, status (draft/ready), base branch, commit count.

Never force-push. Never auto-merge. Draft by default. No AI trailers.
