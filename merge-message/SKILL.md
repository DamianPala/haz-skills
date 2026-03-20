---
name: merge-message
description: "Generate a Conventional Commits squash commit message from branch commits before merge. Runs change-summary pipeline for deep diff analysis (submodule expansion, type classification, breaking change detection with migration paths) that produces significantly better results than raw git log inspection. Formats CC subject + body with typed items + BREAKING CHANGE footer for pasting into GitLab/GitHub merge dialog. Use this skill whenever the user mentions merge message, squash message, squash commit, MR message, PR merge, or wants a commit message for merging a branch. Polish: 'merge message', 'squash message', 'message do MR/PR', 'commit message do merge'. Explicitly NOT for: regular commits (use commit skill), code review, PR creation, or changelog generation."
version: 1.0.0
---

# Merge Message

## Rules

- Output must be a valid Conventional Commits message (subject + body + optional footer)
- change-summary is the primary source of truth. Git log is supplementary cross-check only
- Never fabricate changes not backed by change-summary output or git history
- Breaking `!` goes before `:` per CC spec: `type(scope)!: description`

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **standalone** (default) | user asks for merge/squash message | Detect context, analyze, generate, print message |
| **sub-skill** | invoked by another skill via Skill tool | Same analysis, return raw CC message text in response, no user interaction |

## Workflow

This skill invokes change-summary (which spawns sub-agents via acpc). If Skill tool is unavailable, read and follow these instructions directly.

### Step 1: Ensure correct working directory

Git commands and platform detection require being inside the target project's git repository. If the user provided a PR/MR URL or branch name for a project that lives in a different directory than the current working directory, `cd` into that project's directory first. Check `git rev-parse --show-toplevel` to confirm you're in the right repo. If you can't determine the project path, ask the user.

Run `git fetch origin` to ensure remote refs are up to date. This is safe (no working tree changes) and prevents analyzing stale diffs when new commits were pushed to the remote.

### Step 2: Detect context

**Platform detection:** run `python3 <skill-dir>/scripts/detect-platform.py`. Returns JSON with `platform`, `host`, and ready-to-use `commands` (`mr_get`, `mr_list`, `mr_create`) with `{iid}`/`{nr}` placeholders. If it exits non-zero, skip PR/MR query. If `commands` is missing, CLI is not installed (skip PR/MR query, still pass `--host` to change-summary).

