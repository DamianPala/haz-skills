# Keep a Changelog: rules and template

Based on Keep a Changelog v1.1.0, adapted for automation workflows. Shared reference for skills that generate or update CHANGELOG.md.

## Rules

1. Changelogs are for humans. Write readable descriptions, not commit dumps
2. File: `CHANGELOG.md`, reverse chronological (newest first)
3. Dates: ISO 8601 `YYYY-MM-DD` (never DD/MM/YYYY, never "March 14")
4. Categories in this fixed order (use only these, skip empty ones):
   - **Added** — new features
   - **Changed** — changes to existing functionality
   - **Deprecated** — features marked for future removal
   - **Removed** — features now eliminated
   - **Fixed** — bug corrections
   - **Security** — vulnerability patches
5. No other categories ("Breaking Changes", "Other", "Performance", etc.). Tools and users depend on the six standard categories for parsing and scanning. Custom categories break tooling and reduce readability
6. Breaking changes: use `**BREAKING:**` prefix inside **Changed** or **Removed**. A breaking change from ANY commit type (feat!, fix!, refactor!, etc.) goes in Changed or Removed, not in its original category
7. Every version gets a compare link at the bottom of the file (reference-style)
8. Edit and group commit messages into user-facing descriptions. Raw commit messages are noisy, repetitive, and written for developers, not users. The changelog should communicate impact, not implementation
9. Yanked releases: `## [X.Y.Z] - YYYY-MM-DD [YANKED]`
10. No intro paragraph ("All notable changes..."). Start with the latest version right after `# Changelog`
11. This skill does not create `## [Unreleased]` sections. If one exists (added manually by devs): merge or keep its content per user choice, leave it empty after release, update its compare link to point from the new tag to HEAD

## Commit parsing

### Merge commits

Skip merge commits (titles like "Merge branch '...' into '...'"). Extract changes from the squash/feature commit instead. When a squash commit body contains multiple prefixed lines, parse each line as a separate entry.

Also skip: version-bump commits ("1.2.0", "Version 1.2.0", "v1.2.0", "Bump version to...") and intermediate release tags that fall within the compare range.

### Conventional Commits mapping

| CC type | Category | Notes |
|---------|----------|-------|
| `feat` | Added | |
| `fix` | Fixed | |
| `refactor` | Omit | Include as Changed only if user-noticeable |
| `perf` | Omit | Include as Changed only if user-noticeable |
| `revert` | Removed or Changed | Describe what was reverted |
| `docs` | Changed | Only if user-facing (README, API docs). Omit internal docs |
| `deprecated` | Deprecated | |
| `security` | Security | |
| `chore`, `ci`, `build`, `style`, `test` | Omit | Unless user-facing |
| Any type with `!` or `BREAKING CHANGE` trailer | Changed or Removed | Always `**BREAKING:**` prefix |

### Non-standard prefixes

Most bracket prefixes (`[FEAT]`, `[FIX]`, `[BUG]`, etc.) are self-explanatory. Ambiguous ones to watch for:
- `[IMP]` (Improvement) → Changed
- `[DEV]` (Developer/internal) → usually omit, include only if user-facing
- `[TST]` (Test) → usually omit, include only if user-facing

For any unrecognized prefix or commit without a prefix, infer category from content. If ambiguous, ask the user.

## Compare link formats

| Platform | Versioned | First release (no prior tag) |
|----------|-----------|------------------------------|
| GitHub | `https://github.com/o/r/compare/<old>...<new>` | `https://github.com/o/r/releases/tag/<tag>` |
| GitLab | `https://gitlab.example.com/o/r/-/compare/<old>...<new>` | `https://gitlab.example.com/o/r/-/releases/<tag>` |

`<tag>` = full tag name as it appears in the repo (e.g. `v2.3.0` or `2.3.0`). Match the repo's existing convention.

## Pre-release and RC tags

- Pre-release versions (e.g. `1.0.0-rc.1`, `2.0.0-alpha.3`) follow the same format rules
- When generating a final release changelog, use the last final tag as base for change analysis. This covers all changes including those from RC cycles
- Deduplication: if the same change appears across multiple commits in the range, keep only one entry. Use the most complete/recent description. When in doubt, group by what changed, not by which commit introduced it

## Anti-patterns

- Dumping raw git log as changelog
- Vague entries ("Bug fixes", "Various improvements", "Minor changes")
- Code-level details ("Refactored X module", "Added import Y to file Z")
- File names, function names, or variable names in entries (exception: developer-facing changelogs for libraries/SDKs may include public API names)
- Listing empty categories
- Missing compare links
- Inconsistent formatting between versions

**Bad vs good example:**

Bad (commit dump):
```
- [FIX] Fix calibration for specific cases.
- [DEV] Update brightness lvl name.
- [FIX] Sensors name with orders.
```

Good (user-facing, edited):
```
### Fixed
- Calibration accuracy for edge-case sensor readings
- Sensor display names now match physical order
```

## Template

```markdown
# Changelog

## [X.Y.Z] - YYYY-MM-DD

### Added

- Feature description from user perspective

### Changed

- **BREAKING:** Changed behavior. Migration: do X instead of Y
- Improved performance of feature Z

### Removed

- **BREAKING:** `legacyMethod()` removed. Use `newMethod()` instead

### Fixed

- Resolved issue with A under condition B

[X.Y.Z]: https://gitlab.example.com/owner/repo/-/compare/W.V.U...X.Y.Z
```

## Verification checklist

After generating changelog content, verify internally (do not output this list). Every answer must be "yes".

1. Every commit since last tag accounted for (included or consciously skipped)?
2. No commit appears in two categories?
3. Categories only from allowed set (Added, Changed, Deprecated, Removed, Fixed, Security)?
4. Categories in correct order (Added → Changed → Deprecated → Removed → Fixed → Security)?
5. Empty categories omitted?
6. Header format: `## [X.Y.Z] - YYYY-MM-DD` with ISO 8601 date?
7. Breaking changes marked `**BREAKING:**` inside Changed or Removed (not a separate section)?
8. Entries written from user perspective (no file names, function names, variable names)? Exception: developer-facing changelogs may include public API names
9. No commit message dump (entries are edited, grouped, readable)?
10. Merge commits skipped?
11. Compare links present and in correct platform format (GitHub vs GitLab)?
12. Tag convention matches repo (v prefix or bare)?
13. If RC/pre-release: entries deduplicated across RC tags?

If any "no", fix before proceeding.
