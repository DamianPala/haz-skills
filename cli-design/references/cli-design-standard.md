# CLI Design Standard for Humans and Agents

> **Version:** 0.1.0-draft.3
>
> **Status:** Working draft. This document is not yet a conformance target.

## Scope

This document defines the contract for greenfield command-line tools and brownfield tools being adapted for reliable use by people and software agents. It includes human-facing behavior, machine-readable introspection, and the minimum safety contract for repeated and mutating operations.

The standard is independent of the operating system, shell, implementation language, framework, and backend. Arguments, standard streams, environment variables, exit codes, and TTY refer to the equivalent process interfaces on each platform. Command examples use POSIX-like notation for readability and are non-normative.

Brownfield tools and compatibility wrappers MAY preserve established behavior when changing it would break existing callers. A retained incompatible path MUST be documented and MUST NOT be presented as conforming. The tool MAY claim conformance only when it provides a documented conforming path for the same operation.

## Conformance

A conforming tool MUST satisfy every applicable requirement in this standard.

A conformance claim MUST identify the standard version.

A conditional requirement applies only when its stated condition is true.

Tests and conformance tools can verify these requirements, but this document remains authoritative if they disagree.

## Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals. Synonymous BCP 14 terms are not used.

## Maintenance

The non-normative [maintenance guide](cli-design-standard-maintenance.md) defines the admission policy and verification workflow for changes to this standard. It is not part of conformance.

## Stage D: Discovery and introspection

A caller should be able to choose a command and construct a valid call without reading source code or probing commands that may change state.

- **D1: Published interfaces MUST match actual behavior.** Help, schema, documentation for the installed tool version, and shipped agent guidance MUST agree with the tool and with each other.

- **D2: Discovery has three layers.** `--help` MUST provide the quick start, and `tool schema` MUST provide the exact contract. `SKILL.md` or `AGENTS.md` MAY add domain or workflow context when the first two layers are not enough.

- **D3: Root `--help` MUST be a standalone cheat sheet.** It MUST state the tool's purpose, list its commands or groups, and point to `tool schema`. When any command returns success data beyond its exit status, root help MUST also point to `--json` under O2. It SHOULD show non-obvious common workflows as literal invocations. Each command MUST provide `--help` that states its purpose and usage and describes its arguments, command-specific flags, and applicable defaults. When the command list grows, help MUST group commands rather than omit them.

- **D4: Speak the shared vocabulary.** Related commands MUST follow a predictable structure (`tool <noun> <verb>` or `tool <verb>`). For equivalent operations, greenfield commands SHOULD prefer `get`, `list`, `create`, and `delete` to `info`, `ls`, and `add`; managed-operation commands SHOULD use `status`, `wait`, and `cancel`, plus `pause` and `resume` for resumable suspension. A canonical flag name MUST keep the same meaning wherever it appears; aliases MAY remain for compatibility. Root `--version` MUST exist. Brownfield names MAY remain for compatibility.

- **D5: A workflow with one unambiguous next step SHOULD expose it as a breadcrumb.** In structured output, `next` MUST be a non-empty array of strings forming a complete argv vector that can be executed without a shell. A command that may emit `next` MUST declare it as an optional field in its D8 output schema. Human-readable output SHOULD render the same invocation as `Next: ...` and safely quote caller-controlled values. Output MUST omit `next` when there is no natural continuation.

  ```console
  $ mytool deploy service-a
  Deployment queued: dep_123
  Next: mytool deployments wait dep_123
  ```

  ```json
  {
    "deployment_id": "dep_123",
    "status": "queued",
    "changed": true,
    "next": ["mytool", "deployments", "wait", "dep_123"]
  }
  ```

- **D6: `tool schema` MUST expose the command interface as JSON.**

  - Consistency: command paths, arguments, flags, and defaults exposed by schema MUST match the parser used at runtime. Shared definitions, generation, and conformance tests are all valid ways to enforce this.
  - Execution: schema MUST write only JSON to stdout and require no application authentication, configuration, network access, or prompts.
  - Routing: `tool schema` MUST return the D7 index, and a command path MUST return D8 detail. Each segment of a command path MUST be passed as a separate argument in the order shown by D7 `commands[].name`.
  - Errors: an unknown path MUST be a usage error and name the nearest valid paths.

- **D7: The schema index MUST let callers choose a command safely.** It MUST contain the following fields.

  | Field | Type | Contract |
  |---|---|---|
  | `schema_version` | string | Introspection format version. |
  | `tool_version` | string | Value reported by `--version`. |
  | `detail` | string | Command template; replace `<command>` with the full command path as separate arguments. |
  | `global_flags` | array | I1 flag descriptors accepted by every command. D8 `flags` MUST NOT repeat them. |
  | `format_defaults` | object | O2 default format for each output context. |
  | `exit_codes` | object | F1 tool-wide exit code meanings. |
  | `errors` | object | F2-F3 structured error contract. |
  | `commands` | array | Sorted, flat routing list of every invocable command by full path; excludes `schema`. |

  Each command entry MUST contain `name`, `description`, and `effects`, and MUST NOT contain invocation details. `description` MUST distinguish neighboring commands, and `effects` MUST follow R1. Command detail, not the index, MUST contain enough information to construct a call.

