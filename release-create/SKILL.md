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
- Exit non-zero: no platform detected. Skip 6f (nothing to publish the release page to), still create tag. The page markdown is still generated and shown, the user can paste it by hand
- Exit zero, no `commands`: host known but CLI not installed (check `note` field). Pass `--host` to change-summary but skip 6f
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

5. If HEAD already carries a final tag made outside this skill (`git tag --points-at HEAD`) and that tag has no release page yet (`gh release view <tag>` / `glab release view <tag>` fails) → **page-only release**: the version is that tag, the base tag is the last final tag before it, Step 3 skips the version proposal, and 6c–6e are skipped. 6a–6b still run, so the CHANGELOG commit lands after the tag: the page's Full changelog link then points at the default branch (see `references/release-page.md`, closing line) and Step 7 tells the user it resolves once that commit is pushed. Tell the user this before Step 2 so they can choose to re-tag instead

### Step 2: Analyze changes (via change-summary)

Invoke change-summary as sub-skill (runs in the current working directory set in Step 1a):

```
Skill: 'change-summary'
Args: "Analyze changes between <base_tag> and HEAD. --platform <gh|glab> --host <host>"
```

`<base_tag>` is the tag resolved in Step 1. For first release (no tags), omit `<base_tag>` entirely (change-summary auto-detects full history). Map platform detection output: `github` → `gh`, `gitlab` → `glab`. Omit `--platform` and `--host` if platform detection failed.

Returns YAML with `changes[]` and metadata. Fields this skill consumes: `category` (KaC-ready: Added/Changed/Fixed/etc.), `description` (user-facing text), `detail` (technical specifics, for developer-facing audience), `breaking` + `migration` (for BREAKING prefix and migration notes), `commits` (hashes behind each change, for PR/MR references), `suggested bump` (major/minor/patch).

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

**First release:** the range is the whole history, so `fix:` and `refactor:` commits describe code nobody ever ran. A fix or change to something that never shipped is not a change for the reader: fold it into the Added entry it belongs to (omit it when no Added entry covers it), and keep Changed/Fixed only for behaviour a reader of an earlier public artifact (a README, a beta) could have relied on.

**Field selection:** start from `description` (user-facing) or `detail` (developer-facing). If `description` is too vague or generic, enrich with context from `detail` so the reader understands what changed, but keep the language appropriate for the audience. Don't mechanically combine both fields every time.

**References:** an entry ends with the links of the PRs/MRs behind its `commits`: `([#123](<url>))`, several as `([#123](…), [#124](…))`, numbers deduplicated and ascending. Number sources, in order: the commit subject (GitHub squash `(#N)` or `Merge pull request #N`; GitLab `(!N)` or `See merge request <project>!N`), then a platform lookup for commits that carry none (rebase merges, edited squash subjects): `gh api --hostname <host> repos/<project>/commits/<sha>/pulls` or `glab api projects/:fullpath/repository/commits/<sha>/merge_requests` (glab resolves host and path from the remote). URLs from platform detection: `<host>/<project>/pull/N` rendered `[#N]` on GitHub, `<host>/<project>/-/merge_requests/N` rendered `[!N]` on GitLab. No PR behind a commit → no reference at all; a bare commit hash is noise to the reader, and the compare link already covers it.

**Breaking changes:** `**BREAKING:**` prefix inside Changed or Removed, with migration notes from change-summary. When multiple breaking changes exist, order by impact: data loss / end-user visible first, then API removals, then renames and signature changes.

This output is the CHANGELOG section. Two more shapes derive from it:

- **Release page** (markdown for 6f): its own shape, defined in `<skill-dir>/references/release-page.md`. Read that file and generate the page now, so the user reviews it in Step 5
- **Tag message** (plain text for 6c): mechanical stripping, done in Step 6

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
10. PR/MR references present on every entry that has one, deduplicated and ascending, none invented?
11. Release page: introduction first, then the breaking block, and the introduction says what changes for the reader rather than naming a standard or a ticket? Breaking changes in the block and nowhere else except the collapsed full list, one one-line sentence each, with rename inventories left to the migration document? Highlights present exactly when the release is first or large, at most 12 one-line items, the collapsed full list exactly when large (per `references/release-page.md`)? `All N changes` equals the entry count? Every item keeps its entries' PR/MR links? Install only for a package the registry knows?

If any "no", fix before proceeding.

### Step 4b: Fresh-eye review of the release page

The author of the notes has read every diff and no longer sees the page the way a reader landing on it does: an alert block that grew into a wall, Highlights that became a second list, an introduction that names a standard instead of a change. One review from a context that has seen none of that catches this at a fraction of the run's cost (the change-summary agents read the whole diff; the reviewer reads a few kilobytes).

Dispatch one subagent with a fresh context, whatever the runtime offers (a subagent tool, a background agent CLI); never review inline. Give it:

