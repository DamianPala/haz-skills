---
name: release-create
description: "Create releases: changelog, annotated tag, and GitHub/GitLab release page. Proposes semver bump, generates Keep a Changelog notes, supports RC pre-releases. Triggers: 'create release', 'new release', 'release this', 'tag release', 'zrob release', 'nowy release', 'wypusc wersje', 'release notes', tagging a version, cutting a release. DO NOT TRIGGER for commits, PR creation, CI/CD setup, or deployment."
version: 1.0.0
---

# Release Create

## Rules

- Never push tags or create releases without explicit user confirmation
- Respect existing tag convention: detect v prefix (or bare) from repo tags, match it
- Keep a Changelog format only. No custom categories, no commit dumps. Details in `references/keep-a-changelog.md`
- change-summary is source of truth for change classification. Trust its YAML output (type, category, confidence)
- Release notes tone matches detected audience (Step 3). Default: user-facing (impact, not implementation)
- Annotated tags only (`git tag -a`), never lightweight tags
- Blocking prompt: find and use a user-prompting tool (AskUserQuestion, ask_user, prompt). Plain text only if none exists. One question per prompt, never batch

## Platform detection

Run `scripts/detect-platform.py` from the skill directory. Returns JSON:
```json
{"platform": "github"|"gitlab", "host": "...", "project": "owner/repo", "commands": {...}}
```
- Exit non-zero: no platform detected. Skip release page creation, still create tag
- Exit zero, no `commands`: host known but CLI not installed (check `note` field). Pass `--host` to change-summary but skip release page creation
- Exit zero, `commands` present: full platform support. `project` field gives owner/repo for compare links

## Workflow

### Step 1: Detect state

Run platform detection first (see section above). Then:

**1a. Ensure correct working directory:**
- `git rev-parse --show-toplevel` to confirm you're inside a git repo. If not, abort
- If user specified a project path, `cd` into it first

**1b. Refresh remote state:**
- `git fetch origin --tags`
- If fetch fails (offline, no remote): warn "Working with local state only, remote tags may be stale", continue

**1c. Guard checks:**
- `git status --porcelain` → non-empty = dirty tree → **blocking prompt**: "Uncommitted changes detected. Commit or stash before releasing? (stash / abort)". If user says stash, run `git stash` and continue. After release, remind user to `git stash pop`
- `git branch --show-current` → empty = detached HEAD → abort "Cannot release from detached HEAD. Check out a branch first"
- Branch name starts with `ci/`, `test/`, `feature/`, `fix/`, `chore/`, `dev/`, `wip/` → likely not a release branch. **Blocking prompt**: "You're on `<branch>`. Releases are usually cut from main/master/develop. Switch to default branch? (switch / continue as RC / abort)"
- `git rev-parse --abbrev-ref --symbolic-full-name @{u}` → if this fails, branch has no upstream tracking. Skip ahead/behind check, warn "No upstream tracking for this branch"
- If upstream exists: `git rev-list --left-right --count HEAD...@{u}` → ahead > 0 → **blocking prompt**: "Branch is N commits ahead of remote. Push before releasing? (push / continue / abort)". Behind > 0 → **blocking prompt**: "Branch is N commits behind remote. Pull before releasing? (pull / abort)"

**1d. Collect context:**
- `git tag --list --sort=-version:refname` (all tags, newest first)
- Use `project` field from platform detection for compare links (owner/repo already parsed). If platform detection failed, fall back to `git remote get-url origin`
- Check if `CHANGELOG.md` exists. If yes, scan for KaC markers: version headers with brackets (`## [X.Y.Z] - YYYY-MM-DD`), standard category headers (`### Added`/`### Fixed`/etc.), compare links at bottom (`[X.Y.Z]: https://...`). Present = KaC format, absent = other format

**Branch → release type:**
- main/master/develop → **final release**
- Other → **RC pre-release** (version: `X.Y.Z-rc.N`)

**Tag handling** (order matters):

1. If no tags exist → **first release**. **Blocking prompt**: "No tags found. First release version? (v1.0.0 / v0.1.0 / custom)". Use user's choice as version, skip points 2-4 below (no tags to detect convention from, no base tag). change-summary will analyze full history

2. Detect tag convention:
   - Majority of existing tags use `v` prefix → use `v`
   - Majority bare → bare
   - Mixed → **blocking prompt**: "Mixed tag convention (vX.Y.Z and X.Y.Z). Which format?"