- **D8: Command detail MUST expose the command contracts.**

  Fields marked `always` MUST be present. A conditional field MUST be present when its condition is true and MUST NOT be present otherwise.

  | Field | JSON type | Presence | Contract |
  |---|---|---|---|
  | `name` | string | always | Full command path. |
  | `description` | string | always | One-line purpose. |
  | `args` | array | always | I1 positional argument descriptors. |
  | `flags` | array | always | I1 command-specific flag descriptors. Effective flags are D7 `global_flags` plus this array. |
  | `effects` | string | always | MUST equal `read_only`, `idempotent`, or `non_idempotent` as defined by R1. |
  | `confirm` | boolean | always | MUST be `true` when any valid call may require `--yes`; see R3. |
  | `interactive` | boolean | always | MUST be `true` when any valid invocation starts an I5 interactive session and `false` otherwise. |
  | `stream` | boolean | success emits a record stream | MUST be `true`. `output` describes one record; see O7. |
  | `output` | object | success conveys data beyond the exit status, or R5 applies | O4 JSON Schema for the success document or one O7 record. |
  | `exit_codes` | object | adds or refines tool defaults | F1 additions or refinements that preserve tool-wide meanings. |
  | `format_defaults` | object | differs from tool default | O2 output defaults. |

#### Example

This non-normative example shows how the index and command detail fit together. D7 and D8 define the contract.
Fields follow the table order for readability; JSON object order is not part of the contract.

```console
$ mytool schema
```

```json
{
  "schema_version": "1",
  "tool_version": "2.1.0",
  "detail": "mytool schema <command>",
  "global_flags": [
    {
      "name": "json",
      "description": "Emit JSON output",
      "type": "boolean",
      "required": false,
      "default": false
    },
    {
      "name": "verbose",
      "description": "Show diagnostic details",
      "type": "boolean",
      "required": false,
      "default": false
    }
  ],
  "format_defaults": {"tty": "text", "non_tty": "json"},
  "exit_codes": {"0": "success", "1": "failure", "2": "usage error"},
  "errors": {"channel": "stderr", "position": "last_line", "format": "json"},
  "commands": [
    {"name": "deploy", "description": "Deploy a service", "effects": "non_idempotent"},
    {"name": "services list", "description": "List deployed services", "effects": "read_only"}
  ]
}
```

```console
$ mytool schema deploy
```

```json
{
  "name": "deploy",
  "description": "Deploy a service to an environment",
  "args": [
    {
      "name": "service",
      "description": "Service to deploy",
      "type": "string",
      "required": true
    }
  ],
  "flags": [
    {
      "name": "env",
      "description": "Target environment",
      "type": "string",
      "required": true,
      "enum": ["dev", "staging", "prod"]
    },
    {
      "name": "manifest",
      "description": "Manifest file or - for stdin",
      "type": "string",
      "required": false,
      "accepts_stdin": true
    },
    {
      "name": "yes",
      "description": "Confirm the deployment",
      "type": "boolean",
      "required": false,
      "default": false
    }
  ],
  "effects": "non_idempotent",
  "confirm": true,
  "interactive": false,
  "output": {
    "type": "object",
    "required": ["deployment_id", "status", "changed"],
    "properties": {
      "deployment_id": {"type": "string"},
      "status": {
        "type": "string",
        "enum": ["queued", "running", "succeeded", "failed"]
      },
      "changed": {"type": "boolean"},
      "warning": {"type": "string"},
      "next": {
        "type": "array",
        "items": {"type": "string"}
      }
    }
  }
}
```

`deploy` inherits tool-wide exit codes and format defaults, so it omits both fields.

- **D9: The introspection contract MUST be stable and versioned.** `schema_version` MUST be a positive decimal integer encoded as a string. Callers should ignore unknown fields. Adding optional introspection or output fields MAY keep `schema_version`; removing an introspection field or changing its type or meaning MUST increment it. Tool versions documented as compatible MUST preserve existing command paths, input meanings and defaults, exit code meanings, and structured output fields. An incompatible change MUST document its replacement and migration; changing `schema_version` alone is insufficient.

- **D10: Agent guidance MUST add context, not repeat the interface.** The tool MAY ship `SKILL.md` or `AGENTS.md` when domain knowledge or workflows need explanation. Guidance MUST point to commands and schema, and MUST NOT duplicate their catalogs.

## Stage I: Invocation and input

