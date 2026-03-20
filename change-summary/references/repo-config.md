# Per-repo configuration

The change-summary script reads optional configuration from the repo's `AGENTS.md` file. Add a `## change-summary` section with a fenced YAML block.

This config controls **submodule diff output size**, not which changes are analyzed. All changes (including from summarized submodules) are still interpreted by the LLM. Ignored submodules produce no diff output at all.

## Format

```markdown
## change-summary

```yaml
submodules:
  ignore:
    - vendor/some-sdk
  summarize:
    - libs/shared-components
```
```

## Submodule modes

| Mode | What the script does | Output |
|------|---------------------|--------|
| `ignore` | Skips entirely, no output | Nothing |
| `summarize` | Runs `git log --oneline` inside the submodule for the changed range | `## Submodule: '<name>' [updated, N commits]` + commit list |
| _(default)_ | Expands full per-file diff | `## File:` headers with unified diff (can be very large) |

### When to use each mode

- **ignore**: Vendor/third-party code that produces huge diffs without adding analytical value (e.g. SDK drivers, 70k+ lines per update). Saves token budget.
- **summarize**: Your own libraries or shared components where commit messages carry enough information. The LLM gets the commit log without reading every line of diff.
- **default**: Small submodules or submodules where you need full diff analysis. No config needed.

## Examples

**Embedded firmware** (large vendor SDKs):
```yaml
submodules:
  ignore:
    - drivers/vendor-hal     # 70k+ lines per update, no analytical value
  summarize:
    - libs/framework         # own code, commit messages are informative
```

**Monorepo with shared libs:**
```yaml
submodules:
  ignore:
    - third-party/protobuf   # generated code, huge diffs
  summarize:
    - packages/common        # shared utils, commit log is enough
```

## How it works

1. The Python script reads `AGENTS.md` from the repo root
2. Finds the `## change-summary` section (case-insensitive heading match)
3. Extracts the first fenced YAML block within that section
4. Parses `submodules.ignore` and `submodules.summarize` lists
5. During diff collection, ignored submodules are skipped, summarized ones get `git log` output instead of full diff

If `AGENTS.md` doesn't exist or has no `## change-summary` section, all submodules use the default mode (full diff).