**Determine base and head:**
1. User provided explicit base/head in prompt (e.g. "merge message for feature-x against develop"): use as given, skip to Step 3
2. User provided a PR/MR URL: extract number from path (`/pull/(\d+)` = PR, `/-/merge_requests/(\d+)` = MR). Run `commands.mr_get` with the number substituted. Parse JSON for base/head branch and description (GitHub: `baseRefName`/`headRefName`/`body`, GitLab: `source_branch`/`target_branch`/`description`)
3. PR/MR open on current branch: run `commands.mr_list`, find entry matching current branch as source/head. Then run `commands.mr_get` with its number. Use base = target branch, head = current branch. Save description for context
4. No PR/MR: detect base branch. Check `git remote -v` for fork indicators first (upstream remote → use `upstream/main`). Otherwise: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null`, fallback to main or master
5. Can't detect: ask user (standalone) or fail with error (sub-skill)

After resolving base and head: if they resolve to the same ref (e.g. on main with no explicit head), stop and tell user there's no branch to generate a merge message for.

### Step 3: Run change-summary

Invoke change-summary via Skill tool (preferred) or by reading its SKILL.md directly if Skill tool is unavailable. Include platform and host from Step 2:

```
Skill: 'change-summary'
Args: "Analyze changes between <base> and <head>. --platform <gh|glab> --host <host> (from Step 2 detection: map github→gh, gitlab→glab)."
```

change-summary returns changes.yaml content with typed, classified changes, confidence levels, breaking flags, and migration info.

If change-summary is unavailable (not installed and SKILL.md not readable): degrade to git-log-only mode. Run `git log --oneline <base>..<head>` and infer changes from commit messages. For CC-prefixed messages (`feat:`, `fix:`, etc.), use the type and description directly. For non-CC messages (`[FEAT]`, `Add X`, `wip`, etc.), infer type from keywords and file context: "add"/"new" → feat, "fix"/"bug"/"patch" → fix, bracket prefixes like `[FEAT]` map to their CC equivalent. Uninformative messages ("wip", "stuff") get type chore. Output is still a valid CC message, just lower quality. Standalone: warn user. Sub-skill: return normally. Skip Step 4.

### Step 4: Cross-check with git log

Run `git log --oneline <base>..<head>`.

Compare against change-summary output by matching commit hashes (each changes.yaml item has a `commits` field). Git log is noisy: expect fixups, WIPs, reverts, merge commits, and misleading messages. Treat it as a checklist, not a source of truth.

- Hash in log AND in changes.yaml: confirmed, use change-summary's description
- Hash in log but NOT in changes.yaml: change-summary captures all types (including test/CI/build), so a missing hash likely means merge commit or empty commit. Only flag if the subject suggests a real change was missed
- Multiple changes.yaml items sharing the same hash (change-summary split one commit into multiple logical changes): trust change-summary, this is expected

change-summary wins on all conflicts.

### Step 5: Generate CC message

**Subject:** `type(scope): description` (or `type(scope)!: description` if breaking)

- Type: choose based on the main value this branch delivers. A branch with 1-line feat + 200-line fix = fix. A feature branch with supporting fixes = feat. Use judgment, not mechanical priority
- Scope: from branch name if it has a type prefix (take everything after the first `/`: `feat/sensors` -> `sensors`, `fix/auth-flow` -> `auth-flow`). From dominant change area if branch name has no convention. Omit if changes span many areas
- Description: imperative mood, lowercase, no period, max 72 chars. Describe the overall outcome

**Body:**

If PR/MR description adds context that is NOT already covered by the subject line or the changes list (e.g. motivation, migration context, deployment notes), include a brief summary line first, then a blank line. Do NOT paraphrase or restate the subject line.

List changes from changes.yaml, each with CC type prefix. Breaking items get `!` after the type (`fix!:`, `refactor!:`) so they're scannable without reading the footer:

```
Changes:
- feat: description from changes.yaml
- fix!: description of a breaking fix
- refactor: description from changes.yaml
```

Start from the `description` field. If it's self-explanatory, use it as-is. If it's too vague or generic (e.g. "timer function added"), enrich with context from `detail` so the reader understands what and why. Don't mechanically combine both fields every time. One line per change. Include ALL changes including breaking ones (the body says WHAT changed). Skip test/ci/chore unless significant (change-summary captures these, but merge messages typically omit them for readability). Deduplicate: if changes.yaml has two items describing the same logical change with different wording, keep the clearer one. Let the body scale naturally with branch size, don't artificially cap it.

**Footer:**

- Breaking: `BREAKING CHANGE:` footer explains HOW TO MIGRATE, not what changed (that's already in Changes). Use the `migration` field from changes.yaml. If migration field is missing, describe what users need to do based on the breaking change. Keep it actionable. Don't repeat the change description from the body. If migration details are too verbose for a commit message, the `!` in subject and breaking items in Changes are sufficient on their own, and the footer can be trimmed or omitted

  When multiple breaking changes exist, group by impact: data loss / end-user visible first, then API removals, then renames and signature changes. Separate groups with blank lines. One line per migration action. Skip group headers for ≤3 breaking changes.

- Issues: scan branch name for `#\d+` or `[A-Z]+-\d+`. Use `Fixes #N` if the branch is a bugfix (type = fix). Use `Refs #N` otherwise (features, refactors). For Jira-style IDs: `Refs PROJ-123`

**Edge cases:**
- Single commit branch: still run change-summary (one commit may bundle multiple logical changes). If truly one change, subject = that commit's message reformatted to CC
- All commits are chore/ci/test: type = chore, body lists changes normally
- change-summary returns `changes: []` (all changes internal): type = chore, subject describes the branch purpose from git log/branch name, body = "Internal changes only (tests, CI, deps)". Standalone: tell user no user-facing changes were found
- Fork PR where base is on upstream remote: check `git remote -v` for fork indicators. Use `upstream/<branch>` as base, not `origin/<branch>`. Same guidance as change-summary's base ref table

### Step 6: Deliver

**Standalone:** print the full message in a fenced code block, wrapped in `---` separators above and below so it visually stands out.

If Step 4 found suspicious commits (user-facing subject but missing from change-summary, reverts, WIPs, fixups, or anything that doesn't fit), list them below the code block: "These commits didn't match change-summary and may need attention:" + short hash + subject. This helps the user verify nothing was lost or misclassified.

Ask: "Does this look good, or do you want to adjust anything? I can also copy it to clipboard."

If user asks to copy, copy the message to system clipboard.

**Sub-skill:** return the raw CC message text in the response. No user interaction.

## Output Example

```
feat(auth)!: add OAuth2 login and refactor session handling

Changes:
- feat: OAuth2 authorization code flow with PKCE
- feat: token refresh runs automatically before expiry
- fix!: session cookie name changed from `sid` to `session_id`
- refactor!: replace custom token store with Redis-backed sessions

BREAKING CHANGE:
- Rename `sid` cookie to `session_id` in all clients
- Replace TokenStore.get() calls with SessionManager.load()

Refs #42
```

## Constraints

- No AI attribution trailers in the generated message
