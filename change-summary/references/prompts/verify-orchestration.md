Per-chunk verification prompts have been pre-generated. Each verifies the interpretation of its own chunk against the raw diff.

## Chunk verify prompt files
{chunk_prompt_list}

## Dispatch

For each chunk verify prompt file, dispatch a background acpc session from the repository root:

```bash
acpc run {agent} --prompt-file <prompt-file> --permissions execute --bg --quiet
```

Each call prints the session id. Launch ALL chunks first, then wait for every id:

```bash
acpc wait <session-id> --timeout 1800
```

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
