# merge-message: Plan

## Goal

Generate a Conventional Commits squash commit message from branch commits before merge. User pastes the result into GitLab/GitHub merge dialog.

## Architecture

Pure SKILL.md, no Python script. change-summary (via Skill tool) is the primary analysis engine. Git log is supplementary cross-check.

### Call chain

```
User (depth 0)
  └─ Skill: merge-message (inline, depth 0)
       ├─ Skill: change-summary (inline, still depth 0)
       │    ├─ Bash: run script
       │    ├─ Agent: interpret diffs (depth 1)
       │    └─ Agent: verify output (depth 1)
       ├─ Bash: git log base..HEAD (supplementary)
       └─ Generate CC message → print to screen
```

Skill->Skill chaining keeps us at depth 0 so change-summary can still use Agent tool.

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **standalone** (default) | user asks for merge message | Detect context, run change-summary, generate message, print |
| **sub-skill** | invoked by another skill via Skill tool | Same analysis, return message as text in response, no user interaction. Calling skill receives the raw CC message (subject + body + footer) directly, no file I/O needed |

## Workflow

### Step 1: Detect context

Determine base ref and head:

1. Check for open PR/MR:
   - `gh pr view --json baseRefName,headRefName` or `glab mr view --output json`
   - If found: base = target branch, head = current branch
2. No PR/MR: auto-detect main branch (`git symbolic-ref refs/remotes/origin/HEAD` or try main/master)
3. User can override: "generate merge message for feature-x against develop"

Also extract: branch name (for scope hint), PR/MR description (if available).

### Step 2: Run change-summary (primary source)

Invoke via Skill tool:

```
Skill tool: 'change-summary'
Args: "Analyze changes between <base> and HEAD. Use --platform <gh|glab> if detected in Step 1."
```

Pass `--platform` if Step 1 detected a PR/MR, so change-summary can fetch the PR/MR description as additional context.

change-summary runs in sub-skill mode: script + interpret + verify, returns changes.yaml content. This gives us:
- Typed, classified changes (feat/fix/refactor/etc.)
- Confidence levels
- Breaking change flags with migration info
- User-facing descriptions + technical details

### Step 3: Supplementary git log cross-check

Run `git log --oneline base..HEAD` to catch anything change-summary might have filtered as internal (tests, CI, deps). If a commit clearly adds user-facing value but isn't in changes.yaml, note it for inclusion.

This is a sanity check, not a primary source. change-summary's output wins on conflicts.

### Step 4: Generate CC message

#### Subject line

Format: `type(scope): description` or `type(scope)!: description` (breaking)

- **Type**: LLM decides based on "what is the main value this branch delivers?" Not mechanical priority. A branch with 1-line feat + 200-line fix = fix. A branch adding a whole feature with supporting fixes = feat.
- **Scope**: extract from branch name if it follows convention (`feat/sensors` -> `sensors`, `fix/auth-flow` -> `auth`). Otherwise from dominant area in changes. Omit if changes span many areas.
- **Subject**: imperative mood, lowercase, no period, max 72 chars. Describe the overall outcome, not individual changes.
- **Breaking**: `!` after type/scope if any change is breaking.

#### Body

List of changes from changes.yaml, each with CC type prefix:

```
Changes:
- feat: humidity sensor readings in USB exports
- fix: prevent buffer overwrite in sensor data reception
- refactor: extract sensor naming to dedicated module
```

Use `description` field from changes.yaml (user-facing language). One line per change. Skip internal/chore unless they're significant.

If PR/MR description exists and adds context not captured in changes, incorporate it into a brief summary paragraph before the changes list.

#### Footer

- `BREAKING CHANGE: <what broke>. <migration path>` if any change has `breaking: true`. Use `migration` field from changes.yaml.
- Issue refs: scan branch name for `#\d+` or `[A-Z]+-\d+`, add `Refs #N`.

### Step 5: Deliver

**Standalone:** Print the full message in a code block. Ask "Does this look good, or do you want to adjust anything? I can also copy it to clipboard."

If user asks to copy: copy to system clipboard using whatever method the platform/OS supports. Do not hardcode clipboard tools (wl-copy, pbcopy, clip.exe) in SKILL.md — the model picks the right one from user's environment.

**Sub-skill:** Return the message string. No user interaction.

## CC Format Reference (from commit skill)

- Subject: imperative, lowercase, no period, max 72 chars
- Body: wrap at 72 chars, blank line after subject
- Breaking: `!` after type/scope + `BREAKING CHANGE:` footer
- Issue refs: `Refs #N` or `Fixes #N` in footer
- No AI attribution trailers

## Output example

```
feat(sensors)!: add humidity sensor support

Changes:
- feat: humidity sensor readings in USB exports
- fix: prevent buffer overwrite in sensor data reception
- refactor: extract sensor naming to dedicated module

BREAKING CHANGE: API response format changed to camelCase.
Regenerate API clients and update parsers.

Refs #42
```

## Edge cases

| Case | Handling |
|------|----------|
| Single commit branch | Still run change-summary (commit might bundle multiple logical changes). If truly one change, subject = that commit's message (reformatted to CC if needed) |
| All commits are chore/ci/test | Type = chore, body lists changes. Note: "This branch contains only internal changes" |
| No open PR/MR, can't detect base | Ask user for target branch |
| change-summary unavailable | Degrade to git-log-only mode with warning. Parse CC prefixes from commit messages directly |
| Very large branch (50+ commits) | change-summary handles chunking. Merge-message summarizes: group related changes, cap body at ~20 lines |

## Dependencies

- **Primary**: change-summary skill (installed, Skill tool available). Without it, degrades to git-log-only mode with warning
- **Optional**: `gh` CLI (GitHub), `glab` CLI (GitLab) for PR/MR detection and description
- **Fallback**: works without gh/glab (manual base ref, no PR description)

## Non-goals

- Auto-merging or pushing (user pastes message manually)
- Rewriting existing merge commits