A caller may be a sandboxed process with no keyboard, a producer of generated bytes, or both. Input handling treats those bytes as data, not shell syntax. The tool resolves declared inputs, validates them before acting, and keeps external work bounded.

- **I1: Every accepted argument and flag MUST have a defined input contract.** D7 `global_flags` and D8 `args` and `flags` MUST expose it as a descriptor.

  | Field | Type | Rule |
  |---|---|---|
  | `name` | string | MUST be present. Flag names omit leading hyphens; one character renders as `-n`, while longer names render as `--name`. |
  | `description` | string | MUST be present. One line stating what the input controls. |
  | `type` | string | MUST be present and equal `string`, `integer`, `number`, or `boolean`. |
  | `required` | boolean | MUST be present. `true` means the caller must provide the input. |
  | `default` | scalar or array | MUST be present when the parser supplies an actual default. Scalar defaults MUST match `type`; variadic and repeatable defaults MUST be arrays whose items match `type`. Required inputs MUST NOT have a default. |
  | `enum` | array | MUST be present and list every choice when the parser declares a closed choice set. Every item MUST match `type`. |
  | `aliases` | array | MAY appear on flags and contain alternative names without leading hyphens. Alias rendering follows `name`. |
  | `variadic` | boolean | MAY be `true` only on the last argument. It consumes the remaining positional values as an ordered array; with `required: true`, it consumes at least one. |
  | `repeatable` | boolean | MAY be `true` only on flags. It allows repeated occurrences and resolves their values to an ordered array. |
  | `accepts_stdin` | boolean | MUST be `true` when `-` selects stdin instead of a file. |

  Arguments MUST appear in invocation order. Omitted `variadic`, `repeatable`, and `accepts_stdin` mean `false`; omitted `aliases` means no aliases. A parser sentinel meaning "not provided", including `null`, is not a default and MUST be omitted.

  Any accepted value syntax, bound, path-resolution rule, dependency, conflict, or dynamic value-discovery path not expressed by another descriptor field MUST be stated in `description`.

  Example descriptors:

  - Argument: `{"name": "file", "description": "Files to upload", "type": "string", "required": true, "variadic": true}`
  - Flag: `{"name": "tag", "description": "Tag to attach", "type": "string", "required": false, "aliases": ["t"], "repeatable": true}`

  Together they accept `mytool upload --tag docs -t archive a.txt b.txt` and resolve both `file` and `tag` to ordered arrays.

- **I2: Configuration MUST be declared, deterministic, and inspectable.**

  - Sources: accepted configuration files and tool-specific environment variables MUST be documented, and an undeclared tool-specific variable MUST NOT change behavior. Greenfield variables SHOULD use a consistent `<TOOL>_<OPTION>` prefix, such as `MYTOOL_LOG_LEVEL`. If a flag selects a configuration file, the tool MUST document whether that file replaces or augments project and user configuration and where it sits in the precedence.
  - Precedence: when more than one source provides a value, resolution MUST be deterministic and documented. Greenfield tools SHOULD use:

    `flags > environment > project configuration > user configuration > built-in defaults`

  - Inspection: layered configuration SHOULD expose each resolved value and its source while masking secrets.

  Example: `--log-level debug` overrides `MYTOOL_LOG_LEVEL=info`, which overrides `log_level = "warning"` in project configuration and `log_level = "error"` in user configuration.

- **I3: Long or generated input MUST use files or stdin, never argv.** A command that accepts a document, script, request body, template, or other unbounded text MUST accept a file path and `-` for stdin. An input that accepts `-` MUST contain `accepts_stdin: true` in its I1 descriptor. The tool MUST reject a call that selects stdin for more than one input.

  The same manifest can come from a file or stdin. Its quotes, newlines, and flag-like text remain data rather than argv:

  ```console
  $ mytool deploy service-a --manifest manifest.json
  $ mytool deploy service-a --manifest - < manifest.json
  ```

- **I4: Secrets MUST NOT be passed as argument or flag values.** A command that needs a secret MUST provide a non-interactive source such as a credential store, file, stdin, or environment variable. Greenfield tools SHOULD use `--token-file PATH` for one secret and `--credentials-file PATH` for structured credentials; either flag SHOULD accept `-` for stdin. Secret sources and their precedence MUST be documented. A secret MUST NOT appear in help, schema, logs, errors, or normal output unless retrieval is the command's documented purpose.

- **I5: Non-interactive behavior MUST be explicit and fail safely.**

  - Prompts: a command MAY prompt only when stdin is a TTY and the selected stdout format is human-readable. Otherwise, it MUST NOT prompt. If required input or confirmation remains unresolved, it MUST fail with an error that names a flag, file, stdin form, or environment variable that can supply it. The absence of a permitted prompt MUST NOT be treated as consent.
  - Interactive sessions: a command MAY start an interactive session only when stdin and stdout are TTYs and the selected stdout format is human-readable. It MUST fail before side effects otherwise. A command that offers such a session MUST declare `interactive: true` in D8.
  - Human action: a workflow MAY require an out-of-band human action. Its non-interactive entry point MUST be discoverable through D7 and D8. Work that continues after that command exits follows Stage M.
  - Paging: a pager MAY start only when stdout is a TTY and the selected format is human-readable; see H3.

