---
name: pr-create
description: "Create and update Pull Requests with structured descriptions generated from git diff and commit history. Supports GitHub (gh) and GitLab (glab). Triggers: $pr, $mr, 'create pr', 'create mr', 'write pr', 'make pr', 'open pr', 'update pr', 'zrob pr', 'otworz pr', 'zaktualizuj pr', 'pull request', 'merge request'. DO NOT TRIGGER for commit-only tasks or code review without PR creation."
---

# PR Create

Create or update Pull Requests / Merge Requests with AI-generated descriptions based on the actual diff and commit history.

## Prerequisites

- At least one of: `gh` CLI, `glab` CLI, or a GitHub/GitLab MCP server (e.g., `mcp__github`, `mcp__gitlab`)
- A git repo on a feature branch (not main/master). If not in a git repo, check if the user mentioned a repo path and `cd` into it.
- On Windows: use Git Bash or WSL for shell commands

## Platform detection

Run `scripts/detect-platform.py` from the skill directory. Returns JSON: `{"cli": "gh"|"glab", "host": "...", "method": "..."}`. If detection fails and a GitHub/GitLab MCP is available, use that instead.

## Modes

Detect mode from the user's message:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **create** (default) | "create", "open", "write", "make", "zrob", "otworz" | New PR |
| **update** | "update", "refresh", "zaktualizuj", "popraw" | Edit existing PR description |
| **draft** | add `--draft` if user says "draft" | Create as draft |

Default to **create** + **draft** when no explicit mode is given (safer default).

## Workflow

### Step 1: Validate state

```bash
# Current branch
BRANCH=$(git branch --show-current)

# Abort if on main/master/develop
# Abort if no commits ahead of base

# Detect base branch
BASE=$(git config "branch.${BRANCH}.merge-base" 2>/dev/null \
  || git config "branch.${BRANCH}.gh-merge-base" 2>/dev/null \
  || echo "")
if [ -z "$BASE" ]; then
  # Try default branch from remote
  BASE=$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null \
    || glab repo view --json default_branch --jq '.default_branch' 2>/dev/null \
    || git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p' \
    || echo "main")
fi

# Verify commits exist
AHEAD=$(git rev-list --count "${BASE}..HEAD")
# If 0, abort: "No commits ahead of ${BASE}. Nothing to PR."
```

For **update** mode, also check:
```bash
# Find existing PR for current branch
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null \
  || glab mr list --source-branch "$BRANCH" --json iid --jq '.[0].iid' 2>/dev/null)
# If empty, offer to create instead
```

### Step 2: Gather context

Run these in parallel:

```bash
# Full diff against base
git diff "${BASE}...HEAD"

# Commit log with bodies
git log --format='### %s%n%n%b' "${BASE}..HEAD"

# Changed files summary
git diff --stat "${BASE}...HEAD"

# Check for repo PR template
cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null \
  || cat .github/pull_request_template.md 2>/dev/null \
  || cat docs/pull_request_template.md 2>/dev/null \
  || echo ""

# Check for uncommitted changes
git status --porcelain
```

If there are uncommitted changes, warn the user: "You have uncommitted changes that won't be included in the PR. Commit or stash first?"

### Step 3: Analyze and generate

Based on the gathered context, generate the PR title and body.

**Title format:** Conventional Commits, under 70 characters.

```
<type>(<scope>): <short description>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `style`, `build`.

Detect type from the diff:
- New files/exports/routes/endpoints → `feat`
- Changes to existing logic that fix incorrect behavior → `fix`
- Structural changes without behavior change → `refactor`
- Only `.md`/docs files → `docs`
- Only test files → `test`
- Config/CI/build files only → `chore`/`ci`/`build`

Scope: derive from the primary directory or module affected. Omit if changes span many areas.

**Body structure:**

If the repo has a PR template (from Step 2), fill it in with the analyzed content. When filling templates:
- Check applicable checkboxes (`- [x]`), leave others unchecked
- For sections that don't apply, write `None` or `N/A` rather than deleting the section
- For yes/no fields (e.g., "Security impact?", "Breaking change?"), answer based on the diff
- Keep the template's structure intact so reviewers see a familiar format

Otherwise, use this structure:

```markdown
## Summary