- the release page markdown and the CHANGELOG section (the two Step 3 outputs, as files)
- `changes.yaml` from Step 2, so it can check the page against the record
- `<skill-dir>/references/release-page.md`, the rules the page claims to follow

The brief asks for answers, not an opinion. The reviewer reads the page top to bottom once, then, from the introduction and the breaking block alone, writes in its own words: what this release is and for whom; what a reader must do before upgrading; the three things it remembers. Then it checks the whole page against the rules file and against `changes.yaml`: nothing on the page that the record does not support, no high-impact entry of the record missing from the page, every rule of the shape kept. Output: either the single word `pass`, or at most five findings ordered by impact, each quoting the line and giving the replacement wording. Generic advice ("could be shorter", "looks good overall") is not a finding. One round, no loop.

Apply the findings you accept, rerun the Step 4 checklist on what changed, and carry the review into Step 5: what the user sees is the reviewed page. A finding you reject is mentioned there in one line with the reason. Skip this step only when the page has three items or fewer.

### Step 5: Present for review

Show: detected audience, proposed version (with bump reasoning), the CHANGELOG section, the release page markdown (in a fenced block, so its shape is visible before anything is published), files to change.

**Blocking prompt**: "Audience: `<detected>`. Release `<version>` on `<date>`? (y / edit / change-version / change-audience / cancel)"

- **edit**: write the CHANGELOG section and the release page to two temp files, tell user both paths, wait for user to say they're done, read back
- **change-version**: ask for new version, update every place it appears: CHANGELOG header and compare link, release page install command, registry URL, compare and Full changelog URLs
- **change-audience**: ask user for audience (developer-facing / user-facing), regenerate notes from Step 3 with new audience

After any of the three: rerun Step 4 on both outputs and present them again with the same prompt. What gets published is what the user last saw.

### Step 6: Execute

**6a. CHANGELOG.md** (skip for RC/pre-releases, changelog reflects final releases only. Follow `references/keep-a-changelog.md` for template, header format, and compare link syntax):
- Exists, KaC format:
  - Prepend new version section (`## [X.Y.Z] - YYYY-MM-DD`) as first section after `# Changelog`
  - If `## [Unreleased]` exists: insert new version below it. If it has content → **blocking prompt**: "Unreleased section has entries. Merge into this release? (merge / keep separate)". After release, leave Unreleased empty and update its compare link to `<new_tag>...HEAD`
  - If `## [Unreleased]` is empty: insert below it, update its compare link to `<new_tag>...HEAD`
- Exists, non-KaC format → **blocking prompt**: "CHANGELOG.md uses a different format. Overwrite with Keep a Changelog? (y / append / skip)". On skip: drop the Full changelog link from the release page before 6f
- Doesn't exist → create with KaC header (from reference template) + current release only. No backfilling from old tags (commit history quality is unknown)
- Add/update compare links at bottom of file

**6b. Commit CHANGELOG changes** (skip if 6a was skipped, e.g. RC/pre-release):
- Stage and commit: `git add CHANGELOG.md && git commit -m "docs(changelog): add <version> release notes"`
- The tag must point to this commit so the tagged state includes the updated CHANGELOG

**6c. Git tag** (tag message = release notes as plain text, strip markdown formatting):
```
git tag -a <version> -F <temp_notes_file>
```
Write two temp files:

1. **Plain text for the tag**, derived from the CHANGELOG section: strip `###` headers → `Added:`, strip `**BREAKING:**` → `BREAKING:`, strip link syntax, prefix with `Release <version>`
2. **Markdown for the release page** (6f): the page reviewed in Step 5, shape per `references/release-page.md`

**6d. Blocking prompt**: "Push tag and create release? (y / tag-only / cancel)"
- **tag-only**: stop here, user pushes manually

**6e. Push tag:**
- `git push origin <version>` (pushes tag only, not branch). If push fails (hook, permissions), tell user and suggest manual push
- If 6b created a CHANGELOG commit: tell user "Branch has a new CHANGELOG commit. Push it when ready: `git push origin <branch>`"

**6f. Create release** (skip if platform detection failed or `commands` absent):
- `platform` = github: `gh release create <version> --title "<version>" --notes-file <markdown_notes_file>` (add `--prerelease` for RC)
- `platform` = gitlab: `glab release create <version> --name "<version>" --notes-file <markdown_notes_file>` (add `--ref <branch>` if not default)
- Title is the bare version (`1.4.0`, or `v1.4.0` under the `v` convention), never `<product> <version>`: the repository name already sits above the release header and in the release list, so a product name in the title reads twice. Exception: a repository releasing several independently versioned packages, where the tag maps to exactly one of them and the title names it (`api 1.4.0`)
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

Release page (markdown, for `--notes-file`; title `1.4.0`): the same release rendered per `references/release-page.md`, which holds a small-release and a large-release example.

## Constraints

- Never push tags without user confirmation
- Release notes tone matches detected audience, confirmed by user in Step 5
- CHANGELOG changes must be committed before creating the tag (tag must point to a commit that includes the updated CHANGELOG)
