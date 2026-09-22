# Release page

Shape of the markdown passed to `gh release create --notes-file` / `glab release create --notes-file`. Input: the CHANGELOG section from Step 3 (entries with categories, breaking flags, migration notes, PR references) and the platform detection output.

The CHANGELOG is the full record. The release page is its headline view for someone who lands on it once. The CHANGELOG section sits under a `## [X.Y.Z] - date` header the page does not have (the platform shows tag, date and author itself), so the page gets its own shape.

## Vocabulary

- **Entry**: one bullet of the CHANGELOG section
- **Item**: one bullet on the page. A Highlights item covers one or more entries and may reword them; it keeps the PR/MR links of the entries it covers, deduplicated, ascending. An item in the full list is an entry verbatim
- **Large release**: more than 20 entries in the CHANGELOG section, breaking entries included (the same count as N in the collapsed list)
- **Impact**, for ordering: first what the reader must act on, then what they can newly do, then what they get without doing anything, then edge cases and cosmetics. Equal impact: Added before Changed before Fixed, then CHANGELOG order

## Structure, top to bottom

No H1, no version or date line, no emoji.

**1. Breaking block.** Breaking entries leave their categories and open the page as one `> [!IMPORTANT]` block: a single breaking change is one sentence stating the break and the migration; several are one bullet each, in impact order. Breaking entries do not appear in the category sections or in Highlights; in a large release they stay, verbatim, in the collapsed full list. A section emptied by that move is omitted. The block keeps the entries' PR/MR links. GitLab renders the alert syntax from 17.10, older instances show a plain quote with the literal `[!IMPORTANT]`.

**2. Introduction.** One factual sentence naming the one or two highest-impact changes. Omitted when the body has three items or fewer. First release: instead, one paragraph of at most two sentences saying what the project does, for whom, and what it gives them.

**3. Body.** Two switches decide its shape: first release or not, large release or not.

- *Not first, not large*: categories promoted to `##` (`## Added`, `## Changed`, ...), same order as the CHANGELOG section, every entry as an item, ordered by impact within a section rather than by commit order.
- *First release or large*: one `## Highlights` section of at most 20 items, ordered by impact. Each item names one thing; entries about one thing (a command and its flags, a feature and its follow-ups, a fix and its variants) fold into one item that names the thing and its parts. The user-visible outcome comes first, detail after a colon only when it changes what the reader does. A first release that is not large shows every entry here, whatever its category.
- *Large*: after Highlights, the full list in one collapsed block. N is the number of entries in the CHANGELOG section, breaking entries included:

  ```markdown
  <details>
  <summary>All N changes</summary>

  ### Added

  - entries verbatim

  ### Changed

  - entries verbatim, `**BREAKING:**` ones included

  </details>
  ```

  The blank lines after `<summary>` and before `</details>` are required, or the markdown inside is not rendered. Highlights and the full list overlap by design; nothing is counted or reconciled between them.
- *No non-breaking entries left* (a breaking-only release): no category sections and no Highlights. A large release keeps the collapsed full list; a first release keeps its project paragraph.

**4. `## Install`**, only when the README gives an install command for a published package: the README's first install command with the released version pinned in the ecosystem's own syntax, then `[<package> <version> on <registry>](<version URL>)`. Published means the registry knows the package: check with the ecosystem's lookup (`pip index versions <package>`, `npm view <package> version`, `cargo search <package>`) or by fetching the registry page for any earlier version. A manifest alone (`pyproject.toml`, `package.json`, `Cargo.toml`) does not prove it.

**5. `## Thanks`**, only when at least one included change was authored by a human outside the maintainers: one sentence with their linked handles, alphabetical, each once. Authors come from the PRs/MRs behind the entries (`gh pr view N --json author`, `glab mr view N`), commit authors (`git log -1 --format=%an <sha>`) for entries without one. Maintainers are the repository's collaborators (`gh api --hostname <host> repos/<project>/collaborators`, `glab api projects/:fullpath/members/all`), the manifest's authors when that call fails. Bots excluded.

**6. Closing line**: `[Compare W.V.U...X.Y.Z](<compare URL>) · [Full changelog](<CHANGELOG.md at the release tag, version anchor>)`. The CHANGELOG link points at the tag (`/blob/<tag>/` on GitHub, `/-/blob/<tag>/` on GitLab) so it is right even before the branch is pushed, and at the file 6a creates or updates, so a CHANGELOG missing today is no reason to omit it. First release: no Compare. No Full changelog when 6a writes no section: an RC, or the user choosing `skip` for a non-KaC file (then drop the link before 6f). Neither: no line.

## Example: small release

````markdown
> [!IMPORTANT]
> The response envelope now uses camelCase keys. Update every response parser before upgrading.

## Added

- CSV and JSON export for query results ([#41](https://github.com/owner/repo/pull/41))
- Rate limiting with configurable per-client thresholds ([#43](https://github.com/owner/repo/pull/43))

## Fixed

- Connection pool exhaustion under concurrent batch requests

## Install

```sh
pip install example-api==1.4.0
```

[example-api 1.4.0 on PyPI](https://pypi.org/project/example-api/1.4.0/)

[Compare 1.3.0...1.4.0](https://github.com/owner/repo/compare/1.3.0...1.4.0) · [Full changelog](https://github.com/owner/repo/blob/1.4.0/CHANGELOG.md#140---2026-09-21)
````

Three items, so no introduction. The breaking change emptied Changed, so the section is gone.

## Example: large release

Abbreviated: a real page lists every entry inside the collapsed block, and N is their exact count.

````markdown
> [!IMPORTANT]
> - The `export` command writes to stdout by default. Pass `--output` to keep writing files. ([#55](https://github.com/owner/repo/pull/55))
> - Config keys are case-sensitive. Lowercase every key in `config.toml`. ([#58](https://github.com/owner/repo/pull/58))

Query results export to CSV, JSON and Parquet, and a query cache cuts repeated calls to a few milliseconds.

## Highlights

- Export to CSV, JSON and Parquet, with `--columns` to pick fields ([#41](https://github.com/owner/repo/pull/41), [#52](https://github.com/owner/repo/pull/52))
- Query cache: repeated queries answer from memory, `--no-cache` bypasses it ([#47](https://github.com/owner/repo/pull/47))
- Rate limiting with configurable per-client thresholds ([#43](https://github.com/owner/repo/pull/43))
- Connection pool no longer exhausts under concurrent batch requests

<details>
<summary>All 34 changes</summary>

### Added

- CSV export for query results ([#41](https://github.com/owner/repo/pull/41))
- JSON export for query results ([#41](https://github.com/owner/repo/pull/41))
- Parquet export for query results ([#52](https://github.com/owner/repo/pull/52))
- …

### Changed

- **BREAKING:** `export` writes to stdout by default. Migration: pass `--output <file>` to keep writing files ([#55](https://github.com/owner/repo/pull/55))
- …

### Fixed

- Connection pool exhaustion under concurrent batch requests
- …

</details>

[Compare 1.3.0...2.0.0](https://github.com/owner/repo/compare/1.3.0...2.0.0) · [Full changelog](https://github.com/owner/repo/blob/2.0.0/CHANGELOG.md#200---2026-09-21)
````
