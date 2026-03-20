## Format reference
- `## Commit log (hints only)` at the top: list of `<hash> <message>` lines. These are unreliable hints, not structure. Use them to understand intent but verify everything from the diff.
- `## File: '<path>' [file-type, status, +N/-M]` or `## File: '<path>' [file-type, status, +N/-M, K change regions]` with unified diff per file
- `## Submodule: '<name>' [status]` for submodule changes
- `## Skipped files` listing filtered lock files and generated code

## Interpretation flow

Read ALL file diffs in the chunk. Identify every distinct logical change from code alone. The commit log is a sidebar for intent hints, not a source of truth. Prefer fine granularity: one item per distinct behavior change or mechanism. Downstream consumers can merge items but cannot split them, so err toward more items with rich detail rather than fewer coarse items.

1. Examine the diffs file by file. Group related changes across files into logical changes.

   **When to keep as one item:** implementation details of a single feature that don't make sense independently (e.g. a new menu item + its persistence + its driver support = one feature).
   **When to split:** sub-changes that are independently meaningful to a reviewer or user (e.g. a feature + its localization into 14 languages = two items, because localization is an independently reviewable concern). Multiple files serving the same behavior = one item. Same file containing two unrelated fixes = two items. Test file changes should normally be their own item with `type: test`, unless trivially coupled to a single source change (one new test for one new function).

2. Only then glance at the commit log to assign confidence:

   | Your finding vs commit log | Action | Confidence |
   |---------------------------|--------|------------|
   | Diff confirms a commit message | Use your description, enrich with message context | high |
   | Diff shows change not mentioned in any message | Keep it, describe from diff alone | medium |
   | A message claims change not obvious in diff | Re-read diff for indirect evidence. If found, include. If truly absent, omit | low (if included) |

3. For each change determine:
   - type: feat / fix / refactor / perf / docs / chore / revert / style / test / ci / build
     Decide from the code diff, not from commit messages or file metadata. A new file can be a refactor (extract to new file). A small change can be a feature. Read the code.
   - breaking: true only when verified from diff (deleted public API, changed function signatures, removed exports, deleted files that are part of a deployment or integration contract such as firmware binaries, config templates, or public scripts). File header hints like `[Deleted]` are not sufficient on their own.
   - description: one sentence, END USER perspective. Describe the benefit or behavior change, not the implementation. No file names, no function names, no technical jargon. "Improved sensor reading reliability" not "Added guard in GetSensorValue to prevent buffer overwrite".
   - detail: technical description for developers/reviewers. Include what specifically changed in the code, relevant component names, mechanisms. Multiple sentences OK.
   - files: list of affected file paths from the diff (relative to repo root). List EVERY file from `## File:` headers in this chunk that is affected by this change. Do not abbreviate, summarize, or skip files. A downstream cross-check will flag missing files.
   - confidence: high / medium / low
   - note: (when confidence < high) explain your inference
   - migration: (breaking changes only) what users need to do

   Do NOT output `commits` or `category` fields. Python fills these deterministically in post-processing.

## Special cases
- Binary files marked [Binary file -- cannot show diff]: describe the change, mark confidence: low. Use type chore for build artifacts, feat/fix for firmware/tools.
- Submodules expanded into real files with prefixed paths: treat like normal files. Uncloned or newly added submodules: mention the change but mark confidence: low.

## Scope
Include ALL changes: source, tests, CI/CD, docs, config, deps. Use the appropriate type (test, ci, chore, docs) for non-feature changes. Downstream consumers decide which types to include in their output (changelog, release notes, dev summary). This skill captures everything.

Only skip: lock files / generated code (listed in `## Skipped files`).

## Self-check before writing output
1. type matches what the diff shows, not the commit log?
2. confidence: high only when diff and a commit message agree?
3. breaking: true only when verified from diff? Has migration field?
4. No changes missed? (re-scan diffs for changes not yet captured)
5. Files with multiple change regions (shown in header as "K change regions"): did you capture changes from ALL regions, not just the largest?
6. Every `## File:` header in this chunk is covered by at least one YAML entry's files list?
7. No duplicates (same behavior described twice)? Distinct mechanisms in the same file are separate items, not duplicates.
8. description is end-user perspective? No file names or technical jargon?
9. detail has technical specifics (component names, mechanisms)? No vague user language?
10. files lists ALL affected paths for each change? No abbreviated or representative subsets?
11. No `commits` or `category` fields in output? (Python adds these)

## Output

Write YAML to `{output_path}` in this exact format. Do NOT include `commits` or `category` fields (Python adds them):

```yaml
# Change Summary: {range}
# Project: {project}
# Suggested bump: major | minor | patch

changes:
  - type: feat
    description: Humidity sensor support with readings in USB exports
    detail: >
      Added HumiditySensor handling in SensorManager, dedicated naming
      index separate from temperature sensors, humidity columns in USB
      CSV export via DataExport module.
    files: [src/SensorManager.c, src/DataExport.c, src/SensorNames.c]
    confidence: high

  - type: fix
    description: Sensor data no longer overwrites unprocessed frames
    detail: >
      Radio data is now only fetched when the previous frame has been
      consumed, preventing overwrites mid-calibration cycle.
    files: [src/Sensor.c]
    confidence: medium
    note: commit log said "fix calibration" but actual change is a data reception guard

  - type: fix
    description: Sensor readings validated against configured channel type
    detail: >
      Incoming sensor values are now rejected when the reported type
      does not match the channel configuration, preventing cross-type
      data corruption.
    files: [src/SensorData.c]
    confidence: medium
    note: not mentioned in commit log, identified from diff

  - type: feat
    breaking: true
    description: API response format changed to camelCase
    detail: >
      TaskifyClient._parse_response now applies to_camel_case to all
      response dictionary keys before returning.
    files: [src/api.py]
    confidence: high
    migration: Regenerate API clients, update parsers

  - type: test
    description: Unit tests added for sensor manager validation logic
    detail: >
      New test cases in SensorManager_ut.c covering type-mismatch rejection
      and frame overwrite prevention.
    files: [tests/SensorManager_ut.c]
    confidence: high

  - type: ci
    description: CI pipeline updated to run integration tests on merge
    detail: >
      Added integration-test stage to .gitlab-ci.yml, triggered on master merges.
    files: [.gitlab-ci.yml]
    confidence: high
```

Suggested bump: any breaking -> major, else any feat -> minor, else -> patch.
Sort changes by significance (features and fixes first, then tests, CI, docs, chore).