3. Find base tag:
   - Final release: last **final** tag (no `-rc`/`-alpha`/`-beta` suffix). This ensures change-summary gets the full range since the previous release
   - RC release: also use last **final** tag as base (same as final release). This way change-summary analyzes the full range and `suggested bump` determines the target version. RC numbering (`-rc.N`) is resolved separately in Step 3

4. `git log <base_tag>..HEAD --oneline` → zero commits = abort "Nothing to release since `<base_tag>`"

### Step 2: Analyze changes (via change-summary)

Invoke change-summary as sub-skill (runs in the current working directory set in Step 1a):

```
Skill: 'change-summary'
Args: "Analyze changes between <base_tag> and HEAD. --platform <gh|glab> --host <host>"
```

`<base_tag>` is the tag resolved in Step 1. For first release (no tags), omit `<base_tag>` entirely (change-summary auto-detects full history). Map platform detection output: `github` → `gh`, `gitlab` → `glab`. Omit `--platform` and `--host` if platform detection failed.

Returns YAML with `changes[]` and metadata. Fields this skill consumes: `category` (KaC-ready: Added/Changed/Fixed/etc.), `description` (user-facing text), `detail` (technical specifics, for developer-facing audience), `breaking` + `migration` (for BREAKING prefix and migration notes), `suggested bump` (major/minor/patch).

**Fallback** (change-summary unavailable): parse commits inline. Skip merge commits and version-bump commits. Map: `feat:`/`[FEAT]` → Added, `fix:`/`[FIX]` → Fixed, `refactor:`/`perf:`/`[IMP]` → Changed, `revert:` → Removed, `deprecated:` → Deprecated, `security:` → Security, `chore:`/`ci:`/`[DEV]` → skip. `!` or `BREAKING CHANGE` → breaking. Unrecognized → ask user. Note: fallback produces raw commit descriptions, not `description`/`detail` fields. Step 3 field selection doesn't apply, write entries directly from commit messages.

### Step 3: Generate release notes

Before generating, read `<skill-dir>/references/keep-a-changelog.md` for formatting rules, template, and verification checklist.

**Version proposal:**
- First release (no prior tags): version already chosen by user in Step 1. Skip bump logic
- Normal release: apply `suggested bump` from change-summary to base tag (MAJOR/MINOR/PATCH increment)
- Filter bump through audience: if bump = major, check if breaking changes are user-facing or internal-only (build artifacts, distribution format, dev tooling, internal APIs). User-facing audience: only user-visible breaking changes warrant major. If all breaking items are internal → **blocking prompt**: "Suggested bump: major (reason: `<breaking items>`). Is this user-facing breaking? (major / downgrade to minor)"
- RC: append `-rc.N` where N = highest existing `X.Y.Z-rc.*` tag + 1 (tags are global, filter by target version pattern, e.g. all `5.4.0-rc.*` tags). If no prior RC for this version, start at `rc.1`
- Final release with prior RCs: change-summary handles deduplication when given the correct base (last final tag)

**Audience detection** (infer from project context: README, file types, build system, existing docs):
- **Developer-facing** (libraries, SDKs, APIs, dev tools): use `detail` field for entries. API names, function signatures, migration code OK
- **User-facing** (apps, SaaS, firmware products, B2B): use `description` field. Benefit language, no implementation details
- Default: user-facing
- For deployed/delivered products (self-hosted, firmware updates, enterprise): always include security patches and breaking changes with migration steps regardless of audience, because the person updating needs this

Audience sets the tone and detail level for release notes. Confirm with user in Step 5.

**Generate release notes:**

change-summary returns ALL change types including internal ones. Filter before generating notes per `references/keep-a-changelog.md` mapping:
- **Always include:** feat, fix, revert
- **Include only if user-noticeable:** refactor, perf, docs
- **Include only if user-facing:** test, ci, build, chore, style
- **Always include regardless of type:** breaking changes

Group included changes by category in fixed order: Added → Changed → Deprecated → Removed → Fixed → Security. Skip empty categories.

**Field selection:** start from `description` (user-facing) or `detail` (developer-facing). If `description` is too vague or generic, enrich with context from `detail` so the reader understands what changed, but keep the language appropriate for the audience. Don't mechanically combine both fields every time.

**Breaking changes:** `**BREAKING:**` prefix inside Changed or Removed, with migration notes from change-summary. When multiple breaking changes exist, order by impact: data loss / end-user visible first, then API removals, then renames and signature changes.

Step 6 handles formatting for each destination (CHANGELOG.md, tag message, release page) from this single output.

### Step 4: Verify (internal checklist)

Verify internally, do not output. Every answer must be "yes":