- **I6: Invalid input MUST fail before side effects.** The tool MUST reject unknown flags, unsupported arguments, invalid values, and conflicting inputs as usage errors. `--` MUST end option parsing; later tokens MUST NOT be interpreted as flags. The tool MUST validate every locally checkable input before changing state. The error SHOULD identify the invalid input and show the accepted form or nearest valid name.

- **I7: Input MUST stay within its declared bounds.**

  - Buffered data: a command that buffers caller-controlled input MUST document and enforce a maximum size before side effects.
  - Restricted paths: a command limited to declared roots MUST resolve each supplied path and reject it when it escapes those roots, including through `..` or a symbolic link.

  For example, assume `mytool upload` accepts at most 10 MiB and may read files only from `./dist`:

  ```console
  $ mytool upload ../secrets.txt
  {"error":{"kind":"invalid_input","message":"Path must resolve inside ./dist"}}

  $ cat 20-mib.bin | mytool upload -
  {"error":{"kind":"invalid_input","message":"Input exceeds the 10 MiB limit"}}
  ```

- **I8: External work MUST be bounded or explicitly unbounded.** Connection establishment and non-streaming network operations MUST use finite default timeouts. A command that waits for external state without waiting being its documented purpose MUST use a finite default deadline. A command whose documented purpose is to wait, watch, follow, or run external work to completion MAY be unbounded by default, but MUST accept `--timeout` and declare that default. Any other unbounded mode MUST require explicit selection.

  For a tool whose documented duration syntax accepts unit suffixes:

  ```console
  $ mytool jobs wait job_123 --timeout 5m
  $ mytool logs job_123 --follow
  ```

  The first call sets a deadline. The second explicitly selects an unbounded mode.

## Stage R: Repeatability and mutation safety

This stage covers calls that mutate state or may be repeated. Safeguards follow the possible damage, not merely whether a command changes state.

- **R1: Effect metadata MUST be conservative.** Every D7 command entry and D8 command detail MUST declare one value:

  | `effects` | Contract |
  |---|---|
  | `read_only` | The command does not change intended state managed or targeted by the tool. |
  | `idempotent` | The command may change intended state, but repeating a successful call with the same inputs MUST succeed without another intended state transition. |
  | `non_idempotent` | The command meets neither preceding guarantee; a repeat may cause another intended effect or return a stable conflict. |

  The declaration MUST cover every valid invocation. Use `non_idempotent` if any invocation lacks the repeat guarantee; otherwise use `idempotent` if any invocation can change intended state, and `read_only` otherwise. A changing response, incidental telemetry, logs, caches, metering, or rate limiting do not alone change the classification.

- **R2: Mutation safeguards MUST match the blast radius.** A mutation is wide when it can affect targets the caller did not name individually. It is irreversible when the tool provides no documented operation that restores the prior state. Idempotence does not reduce these safeguards:

  | Operation | Minimum safeguard |
  |---|---|
  | `effects: "read_only"` | None |
  | Narrow, reversible mutation | None |
  | Narrow, irreversible mutation | Explicit `--yes` in non-interactive use |
  | Wide mutation | Explicit `--yes` and R4 preview |

  An M3 cancellation of exactly one managed operation by its M1 identifier does not require an additional confirmation. Any wider cancellation follows the table.

- **R3: Safety gates MUST fail closed and be discoverable.** Every command that can require `--yes`, including those required by R2, MUST declare `confirm: true` in D8. Without `--yes`, a non-interactive call MUST stop before side effects and name the gate. `--yes` confirms a prompt; `--force` overrides a documented precondition. Accepting one MUST NOT enable the other.

- **R4: Wide mutations MUST be previewable.** The command MUST provide `--dry-run`, which reports the planned targets and effects without changing state.

- **R5: Mutating commands MUST report what happened.**

  - Every command whose `effects` is not `read_only` MUST declare a boolean `changed` in its D8 output and return it in every structured success response. `changed` reports whether this invocation caused a new intended state transition, not whether background work completed.
  - When authoritative state reports a concurrent conflict, the CLI MUST return a stable conflict error and MUST NOT silently overwrite it.
  - A `non_idempotent` command whose repetition could duplicate an effect SHOULD accept `--idempotency-key` when the backing service supports idempotency keys.

  For example, an idempotent create-or-get may return `changed: true` and then `changed: false`. A strict create may return `changed: true` and then a stable conflict.

