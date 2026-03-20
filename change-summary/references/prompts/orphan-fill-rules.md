The files below were NOT covered by any entry in the initial interpretation pass. Your job is to describe the changes in these files. They may be small standalone changes, or parts of a larger feature that was partially captured.

## Format reference
- `## File: '<path>' [file-type, status, +N/-M]` or `## File: '<path>' [file-type, status, +N/-M, K change regions]` with unified diff per file

## Interpretation rules

For each file (or group of related files), create a YAML entry:

1. Read each file's diff carefully. Determine what changed and why.
2. Group related orphan files into one entry if they are part of the same logical change.
3. For each change determine:
   - type: feat / fix / refactor / perf / docs / chore / revert / style / test / ci / build
     Decide from the code diff alone.
   - breaking: true only when verified from diff (deleted public API, changed interface)
   - description: one sentence, END USER perspective. No file names, no jargon.
   - detail: technical description for developers. Component names, mechanisms, specifics.
   - files: list ALL file paths from the `## File:` headers that belong to this change
   - confidence: high / medium / low
   - note: (when confidence < high) explain your inference
   - migration: (breaking changes only) what users need to do

   Do NOT output `commits` or `category` fields. Python fills these.

## Self-check
1. Every `## File:` header is covered by at least one YAML entry's files list?
2. type matches what the diff shows?
3. description is end-user perspective? detail has technical specifics?
4. No `commits` or `category` fields in output?

## Output

Write YAML to `{output_path}` in this exact format:

```yaml
changes:
  - type: feat
    description: End-user description of the change
    detail: >
      Technical details about what changed in the code.
    files: [path/to/file.c]
    confidence: high
```

Sort changes by significance (features and fixes first, then tests, CI, docs, chore).
