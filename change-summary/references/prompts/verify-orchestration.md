Per-chunk verification prompts have been pre-generated. Each verifies the interpretation of its own chunk against the raw diff.

## Chunk verify prompt files
{chunk_prompt_list}

## Dispatch

For each chunk verify prompt file, run in the background:

```bash
acpc prompt {agent} --input-file <prompt-file> --model standard --permissions write --quiet &
```

Launch ALL chunks in parallel. Then `wait` for all to complete.

Do NOT verify changes yourself. Do NOT read the chunk data files directly.

## Collect results

After all processes complete, read all `{workdir}/verify-chunk-*-result.txt` files.

Report: "Verify done: results" followed by each chunk's verdict (PASS or issue summary).

If ALL say "PASS": write "PASS" to `{workdir}/verify-result.txt`.
Otherwise: collect all issues and write them to `{workdir}/verify-result.txt`, one per line.

### Retry on failure

If any verify result file is missing:
1. Re-run the failed chunk's acpc command (same args, not in background)
2. If it fails again, report which chunk(s) failed and stop. Do not continue with partial results.