1. Every change-summary item accounted for (included or consciously skipped)?
2. Categories from allowed set only, in correct order?
3. Breaking changes have `**BREAKING:**` prefix and migration notes?
4. Version number consistent (release notes, tag, CHANGELOG header, compare links)?
5. Date is today (ISO 8601 `YYYY-MM-DD`)?
6. Entries match detected audience? (user-facing: no file/function/variable names. Developer-facing: API names OK, no internal implementation)
7. Entries are readable and grouped (not raw field dumps)?
8. Empty categories omitted?
9. Compare link format planned for Step 6 matches platform (GitHub vs GitLab) and tag convention?

If any "no", fix before proceeding.

### Step 5: Present for review

Show: detected audience, proposed version (with bump reasoning), release notes, files to change.

**Blocking prompt**: "Audience: `<detected>`. Release `<version>` on `<date>`? (y / edit / change-version / change-audience / cancel)"

- **edit**: write notes to temp file, tell user path, wait for user to say they're done, read back
- **change-version**: ask for new version, update headers
- **change-audience**: ask user for audience (developer-facing / user-facing), regenerate notes from Step 3 with new audience

### Step 6: Execute

**6a. CHANGELOG.md** (skip for RC/pre-releases, changelog reflects final releases only. Follow `references/keep-a-changelog.md` for template, header format, and compare link syntax):
- Exists, KaC format:
  - Prepend new version section (`## [X.Y.Z] - YYYY-MM-DD`) as first section after `# Changelog`
  - If `## [Unreleased]` exists: insert new version below it. If it has content → **blocking prompt**: "Unreleased section has entries. Merge into this release? (merge / keep separate)". After release, leave Unreleased empty and update its compare link to `<new_tag>...HEAD`
  - If `## [Unreleased]` is empty: insert below it, update its compare link to `<new_tag>...HEAD`
- Exists, non-KaC format → **blocking prompt**: "CHANGELOG.md uses a different format. Overwrite with Keep a Changelog? (y / append / skip)"
- Doesn't exist → create with KaC header (from reference template) + current release only. No backfilling from old tags (commit history quality is unknown)
- Add/update compare links at bottom of file

**6b. Commit CHANGELOG changes** (skip if 6a was skipped, e.g. RC/pre-release):
- Stage and commit: `git add CHANGELOG.md && git commit -m "docs(changelog): add <version> release notes"`
- The tag must point to this commit so the tagged state includes the updated CHANGELOG

**6c. Git tag** (tag message = release notes as plain text, strip markdown formatting):
```
git tag -a <version> -F <temp_notes_file>
```
Write release notes to two temp files: (1) plain text for tag (strip `###` headers → `Added:`, strip `**BREAKING:**` → `BREAKING:`, strip link syntax, prefix with `Release <version>`), (2) markdown for release page in 6f.

**6d. Blocking prompt**: "Push tag and create release? (y / tag-only / cancel)"
- **tag-only**: stop here, user pushes manually

**6e. Push tag:**
- `git push origin <version>` (pushes tag only, not branch). If push fails (hook, permissions), tell user and suggest manual push
- If 6b created a CHANGELOG commit: tell user "Branch has a new CHANGELOG commit. Push it when ready: `git push origin <branch>`"

**6f. Create release** (skip if platform detection failed or `commands` absent):
- `platform` = github: `gh release create <version> --title "<version>" --notes-file <markdown_notes_file>` (add `--prerelease` for RC)
- `platform` = gitlab: `glab release create <version> --notes-file <markdown_notes_file>` (add `--ref <branch>` if not default)
- If CLI fails (404, permissions): try platform API fallback using `project_id`/`project` from platform detection. If API also fails, check for available MCP tools for the platform (e.g. `create_release`, `create_tag`). If all methods fail, output manual instructions

### Step 7: Post-release guidance

Informational output (not blocking):
- Tag name and release URL: "Verify the release page: `<URL>`"
- CI detected (`.github/workflows/`, `.gitlab-ci.yml`): "Pipeline may be running. Check: `gh run list` / `glab ci status`"
- No CI: "To attach build artifacts: `gh/glab release upload <version> ./file`"

## Output Example

Tag message (plain text, for `git tag -a -F`):
```
Release 1.4.0

Added:
- CSV and JSON export for query results
- Rate limiting with configurable per-client thresholds

Changed:
- BREAKING: Response envelope uses camelCase keys. Migration: update all response parsers

Fixed:
- Connection pool exhaustion under concurrent batch requests
```

## Constraints

- Never push tags without user confirmation
- Release notes tone matches detected audience, confirmed by user in Step 5
- CHANGELOG changes must be committed before creating the tag (tag must point to a commit that includes the updated CHANGELOG)
