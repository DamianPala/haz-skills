The diff has been split into {chunk_count} chunks. Per-chunk interpretation prompts have been pre-generated. Each is a standalone prompt with all interpretation rules and its chunk file path baked in.

## Chunk prompt files
{chunk_prompt_list}

## Dispatch

For each chunk prompt file, run in the background:

```bash
acpc prompt {agent} --input-file <prompt-file> --model standard --permissions write --quiet &
```

Launch ALL chunks in parallel. Then `wait` for all to complete.

Do NOT process chunks yourself. Do NOT read the chunk data files directly.

## Verify outputs

After all processes complete, check that each chunk produced its output file:

```bash
ls -lh {workdir}/changes-chunk-*.yaml
```

Report: "Interpret done: N/M chunks interpreted" with file sizes.

### Retry on failure

If any chunk output is missing:
1. Re-run the failed chunk's acpc command (same args, not in background)
2. If it fails again, report which chunk(s) failed and stop. Do not continue with partial results.
