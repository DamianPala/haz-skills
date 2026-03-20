You are deduplicating a merged change summary YAML. The file was produced by multiple independent LLM workers interpreting different chunks of the same diff. Some changes may describe the same logical feature from different files.

## Input

Read the merged changes file: `{changes_path}`

## Task

Find and merge near-duplicate entries. Two entries are near-duplicates when:
- They describe the same logical change from different perspectives or file subsets
- Their descriptions convey the same behavior change with different wording
- They would confuse a reader who sees both as if they were separate changes

Two entries are NOT duplicates when:
- They affect the same file but describe different independent changes
- They are related but independently meaningful (e.g., a feature and its tests)

## Rules

1. Read all entries first. Identify clusters of near-duplicates.
2. For each cluster, merge into a single entry:
   - Combine `files` lists (union, no duplicates)
   - Pick the best `description` (most clear, end-user perspective)
   - Merge `detail` fields (combine technical specifics from both)
   - Keep the more specific `type` (feat > refactor > chore)
   - Keep `breaking: true` if any entry in the cluster has it
   - Keep `confidence: high` if any entry has it
   - Combine `commits` lists if present (union)
3. Leave non-duplicate entries unchanged. Do not modify their wording.
4. Do not remove entries that are merely related but independently meaningful.
5. Preserve YAML header comments (# Change Summary, # Project, # Suggested bump).

## Output

Write the deduplicated YAML to `{output_path}`. Same format as input, just with duplicates merged.

## Self-check
1. Every file from the input is still present in at least one entry?
2. No two entries describe the same logical change?
3. No entries were removed that were independently meaningful?
4. Header comments preserved?