- **R6: Built-in retries MUST be safe and bounded.** A CLI that retries requests internally:

  - MUST retry only failures that would be reported with `retryable: true` under F3, and only for `read_only` or `idempotent` commands, or requests protected by an idempotency key;
  - MUST preserve the original inputs, limit the number of attempts, and remain within the I8 timeout;
  - SHOULD honor `Retry-After` when the timeout allows.

## Stage O: Output

A caller should be able to select a representation before execution, parse stdout without filtering diagnostics, and consume large results without mistaking one page for the whole result.

- **O1: The standard streams MUST be classified independently.** The TTY state of stdin controls prompt policy under I5, stdout controls the default format under O2, and stderr controls diagnostic decoration under O3. Redirecting one stream MUST NOT change how another is classified.

- **O2: Output format selection MUST be explicit and predictable.**

  - Declaration: D7 `format_defaults` MUST declare `tty` and `non_tty` format names. D8 `format_defaults` MUST appear only when a command differs from those tool-wide defaults.
  - Machine access: every command with D8 `output` MUST accept `--json`. If it also accepts `--format`, `--json` MUST produce the same output as `--format json` for documents and `--format ndjson` for streams.
  - Defaults: a greenfield command with D8 `output` SHOULD default to human-readable output on a TTY. On non-TTY stdout, structured data MUST default to JSON or NDJSON. A command whose primary result is a textual document rather than a set of fields or records MAY default to a declared native format such as text or Markdown. A brownfield command MAY retain an established non-TTY default when it is stable, parseable, and declared.
  - Precedence: an explicit format flag MUST override the detected default. Conflicting explicit format flags MUST be usage errors.
  - Names: a greenfield tool MUST NOT define `--output`. If it accepts a destination path, the flag MUST be named `--output-file`. Formats use `--json` or `--format`.

- **O3: The output streams MUST have separate roles.**

  - Channels:
    - stdout MUST contain only the result.
    - stderr MUST carry logs, warnings, and progress.
  - Decoration:
    - Machine-readable stdout MUST contain only the selected representation, without banners, terminal decoration, or ANSI escapes.
    - Terminal decoration MAY appear only when its stream is a TTY or a documented flag or environment variable forces it.
    - Animated progress MAY appear only when stderr is a TTY.
    - On non-TTY stderr, progress MUST use complete plain lines or be omitted.
  - Consistency:
    - Human and machine renderings MAY differ in detail.
    - They MUST NOT contradict each other.
    - When human-readable output is only a bounded preview of the result, it MUST say so and identify how to retrieve the complete result.
  - Untrusted content:
    - Machine output MUST serialize caller-controlled and remote values through the selected format.
    - Human output MUST escape terminal control sequences in those values.

- **O4: A command schema MUST describe its JSON success value.** The D8 `output` field describes one success document, or one record when D8 declares `stream: true`. It MUST follow JSON Schema Draft 2020-12 and use only `type`, `enum`, `properties`, `required`, and `items`. The dialect is fixed by this requirement, so `output` MUST NOT contain `$schema`.

  - Every schema MUST contain `type`. It MUST be `string`, `integer`, `number`, `boolean`, `array`, or `object`, or a two-element array containing one of those types and `null`.
  - `enum` MAY restrict a value to a finite set. Every member MUST conform to the same schema.
  - An array schema MUST contain `items`. An object schema MUST contain `properties`, which lists every field the current version may return, and `required`, which lists every always-present field.

  Example schema:

  ```json
  {
    "type": "object",
    "required": ["job_id", "status", "progress"],
    "properties": {
      "job_id": {"type": "string"},
      "status": {
        "type": "string",
        "enum": ["queued", "running", "succeeded", "failed", "unknown"]
      },
      "progress": {"type": ["number", "null"]},
      "warnings": {
        "type": "array",
        "items": {"type": "string"}
      }
    }
  }
  ```

- **O5: JSON output MUST match its declared contract.**

  - Document: unless D8 declares `stream: true`, a `--json` success MUST contain exactly one JSON value conforming to the D8 `output` schema, encoded as UTF-8 and followed by LF. A failed document call MUST NOT leave an incomplete or invalid JSON value on stdout.
  - Values: values MUST keep their declared JSON types. Machine output MUST NOT silently truncate a value.
  - Bounded values: a command that may cap a single inline value MUST declare a required boolean `truncated` and an optional string `output_file` in its D8 output schema. Every result MUST return `truncated`. When it is `true`, `output_file` MUST identify a caller-readable file containing the complete value, the inline value is a preview, and the file's retention MUST be documented. Collections and record streams MUST use O6 and O7 instead.
  - Time: timestamps MUST use RFC 3339 with an explicit offset. Numeric duration field names MUST state their unit.

  Matching output:

  ```json
  {
    "job_id": "job_123",
    "status": "running",
    "progress": 0.4,
    "warnings": []
  }
  ```

  A bounded single value may instead report:

  ```json
  {
    "answer": "First part of the answer...",
    "truncated": true,
    "output_file": "/tmp/mytool/results/job_123.md"
  }
  ```