<1-3 bullet points: WHAT changed and WHY. Focus on the why, the diff shows the what.>

## Changes

<Only for non-trivial PRs (>3 files or >100 lines). Brief description of the approach, design decisions, or alternatives considered. Skip for simple changes.>

## Breaking changes

<Only when PR modifies public APIs, configs, CLI flags, or interfaces. What breaks and how to migrate. Skip if nothing breaks.>

## Not changed

<Only for large PRs (>300 lines) where scope is ambiguous. 1-2 bullets clarifying what is explicitly out of scope, so reviewers don't waste time looking for it. Skip for small/medium changes.>

## Issues

<Auto-detected from branch name and commit messages. Format: "Fixes #123", "Refs #456", "Closes PROJ-789". Omit section if none found.>

## Test plan

<Checklist with checkboxes. Concrete commands, manual steps, or "Covered by existing tests". Always include.>
- [ ] `make test` passes
- [ ] Manual: verify X works as expected
```

**Issue detection patterns:**

Scan branch name and commit messages for:
- `#\d+` → GitHub/GitLab issue
- `[A-Z]+-\d+` → Jira/Linear style (e.g., PROJ-123)
- `fixes`, `closes`, `resolves` prefix → use `Fixes` keyword
- Otherwise → use `Refs`

**Scaling rules:**

| Diff size | Title | Body |
|-----------|-------|------|
| Trivial (<30 lines, 1-2 files) | type: description | Summary (1 bullet) + Test plan |
| Medium (30-300 lines) | type(scope): description | Summary + Changes + Test plan |
| Large (>300 lines) | type(scope): description | Summary + Changes + Breaking changes* + Not changed + Issues + Test plan |

### Step 4: Present for review

Before creating the PR, show the user the generated title and body:

```
Title: feat(auth): add SSO login via SAML

Body:
## Summary
- Add SAML-based SSO authentication flow for enterprise customers
- Integrate with existing session management, no breaking changes

## Test plan
- [ ] `make test` passes
- [ ] Manual: login via SSO on staging
```

If the repo has a test runner (e.g., `Makefile` with `test` target, `package.json` with `test` script, `pytest.ini`, `Cargo.toml`), suggest running tests: "Want to run tests before creating the PR?" Don't enforce, just offer.

Ask: "Create this PR? (y/edit/cancel)" or just proceed if the user said to create directly.

If the user picks **edit**: write the title and body to a temp file (e.g., `/tmp/pr-description.md`), tell them the path, and wait. Read the file back after they confirm they're done editing.

### Step 5: Create or update

Push the branch if needed (`git push -u origin "$BRANCH"`). If remote is ahead, use `git push --force-with-lease` (never bare `--force`).

Create or update using `gh pr create` / `glab mr create` (or `gh pr edit` / `glab mr update` for update mode). Key flags:
- Always pass `--draft` unless user explicitly said "ready"
- For `gh`: pass body via `--body-file -` with heredoc to avoid shell escaping issues
- For `glab`: pass `--target-branch "$BASE"`

### Step 6: Confirm

After creation/update, output:
- PR/MR URL (clickable)
- Status (draft/ready)
- Base branch
- Number of commits included

## Rules

- Never create PRs to main/master from another person's branch without asking
- Never force-push as part of PR creation
- Never auto-merge or auto-approve
- If the diff is huge (>1000 lines), suggest splitting into smaller PRs before generating
- Don't restate obvious code changes in the description ("Added import X to file Y"). Focus on intent and impact
- Don't add filler phrases ("This PR improves the codebase", "comprehensive changes")
- Keep the summary factual and concise, matching the user's communication style
- If commit messages are high-quality Conventional Commits, lean on them for the summary
- Include file counts and line stats only if they add value (large PRs)

## Common mistakes to avoid

- Generating description from only the latest commit (use ALL commits since base)
- Missing unpushed branch (always check and push if needed)
- Ignoring existing PR template in the repo
- Creating a ready (non-draft) PR by default (prefer draft)
- Verbose descriptions for trivial changes (3-line fix doesn't need 3 paragraphs)
- Generic test plans ("run the tests") instead of specific commands