- **O6: Potentially unbounded document collections MUST be bounded and continuable.**

  - Window: a collection without a documented finite maximum MUST use a finite default limit and accept `--limit` and `--cursor`.
  - Continuation: each JSON page MUST contain an `items` array and `next_cursor`. The cursor MUST be an opaque string that the caller passes unchanged to `--cursor`, or `null` on the final page.
  - Resume: source, filters, and order MUST remain unchanged when using `--cursor`; the limit and output format MAY change. If the cursor is invalid, expired, incompatible, or cannot continue the same result set, the command MUST fail with non-zero exit and F3 `kind` `cursor_unavailable`. It MUST NOT silently restart from another position.
  - Stability: pagination MUST use a stable, documented order and document whether pages read live state or one fixed snapshot. The tool MUST bound the number of items, not silently omit fields from individual items.
  - Shape: a collection with a documented finite maximum MAY use a bare array. An empty collection MUST use the same shape with an empty array, not `null` or absent output.

  ```console
  $ mytool jobs list --limit 2 --json
  ```

  ```json
  {
    "items": [
      {"id": "job_123", "status": "running"},
      {"id": "job_456", "status": "queued"}
    ],
    "next_cursor": "cur_abc123"
  }
  ```

- **O7: Record streams MUST be bounded, framed, and resumable.** For a command with D8 `stream: true`, `output` MUST be an object schema with `cursor` as a required string property.

  - Framing: `--json` MUST emit UTF-8 NDJSON with one complete JSON object per LF-terminated line and no blank lines. Each record MUST conform to D8 `output` and become readable before the command waits for another record or exits. O5 value and time rules and D9 compatibility rules apply to each record.
  - Window: without `--follow`, the command MUST terminate. A stream without a documented finite maximum MUST use a finite default limit and accept `--limit`. `--follow` removes that default limit. An explicit `--limit` remains effective with or without `--follow` and ends the read after that many records. Reaching a limit ends that read, not the record source.
  - Ordering: the stream MUST use a stable, documented order and MUST NOT stop before the effective limit while matching records are available.
  - Continuation: each `cursor` MUST be a non-empty opaque string. The command MUST accept `--after-cursor` and resume strictly after that record without skipping any matching record in the same logical stream. Inputs selecting the source, filters, or order MUST remain the same; limits, following, timeouts, and output format MAY change. If this continuation cannot be guaranteed because the cursor or required history is invalid, expired, or incompatible, the command MUST fail with non-zero exit and F3 `kind` `cursor_unavailable`; it MUST NOT silently resume elsewhere.
  - Following: a follow mode MAY exist, SHOULD be named `--follow`, and MUST require explicit selection under I8. Without an explicit `--limit`, it is unbounded.
  - Completion: exit `0` means the requested read ended successfully, not that the record source is exhausted; empty stdout is valid. After a non-zero exit, prior LF-terminated records remain valid and an unterminated final fragment is not a record. This standard defines no end record; EOF and the exit status are authoritative.

  Example command schema excerpt:

  ```json
  {
    "stream": true,
    "output": {
      "type": "object",
      "required": ["cursor", "timestamp", "level", "message"],
      "properties": {
        "cursor": {"type": "string"},
        "timestamp": {"type": "string"},
        "level": {
          "type": "string",
          "enum": ["debug", "info", "warning", "error"]
        },
        "message": {"type": "string"}
      }
    }
  }
  ```

  A bounded read and its continuation:

  ```console
  $ mytool logs job_123 --limit 2 --json
  {"cursor":"cur_101","timestamp":"2026-08-15T10:00:00Z","level":"info","message":"Started"}
  {"cursor":"cur_102","timestamp":"2026-08-15T10:00:01Z","level":"info","message":"Fetching input"}

  $ mytool logs job_123 --after-cursor cur_102 --limit 2 --json
  {"cursor":"cur_103","timestamp":"2026-08-15T10:00:04Z","level":"warning","message":"Retrying"}

  $ mytool logs job_123 --after-cursor cur_103 --follow --json
  {"cursor":"cur_104","timestamp":"2026-08-15T10:00:09Z","level":"info","message":"Recovered"}
  ```

  An unavailable cursor fails through F3 on stderr:

  ```json
  {"error":{"kind":"cursor_unavailable","message":"The cursor is no longer available","retryable":false,"action":"agent","hint":"Start a fresh read without --after-cursor"}}
  ```

  Non-normative note: cursor-based resume guarantees a continuation position, not exactly-once delivery. Persisting a cursor only after processing its record minimizes replay; a crash before that checkpoint may cause the record to be received again.

- **O8: Output MUST survive normal pipeline closure.** When a downstream reader closes a pipe, a command that has not otherwise failed MUST stop writing and emit no stack trace or broken-pipe diagnostic. Its exit status MAY follow the platform's pipe-closure convention; any non-zero meaning MUST be documented under F1.

## Stage F: Failure

Failures need a stable machine signal and enough information for the caller to choose its next action. Success must not hide incomplete or uncertain work.

- **F1: Exit codes MUST be stable and documented.**

  Tool-wide D7 `exit_codes` MUST contain these decimal-string keys:

  | Code | Meaning |
  |---|---|
  | `0` | Success, including an empty result or no differences. |
  | `1` | Generic failure. |
  | `2` | Usage error. |

  - Exit `0` MUST mean the command observed its documented postcondition through the interface it used. Independent re-verification is not required. For managed operations, acceptance and completion follow M1-M2.
  - Additional codes MUST each have one stable meaning. Fine-grained failures MUST use F3 `kind` instead.
  - D8 command `exit_codes` MUST appear only when they add a code or refine a tool-wide description without changing its meaning.

- **F2: The schema index MUST declare one structured-error location.** D7 `errors` MUST equal `{"channel":"stderr","position":"last_line","format":"json"}`. When the tool exits with an error, the last non-empty stderr line MUST be one F3 JSON object. Human-readable diagnostics MAY precede it.

- **F3: Structured errors MUST have a stable envelope.** The document MUST contain exactly one top-level field, `error`, whose value is an object. Its `kind` is the only stable match target; message text is not a stable interface.

  | Field | Presence | Contract |
  |---|---|---|
  | `kind` | MUST | String identifier with stable machine meaning. |
  | `message` | MUST | String identifying the failed operation and cause. |
  | `retryable` | MAY | Boolean. `true` only when the same invocation may resolve the failure without duplicating an intended effect. |
  | `action` | MAY | `agent` when the caller can recover autonomously, `user` when human action is required, or `none` when no recovery action exists. |
  | `hint` | SHOULD if one concrete recovery step is known | String recovery step; omit rather than guess. |
  | `context` | MAY | Object containing machine-readable values needed for recovery. |

  ```json
  {
    "error": {
      "kind": "image_not_found",
      "message": "Cannot deploy 'web-api': image 'web:v2.1.0' was not found",
      "retryable": false,
      "action": "agent",
      "hint": "Run mytool images list web",
      "context": {"service": "web-api", "image": "web:v2.1.0"}
    }
  }
  ```

- **F4: Fallbacks and uncertain outcomes MUST be explicit.**

  - If a failed command may have caused an intended effect and did not observe the outcome, it MUST use F3 `kind` `outcome_unknown` and MUST NOT report completion or absence. Known completed effects SHOULD be identified in `context`. O5 and O7 define which prior stdout remains valid.
  - If usable partial results survive a failure, the structured error SHOULD identify them in `context`.
  - After a failure, a command MUST NOT silently replace the requested target, source, or mode. It MUST fail through F2-F3 or identify the substitution in its declared structured result.

  ```json
  {"error":{"kind":"outcome_unknown","message":"The deployment request timed out and its outcome could not be determined","retryable":false,"context":{"deployment":"dep_123"}}}
  ```

- **F5: User interruption MUST fail honestly.** A command that receives the platform's normal user-interrupt request MUST exit without a stack trace and fail through F2-F3 with `kind` `interrupted`, unless F4 requires `outcome_unknown`. Interrupting observation of managed work MUST NOT cancel or otherwise change that work.

## Stage M: Managed operations

A managed operation is work that continues after the command that started it exits. A tool without such work has no Stage M requirements.

- **M1: Accepted work MUST remain identifiable.** A command that exits before requested work finishes MUST return a non-empty canonical identifier in structured success output. Its field name is tool-defined but MUST remain consistent across the command that starts the work and every command that addresses it. Exit `0` means the work was accepted, not completed. The identifier MUST remain usable after the initiating process exits and MUST NOT later resolve to a different entity. Its D5 breadcrumb SHOULD name the wait command.

  When a command offers both waiting for completion and returning after acceptance, selecting the latter MUST change only how long the command waits, not the work it starts. Its flag SHOULD follow H1.

- **M2: Managed work MUST expose status and wait.** The tool MUST provide non-interactive commands for inspecting current status and waiting for a terminal state. Both MUST accept the identifier returned under M1; D4 covers their names.

  - Both commands MUST declare `effects: read_only`.
  - The status command MUST report the current state without waiting for a terminal state.
  - Structured results from both commands MUST contain `status` and the identifier under the same field name. The D8 output schema MUST declare `status` as a finite enum containing terminal values `succeeded` and `failed`, plus `canceled` when cancellation exists. It MAY add values for unfinished states and MUST add `unknown` when an existing operation's current state can be indeterminate. `unknown` MAY be returned only when the tool successfully observes an underlying state that explicitly represents indeterminacy. A timeout, transport error, or other failure to read state MUST fail through F2-F3 and MUST NOT return `unknown`.
  - Any retention or expiry policy for managed operations MUST be documented. An unrecognized or expired identifier MUST fail through F2-F3 and MUST NOT be reported as an operation state.
  - The wait command MUST exit `0` when it successfully observes any terminal state. The operation outcome MUST be reported by `status` and MUST NOT change that exit code. Failure to observe the operation MUST fail through F2-F3.
  - The wait command MUST follow I8 and return immediately when the operation is already terminal. Timing out or terminating it MUST NOT cancel or otherwise change the operation, and MUST NOT be reported as a terminal operation outcome.

  Operation logs and events MAY supplement status and wait, but MUST NOT replace them.

- **M3: Cancellation MUST be honest.** If a managed operation can be canceled, the tool MUST provide a non-interactive cancellation command whose name follows D4. It MUST accept the identifier returned under M1, declare `effects: idempotent`, and follow Stage R. Structured success MUST contain `status` and the identifier under the same field name; R5 supplies `changed`. Exit `0` means cancellation was accepted or a terminal state was observed, not necessarily that the operation was canceled. The command MUST NOT report `canceled` until it observes that state; if the operation wins the race, it MUST report the actual terminal state.

  ```console
  $ mytool jobs status job_123 --json
  {"job_id":"job_123","status":"running"}

  $ mytool jobs cancel job_123 --json
  {"job_id":"job_123","status":"canceling","changed":true}

  $ mytool jobs wait job_123 --timeout 5m --json
  {"job_id":"job_123","status":"canceled"}
  ```

- **M4: Resumable suspension MUST remain distinct from cancellation.** If managed work can be suspended and later resumed from the same point, the tool MUST expose non-interactive suspension and resumption commands whose names follow D4. Both MUST accept the identifier returned under M1, declare `effects: idempotent`, and return the identifier, `status`, and `changed` in structured success. They MUST report only a status they observed. While suspended, `status` MUST be `paused` and non-terminal. Cancellation under M3 remains terminal and MUST NOT mean suspension.

## Stage H: Human interface

A person at the terminal should find familiar flag names, standard environment behavior, and output that remains readable without color.

- **H1: Greenfield flags MUST have canonical long names.** In a greenfield tool, flag names MUST use kebab-case and each concept MUST have one canonical long name. When the tool supports a concept below, it SHOULD use the listed long name. A listed alias MAY be added when it has no conflicting local meaning. Every accepted alias MUST behave exactly like its canonical flag and appear in the I1 descriptor.

  | Concept | Long name | Common alias | Related rule |
  |---|---|---|---|
  | Help | `--help` | `-h` | D3 |
  | Version | `--version` | `-V` | D4 |
  | More diagnostics | `--verbose` | `-v` | O3 |
  | Less diagnostics | `--quiet` | `-q` | O3 |
  | Preview a mutation | `--dry-run` | `-n` | R4 |
  | Override a named precondition | `--force` | `-f` | R3 |
  | Confirm a prompt | `--yes` | `-y` | R3 |
  | Select a configuration file | `--config PATH` | `-c PATH` | I2 |
  | Return after accepting managed work | `--background` | `--bg` | M1 |
  | Bound a wait | `--timeout DURATION` | No recommendation | I8, M2 |
  | Bound returned items or records | `--limit N` | No recommendation | O6, O7 |

  `-n` follows the established no-op and dry-run convention. `-d` and `-l` are too overloaded to recommend for dry-run or limit.

- **H2: Tools with nested commands SHOULD provide shell completions.** When provided, static command, flag, and alias candidates MUST match the installed interface.

- **H3: External editors and pagers MUST respect user selection.** A tool that starts an editor MUST prefer `VISUAL` to `EDITOR` unless a documented setting overrides them. A tool that starts a pager MUST honor `PAGER` unless a documented setting overrides it. I5 defines when a pager may start.

- **H4: Color MUST remain optional.** A tool that emits color MUST disable it when `NO_COLOR` is non-empty or the output stream is not a TTY, unless explicit color control overrides that default. Color MUST NOT be the only carrier of information. If provided, color flags MUST use `--color=always|never`; `--no-color` MAY be provided as `--color=never`.

- **H5: List-like commands with complete results SHOULD offer `--plain`.** A paginated command MAY offer it only for a page explicitly selected with `--limit` or `--cursor`. `--plain` MUST emit one item per LF-terminated line, with no heading or terminal decoration. The line format MUST be documented and stable; if items can contain LF, its escaping MUST be documented. If `--format` exists, `--plain` MUST equal `--format plain`.

  ```console
  $ mytool services list --plain
  api
  worker
  scheduler
  ```
