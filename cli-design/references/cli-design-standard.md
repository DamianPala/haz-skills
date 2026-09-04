# CLI Design Standard for Humans and Agents

> **Version:** 0.1.0-draft.3
>
> **Status:** Working draft. This document is not yet a conformance target.

## Scope

This document defines the contract for command-line tools, new or adapted, for reliable use by people and software agents. It includes human-facing behavior, machine-readable introspection, and the minimum safety contract for repeated and mutating operations.

The standard is independent of the operating system, shell, implementation language, framework, and backend. Arguments, standard streams, environment variables, exit codes, and TTY refer to the equivalent process interfaces on each platform. Command examples use POSIX-like notation for readability and are non-normative.

A brownfield path MAY preserve established behavior when changing it would break existing callers. A retained incompatible path MUST be documented and MUST NOT be presented as conforming. The tool MAY claim conformance only when it provides a documented conforming path for the same operation.

## Design principles

This section is non-normative. It records the decisions that shape the standard.

- **A process contract.** The standard binds arguments, the standard streams, environment variables, exit codes, and one introspection command. It requires no daemon, socket, or protocol library, so any tool that can be executed can conform.
- **A testable contract.** Each requirement has an observable pass or fail. A preference without a test belongs in guidance.
- **An introspection command, not `--help --json`.** D7 and D8 form a versioned contract (D9), fetched without credentials, configuration, or network (D6), and carry `effects`, `confirm`, and an output schema. Help output is a rendering for people and stays free to change.
- **Context from the stdin TTY and the selected stdout format.** Terms define the interactive context once. A caller forces the non-interactive context with `--json` or by withholding a TTY on stdin. A second, tool-defined signal for the same context would let the two disagree.
- **Conditional requirements and one extension, no profiles.** Applicability is stated per requirement: Stage R when a command mutates, Stage M when work outlives the command that started it, O6 when a collection has no documented finite maximum. `continuation` is the only extension because resumable pagination is a guarantee a tool cannot provide by accident.
- **`--json`, not `--output`.** `--json` is one flag a caller can pass without knowing the tool's format names. `--output` means a file path in some tools and a format in others, so a caller who sees it cannot tell which.
- **An open table of error kinds.** Names in the F3 error table keep their meanings everywhere; any other `kind` is tool-defined and unprefixed. A caller acts on the names it knows either way, and a prefix would only cost the tool.

## Terms

- **Greenfield, brownfield.** These words describe a command path, flag, environment variable, or F3 `kind`, not a tool. It is brownfield when it preserves a released contract and greenfield otherwise.
- **Interactive context, non-interactive context.** A call runs in an interactive context when stdin is a TTY and the selected stdout format is human-readable, and in a non-interactive context otherwise. These terms govern prompts and consent; I5 adds conditions for the prompt stream, interactive sessions, and pagers.
- **Machine-readable, human-readable.** `json` and `ndjson` are machine-readable formats, as is any other format the tool documents as machine-readable. Every other format, including `text`, `plain`, Markdown, and a native document format, is human-readable.
- **Introspection command.** The arguments, excluding the program name, that return the D7 index. It is `schema` unless D6 requires another form.
- **Core requirement.** A normative statement not labeled with an extension name, including an unlabeled clause within a requirement that also contains extension clauses.
- **Extension.** A named set of clauses labeled with that name. An extension is an optional guarantee that a tool enables by declaring it in D7.

## Conformance

A conforming tool MUST satisfy every applicable core requirement in this standard. A conditional requirement applies only when its stated condition is true.

A conformance claim is the D7 `conformance` field. It MUST identify this document's version and every extension the tool claims. This version defines one extension, `continuation`. A tool MAY claim it only if every clause under that name is satisfied by every command on every conforming path.

Tests and conformance tools can verify these requirements, but this document remains authoritative if they disagree.

## Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals. Synonymous BCP 14 terms are not used.

## Maintenance

The non-normative [maintenance guide](cli-design-standard-maintenance.md) defines the admission policy and verification workflow for changes to this standard. It is not part of conformance.

## Stage D: Discovery and introspection

A caller should be able to choose a command and construct a valid call without reading source code or probing commands that may change state.

- **D1: Published interfaces MUST match actual behavior.** Help, schema, documentation for the installed tool version, and shipped agent guidance MUST agree with the tool and with each other.

- **D2: Discovery has three layers.** `--help` MUST provide the quick start, and the introspection command MUST provide the exact command-line contract. `SKILL.md` or `AGENTS.md` MAY add domain or workflow context when the first two layers are not enough.

- **D3: Root `--help` MUST be a standalone cheat sheet.** It MUST state the tool's purpose, list its named commands or groups, if any, and state the literal invocation of the introspection command. When any command returns success data beyond its exit status, root help MUST also point to `--json` under O2. It SHOULD show non-obvious common workflows as literal invocations. Each command MUST provide `--help` that states its purpose and usage and describes its arguments, command-specific flags, and applicable defaults. When the command list grows, help MUST group commands rather than omit them.

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

- **D6: The introspection command MUST expose the command interface as JSON.**

  - Entry: the introspection command MUST be unambiguous from the arguments alone and MUST NOT dispatch to a retained domain operation. On greenfield paths, `schema` as the first argument MUST be reserved for introspection. When a retained contract already uses `schema` as its first argument, the tool MUST provide introspection in another form, such as a prefix (`tool contract schema`) or a flag (`tool --schema`).
  - Consistency: command paths, arguments, flags, and defaults exposed by schema MUST match the parser used at runtime. Shared definitions, generation, and conformance tests are all valid ways to enforce this.
  - Execution: the introspection command MUST write only JSON to stdout and require no application authentication, configuration, network access, or prompts.
  - Routing: the introspection command alone MUST return the D7 index, and followed by a command path it MUST return D8 detail. A command path's segments are the parts of D7 `commands[].name` split on U+0020; each segment MUST be passed as a separate argument in that order. A tool with exactly one command and no command path MUST list that command with `name` `""` and include its D8 detail as D7 `command`; any argument after the introspection command is then an unknown path.
  - Errors: an unknown path MUST be a usage error and name the nearest valid paths, if any.

- **D7: The schema index MUST let callers choose a command safely.** It MUST contain the following fields.

  | Field | Type | Contract |
  |---|---|---|
  | `schema_version` | string | Introspection format version. |
  | `tool_version` | string | Value reported by `--version`. |
  | `global_flags` | array | I1 flag descriptors accepted by every command. D8 `flags` MUST NOT repeat them. |
  | `format_defaults` | object | O2 default format for each output context. |
  | `exit_codes` | object | F1 tool-wide exit code meanings. |
  | `conformance` | object | Conformance claim. `standard` MUST equal this document's version. `extensions` MUST contain each claimed extension exactly once; a caller that does not recognize an extension name MUST NOT rely on that extension. |
  | `commands` | array | Flat routing list of every invocable command by full path, sorted by `name` in Unicode code point order; excludes the introspection command. |
  | `command` | object | Present exactly when the tool has one unnamed command: that command's D8 detail. |

  Each command entry MUST contain `name`, `description`, and `effects`, and MUST NOT contain invocation details. `name` MUST consist of non-empty segments separated by exactly one U+0020, or be `""` for the unnamed command, and MUST be unique within `commands`. `description` MUST distinguish neighboring commands, and `effects` MUST follow R1. Command detail, not a command entry, MUST contain enough information to construct a call.

- **D8: Command detail MUST expose the command contracts.**

  Fields marked `always` MUST be present. A conditional field MUST be present when its condition is true and MUST NOT be present otherwise.

  | Field | JSON type | Presence | Contract |
  |---|---|---|---|
  | `name` | string | always | Full command path, or `""` for a tool with one unnamed command. |
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
  "conformance": {"standard": "0.1.0-draft.3", "extensions": []},
  "commands": [
    {"name": "deploy", "description": "Deploy a service", "effects": "non_idempotent"},
    {"name": "services list", "description": "List deployed services", "effects": "read_only"}
  ]
}
```

`services list` is one entry with two segments, fetched as `mytool schema services list`.

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

A tool with one unnamed command has no command path, so its index carries the detail:

```console
$ hashfile schema
```

```json
{
  "schema_version": "1",
  "tool_version": "1.0.0",
  "global_flags": [
    {"name": "json", "description": "Emit JSON output", "type": "boolean", "required": false, "default": false}
  ],
  "format_defaults": {"tty": "text", "non_tty": "json"},
  "exit_codes": {"0": "success", "1": "failure", "2": "usage error"},
  "conformance": {"standard": "0.1.0-draft.3", "extensions": []},
  "commands": [{"name": "", "description": "Hash a file", "effects": "read_only"}],
  "command": {
    "name": "",
    "description": "Hash a file",
    "args": [{"name": "file", "description": "File to hash", "type": "string", "required": true}],
    "flags": [{"name": "algorithm", "description": "Digest algorithm", "type": "string", "required": false, "default": "sha256"}],
    "effects": "read_only",
    "confirm": false,
    "interactive": false,
    "output": {"type": "object", "required": ["digest"], "properties": {"digest": {"type": "string"}}}
  }
}
```

`hashfile README.md` runs the command. `hashfile schema README.md` is an unknown path under D6.

- **D9: The introspection contract MUST be stable and versioned.** `schema_version` MUST be a positive decimal integer encoded as a string. Callers should ignore unknown fields. Adding an optional introspection or output field MAY keep `schema_version`. Adding a required introspection field, removing an introspection field, or changing its type or meaning MUST increment it. Tool versions documented as compatible MUST preserve existing command paths, input meanings and defaults, exit code meanings, F3 `kind` meanings, and structured output fields. An incompatible change MUST document its replacement and migration; changing `schema_version` alone is insufficient.

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
  | `default` | scalar or array | MUST be present when the parser supplies an actual default. Scalar defaults MUST match `type`; variadic and repeatable defaults MUST be arrays whose items match `type`. Required inputs MUST NOT have a default. `default` is the built-in default. A value resolved at run time, from I2 sources or from the environment, such as the working directory or the newest available version, MUST be omitted and described in `description`. |
  | `enum` | array | MUST be present and list every choice when the parser declares a closed choice set. Every item MUST match `type`. |
  | `aliases` | array | MAY appear on flags and contain alternative names without leading hyphens. Alias rendering follows `name`. |
  | `variadic` | boolean | MAY be `true` only on the last argument. It consumes the remaining positional values as an ordered array; with `required: true`, it consumes at least one. |
  | `repeatable` | boolean | MAY be `true` only on flags. It allows repeated occurrences and resolves their values to an ordered array. |
  | `accepts_stdin` | boolean | MUST be `true` when `-` selects stdin instead of a file. |

  Arguments MUST appear in invocation order. A flag with `type: boolean` MUST set its value to `true` when given by its bare name and MUST NOT consume the following argument as its value; it MAY also accept both `--name=true` and `--name=false`. Omitted `variadic`, `repeatable`, and `accepts_stdin` mean `false`; omitted `aliases` means no aliases. A parser sentinel meaning "not provided", including `null`, is not a default and MUST be omitted.

  Any accepted value syntax, bound, path-resolution rule, dependency, conflict, or dynamic value-discovery path not expressed by another descriptor field MUST be stated in `description`.

  Example descriptors:

  - Argument: `{"name": "file", "description": "Files to upload", "type": "string", "required": true, "variadic": true}`
  - Flag: `{"name": "tag", "description": "Tag to attach", "type": "string", "required": false, "aliases": ["t"], "repeatable": true}`

  Together they accept `mytool upload --tag docs -t archive a.txt b.txt` and resolve both `file` and `tag` to ordered arrays.

- **I2: Configuration MUST be declared, deterministic, and inspectable.**

  - Sources: accepted configuration files and tool-specific environment variables MUST be documented, and an undeclared tool-specific variable MUST NOT change behavior. Greenfield variables SHOULD use a consistent `<TOOL>_<OPTION>` prefix, such as `MYTOOL_LOG_LEVEL`. If a flag selects a configuration file, the tool MUST document whether that file replaces or augments project and user configuration and where it sits in the precedence.
  - Precedence: when more than one source provides a value, resolution MUST be deterministic and documented. Greenfield paths SHOULD resolve in this order:

    `flags > environment > project configuration > user configuration > built-in defaults`

  - Inspection: layered configuration SHOULD expose each resolved value and its source while masking secrets.

  Example: `--log-level debug` overrides `MYTOOL_LOG_LEVEL=info`, which overrides `log_level = "warning"` in project configuration and `log_level = "error"` in user configuration.

- **I3: Long or generated input MUST use files or stdin, never argv.** A command that accepts a document, script, request body, template, or other unbounded text MUST accept a file path and `-` for stdin. An input that accepts `-` MUST contain `accepts_stdin: true` in its I1 descriptor. The tool MUST reject a call that selects stdin for more than one input.

  The same manifest can come from a file or stdin. Its quotes, newlines, and flag-like text remain data rather than argv:

  ```console
  $ mytool deploy service-a --manifest manifest.json
  $ mytool deploy service-a --manifest - < manifest.json
  ```

- **I4: Secrets MUST NOT be passed as argument or flag values.** A command that needs a secret MUST provide a source usable in a non-interactive context, such as a credential store, file, stdin, or environment variable. Greenfield commands SHOULD use `--token-file PATH` for one secret and `--credentials-file PATH` for structured credentials; either flag SHOULD accept `-` for stdin. Secret sources and their precedence MUST be documented. A secret MUST NOT appear in help, schema, logs, errors, or normal output unless retrieval is the command's documented purpose.

  With `--token-file token.txt` under `--verbose`, a diagnostic may name the source, such as `Using token from token.txt`, but not the token.

- **I5: Behavior in a non-interactive context MUST be explicit and fail safely.**

  - Prompts: a command MAY prompt only in an interactive context and only by writing the prompt to a stream that is a TTY. Otherwise, it MUST NOT prompt. If required input or confirmation remains unresolved, it MUST fail with an error that names a flag, file, stdin form, or environment variable that can supply it. The absence of a permitted prompt MUST NOT be treated as consent. A command MUST NOT prompt while stdin supplies an input, and an unanswered prompt, including end of input, MUST NOT be treated as consent.
  - Interactive sessions: a command MAY start an interactive session only when stdin and stdout are TTYs and the selected stdout format is human-readable. It MUST fail before side effects otherwise. A command that offers such a session MUST declare `interactive: true` in D8. Starting an external editor is an interactive session.
  - Human action: a workflow MAY require an out-of-band human action. Its entry point MUST work in a non-interactive context and be discoverable through D7 and D8. Work that continues after that command exits follows Stage M. In a non-interactive context, a command MUST NOT wait for a human action outside the call, such as a browser or device approval, unless that wait is the command's documented purpose. It MUST fail before side effects instead and name the entry point or I4 source that resolves it.
  - Paging: a pager MAY start only when stdout is a TTY and the selected format is human-readable; see H3.

  While stdin supplies the manifest, the command cannot prompt for confirmation, so it fails and names `--yes`:

  ```console
  $ mytool deploy api --env prod --manifest - < manifest.json
  Error: Deploying 'api' to prod requires confirmation
  Run: mytool deploy api --env prod --manifest - --yes
  ```

- **I6: Invalid input MUST fail before side effects.** The tool MUST reject unknown flags, unsupported arguments, invalid values, and conflicting inputs as usage errors. A usage error MUST use F3 `kind` `invalid_input`. `--` MUST end option parsing; later tokens MUST NOT be interpreted as flags. A greenfield command SHOULD accept flags before, between, and after positional arguments up to `--`. The tool MUST validate every locally checkable input before changing state. The error SHOULD identify the invalid input and show the accepted form or nearest valid name.

- **I7: Input MUST stay within its declared bounds.**

  - Buffered data: a command that buffers caller-controlled input MUST document and enforce a maximum size before side effects.
  - Restricted paths: a command limited to declared roots MUST resolve each supplied path and reject it when it escapes those roots, including through `..` or a symbolic link.

  For example, assume `mytool upload` accepts at most 10 MiB and may read files only from `./dist`:

  ```console
  $ mytool upload ../secrets.txt --json
  {"error":{"kind":"invalid_input","message":"Path must resolve inside ./dist"}}

  $ cat 20-mib.bin | mytool upload - --json
  {"error":{"kind":"invalid_input","message":"Input exceeds the 10 MiB limit"}}
  ```

- **I8: External work MUST be bounded or explicitly unbounded.** Connection establishment and non-streaming network operations MUST use finite default timeouts. A command that waits for external state without waiting being its documented purpose MUST use a finite default deadline. A wait for a human action follows I5. A command whose documented purpose is to wait, watch, follow, or run external work to completion MAY be unbounded by default, but MUST accept `--timeout` and declare that default. `--timeout` MUST accept an integer immediately followed by `s`, `m`, or `h` and MAY accept other forms, such as a bare integer with a documented unit. Any other unbounded mode MUST require explicit selection.

  A bounded and an unbounded call:

  ```console
  $ mytool jobs wait job_123 --timeout 5m
  $ mytool logs job_123 --follow
  ```

  The first call sets a deadline. The second explicitly selects an unbounded mode.

## Stage R: Repeatability and mutation safety

This stage covers calls that mutate state or may be repeated. Safeguards follow the possible damage, not merely whether a command changes state. A tool whose every command declares `effects: read_only` has no mutation requirements under R2-R5. R6 applies when the tool retries requests internally.

- **R1: Effect metadata MUST be conservative.** Every D7 command entry and D8 command detail MUST declare one value:

  | `effects` | Contract |
  |---|---|
  | `read_only` | The command does not change intended state managed or targeted by the tool. |
  | `idempotent` | The command may change intended state, but repeating a successful call with the same inputs MUST succeed without another intended state transition. |
  | `non_idempotent` | The command meets neither preceding guarantee; a repeat may cause another intended effect or return a stable conflict. |

  The declaration MUST cover every valid invocation. Use `non_idempotent` if any invocation lacks the repeat guarantee; otherwise use `idempotent` if any invocation can change intended state, and `read_only` otherwise. A changing response, incidental telemetry, logs, caches, metering, or rate limiting do not alone change the classification. For example, a delete by stable identifier whose repeat succeeds with `changed: false` is `idempotent`; a delete whose repeat fails with `not_found`, or whose targets are resolved at run time and may differ on a later repeat, such as the newest item or every stale item, is `non_idempotent`.

- **R2: Mutation safeguards MUST match the blast radius.** A mutation is wide when it can affect targets the caller did not name individually. It is irreversible when the tool provides no documented operation that restores the prior state. Idempotence does not reduce these safeguards:

  | Operation | Minimum safeguard |
  |---|---|
  | `effects: "read_only"` | None |
  | Narrow, reversible mutation | None |
  | Narrow, irreversible mutation | R3 confirmation: `--yes` in a non-interactive context |
  | Wide mutation | R3 confirmation, and the command provides `--dry-run` under R4 |

  An M3 cancellation of exactly one managed operation by its M1 identifier does not require an additional confirmation. Any wider cancellation follows the table.

- **R3: Safety gates MUST fail closed and be discoverable.** Every command that can require `--yes`, including those required by R2, MUST declare `confirm: true` in D8, and a command that declares `confirm: true` MUST accept `--yes`. Without `--yes`, a call in a non-interactive context that would perform the gated effect MUST stop before side effects and fail with F3 `kind` `confirmation_required`, naming `--yes`. A `--dry-run` call MUST NOT require `--yes`; a command that accepts `--yes` MUST accept it with `--dry-run` and ignore it. `--yes` confirms a prompt; `--force` overrides a documented precondition. Accepting one MUST NOT enable the other.

  A gated call in a non-interactive context, here with `--json` and no TTY on stdin, stops before side effects; under R4, the same command previews without `--yes`:

  ```console
  $ mytool services prune --env staging --json < /dev/null
  {"error":{"kind":"confirmation_required","message":"Pruning staging services requires confirmation","hint":"Repeat with --yes"}}
  ```

- **R4: Wide mutations MUST be previewable.** The command MUST provide `--dry-run`. Any command that accepts it MUST then leave intended state unchanged, apply the same permission checks as the mutating call, and fail with the `kind` that call would fail with before side effects, except `confirmation_required`. Its structured success MUST conform to the same D8 `output`, list each target the mutating call would affect as observed during that call, and return `changed: false`; a value produced only by performing the mutation MUST be omitted or `null`.

  Preview and mutation share one output schema:

  ```console
  $ mytool services prune --env staging --dry-run --json
  {"targets":["api","worker"],"changed":false}

  $ mytool services prune --env staging --yes --json
  {"targets":["api","worker"],"changed":true}
  ```

- **R5: Mutating commands MUST report what happened.**

  - Every command whose `effects` is not `read_only` MUST declare a boolean `changed` in its D8 output and return it in every structured success response. `changed` reports whether this invocation caused a new intended state transition, not whether background work completed.
  - When authoritative state reports a concurrent conflict, the CLI MUST fail with F3 `kind` `conflict` and MUST NOT silently overwrite it.
  - A `non_idempotent` command whose repetition could duplicate an effect SHOULD accept `--idempotency-key` when the backing service supports idempotency keys.

  For example, an idempotent create-or-get may return `changed: true` and then `changed: false`. A strict create may return `changed: true` and then fail with `kind` `conflict`. Under O3 Consistency, human-readable output of a repeated idempotent delete reports absence rather than deletion, for example `Already absent: api`.

- **R6: Built-in retries MUST be safe and bounded.** A CLI that retries requests internally:

  - MUST retry only failures that would be reported with `retryable: true` under F3, and only for `read_only` or `idempotent` commands, or requests protected by an idempotency key;
  - MUST preserve the original inputs, limit the number of attempts, and remain within the I8 timeout;
  - SHOULD honor `Retry-After` when the timeout allows.

## Stage O: Output

A caller should be able to select a representation before execution, parse stdout without filtering diagnostics, and consume large results without mistaking one page for the whole result.

- **O1: The standard streams MUST be classified independently.** The TTY state of stdin is one input to the I5 prompt policy, stdout controls the default format under O2, and stderr controls diagnostic decoration under O3 and whether F2 requires the structured error object. Redirecting one stream MUST NOT change how another is classified.

- **O2: Output format selection MUST be explicit and predictable.**

  - Declaration: D7 `format_defaults` MUST declare `tty` and `non_tty` format names. D8 `format_defaults` MUST appear only when a command differs from those tool-wide defaults.
  - Machine access: every command with D8 `output` MUST accept `--json`, and every other command SHOULD. On a command without `output`, `--json` selects the `json` format, and a success MUST write no bytes to stdout. If a command also accepts `--format`, `--json` MUST produce the same output as `--format json`, or as `--format ndjson` for a stream.
  - Defaults: a greenfield command with D8 `output` SHOULD default to human-readable output on a TTY. On non-TTY stdout, structured data MUST default to JSON or NDJSON. A command whose primary result is a textual document rather than a set of fields or records MAY default to a declared native format such as text or Markdown. A brownfield command MAY retain an established non-TTY default when it is stable, parseable, and declared.
  - Precedence: an explicit format flag MUST override the detected default. Conflicting explicit format flags MUST be usage errors.
  - Names: a greenfield command MUST NOT accept `--output`. If it accepts a destination path, the flag MUST be named `--output-file`. Under `--output-file`, the result goes to that file and a success writes no bytes to stdout. Formats use `--json` or `--format`.

  A command without `output` under `--json`, and a command with `output` under `--output-file`:

  ```console
  $ mytool config validate --json
  $ mytool services list --json --output-file services.json
  ```

  Both exit `0` and write no bytes to stdout; the second leaves the result in `services.json`.

- **O3: The output streams MUST have separate roles.**

  - Channels:
    - stdout MUST contain only the result.
    - stderr MUST carry logs, warnings, progress, and errors.
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

  - Document: unless D8 declares `stream: true`, a `--json` success of a command with `output` MUST contain exactly one JSON value conforming to that schema, encoded as UTF-8 and followed by LF. A failed document call MUST NOT leave an incomplete or invalid JSON value on stdout.
  - Values: values MUST keep their declared JSON types. Machine output MUST NOT silently truncate a value.
  - Bounded values: a command that may cap a single inline value MUST declare a required boolean `truncated` and an optional string `output_file` in its D8 output schema. Every result MUST return `truncated`. When it is `true`, `output_file` MUST identify a file that holds the complete value; unless the caller selected that path, the file SHOULD NOT be accessible to other users. The inline value is a preview, and the file's retention MUST be documented. Collections and record streams MUST use O6 and O7 instead.
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
    "output_file": "/home/user/.cache/mytool/results/job_123.md"
  }
  ```

- **O6: Potentially unbounded document collections MUST be bounded.** An R4 target list, in a preview or in the mutation's own result, is not a collection under this requirement; a command that caps it follows O5 Bounded values.

  - Window: a collection without a documented finite maximum MUST use a finite default limit and accept `--limit`. The tool MUST bound the number of items, not silently omit fields from individual items.
  - Shape: a bounded collection MUST be an object with an `items` array and a boolean `has_more` that is `true` exactly when matching items exist beyond those returned. A collection with a documented finite maximum MAY use a bare array. An empty collection MUST use the same shape with an empty array, not `null` or absent output.

  Under the `continuation` extension:

  - Cursor: the command MUST accept `--cursor`, and each JSON page MUST contain `next_cursor`, an opaque string that the caller passes unchanged to `--cursor`, or `null` on the final page. `has_more` MUST be `true` if and only if `next_cursor` is not `null`.
  - Resume: source, filters, and order MUST remain unchanged when using `--cursor`; the limit and output format MAY change. If the cursor is invalid, expired, incompatible, or cannot continue the same result set, the command MUST fail with non-zero exit and F3 `kind` `cursor_unavailable`. It MUST NOT silently restart from another position.
  - Stability: pagination MUST use a stable, documented order and document whether pages read live state or one fixed snapshot.

  A page from a tool that declares `continuation`:

  ```console
  $ mytool jobs list --limit 2 --json
  ```

  ```json
  {
    "items": [
      {"id": "job_123", "status": "running"},
      {"id": "job_456", "status": "queued"}
    ],
    "has_more": true,
    "next_cursor": "cur_abc123"
  }
  ```

- **O7: Record streams MUST be bounded and framed.** This requirement applies to a command with D8 `stream: true`.

  - Framing: `--json` MUST emit UTF-8 NDJSON with one complete JSON object per LF-terminated line and no blank lines. Each record MUST conform to D8 `output` and become readable before the command waits for another record or exits. O5 value and time rules and D9 compatibility rules apply to each record.
  - Window: without `--follow`, the command MUST terminate. A stream without a documented finite maximum MUST use a finite default limit and accept `--limit`. `--follow` removes that default limit. An explicit `--limit` remains effective with or without `--follow` and ends the read after that many records. Reaching a limit ends that read, not the record source.
  - Ordering: the stream MUST use a stable, documented order and MUST NOT stop before the effective limit while matching records are available.
  - Following: a follow mode MAY exist, SHOULD be named `--follow`, and MUST require explicit selection under I8. Without an explicit `--limit`, it is unbounded.
  - Completion: exit `0` means the requested read ended successfully, not that the record source is exhausted; empty stdout is valid. After a non-zero exit, prior LF-terminated records remain valid and an unterminated final fragment is not a record. This standard defines no end record; EOF and the exit status are authoritative.

  Under the `continuation` extension:

  - Cursor: `output` MUST be an object schema with `cursor` as a required string property, and each `cursor` MUST be a non-empty opaque string. The command MUST accept `--after-cursor` and resume strictly after that record without skipping any matching record in the same logical stream. Inputs selecting the source, filters, or order MUST remain the same; limits, following, timeouts, and output format MAY change. If this continuation cannot be guaranteed because the cursor or required history is invalid, expired, or incompatible, the command MUST fail with non-zero exit and F3 `kind` `cursor_unavailable`; it MUST NOT silently resume elsewhere.

  Example command schema excerpt for a tool that declares `continuation`:

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

- **F2: Structured errors MUST have one location.** When the tool exits with an error, stderr MUST contain the F3 `message` and, when the error has one, its `hint`, as human-readable diagnostics or inside the F3 JSON object. When the selected stdout format is machine-readable or stderr is not a TTY, the last non-empty stderr line MUST be that object, including under `--quiet`; otherwise the object MAY be omitted. Whenever the object is emitted, it MUST be the last non-empty stderr line, and a requirement that names an F3 `kind` applies to it.

  The same failure with `--json` and at a terminal:

  ```console
  $ mytool deploy api --json
  {"error":{"kind":"image_not_found","message":"Cannot deploy 'api': image 'web:v2.1.0' was not found","hint":"Run mytool images list web"}}

  $ mytool deploy api
  Error: Cannot deploy 'api': image 'web:v2.1.0' was not found
  Run: mytool images list web
  ```

- **F3: Structured errors MUST have a stable envelope.** The document MUST contain exactly one top-level field, `error`, whose value is an object. Its `kind` is the only stable match target; message text is not a stable interface.

  | Field | Presence | Contract |
  |---|---|---|
  | `kind` | MUST | String with stable machine meaning; the values in the table below have shared meanings. |
  | `message` | MUST | String identifying the failed operation and cause. |
  | `retryable` | MAY | Boolean. `true` only when the same invocation may resolve the failure without duplicating an intended effect. When omitted, the caller has no assurance that a retry is safe. |
  | `action` | MAY | `agent` when the caller can recover autonomously, `user` when human action is required, or `none` when no recovery action exists. |
  | `hint` | SHOULD if one concrete recovery step is known | String recovery step; omit rather than guess. |
  | `context` | MAY | Object containing machine-readable values needed for recovery. |

  A tool MUST NOT use a `kind` listed below with another meaning and SHOULD use it when its definition applies; a requirement that names a `kind` keeps its own keyword. Any other `kind` is tool-defined. A released `kind` whose meaning conflicts with the table is brownfield: the tool MAY retain it and MUST document it as not conforming.

  | `kind` | Meaning | Named by |
  |---|---|---|
  | `invalid_input` | The call is a usage error or exceeds an I7 bound. | I6 |
  | `not_found` | A target identified by an argument or flag value does not exist in the state the tool manages or targets. | M2 |
  | `conflict` | Authoritative state conflicts with the requested change, such as a concurrent modification or a strict create whose target exists. | R5 |
  | `permission_denied` | The caller is identified and the action is forbidden. | |
  | `unauthenticated` | The caller could not be identified: credentials are missing, invalid, or expired. | |
  | `timeout` | The command's own I8 deadline passed, and any intended effect is known not to have happened. | |
  | `unavailable` | A dependency rejected or failed the request transiently, including rate limiting. | |
  | `outcome_unknown` | The intended effect may have happened and was not observed. | F4 |
  | `interrupted` | The user interrupted the command and F4 does not apply. | F5 |
  | `cursor_unavailable` | The cursor is invalid, expired, or incompatible, or required history is missing. | O6, O7 |
  | `confirmation_required` | R3 stopped the call before its gated effect. | R3 |
  | `precondition_failed` | A documented precondition that `--force` overrides is not met. | |

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
  {"error":{"kind":"outcome_unknown","message":"The deployment request timed out and its outcome could not be determined","retryable":false,"context":{"deployment_id":"dep_123"}}}
  ```

- **F5: User interruption MUST fail honestly.** A command that receives the platform's normal user-interrupt request MUST exit without a stack trace and fail through F2-F3 with `kind` `interrupted`, unless F4 requires `outcome_unknown`. Interrupting observation of managed work MUST NOT cancel or otherwise change that work.

## Stage M: Managed operations

A managed operation is work that continues after the command that started it exits. A tool without such work has no Stage M requirements.

- **M1: Accepted work MUST remain identifiable.** A command that exits before requested work finishes MUST return a non-empty canonical identifier in structured success output. Its field name is tool-defined but MUST remain consistent across the command that starts the work and every command that addresses it. If the command that starts the work fails after obtaining the identifier, any F3 object it emits MUST carry the identifier in `context` under the same field name. Exit `0` means the work was accepted, not completed. The identifier MUST remain usable after the initiating process exits and MUST NOT later resolve to a different entity. Its D5 breadcrumb SHOULD name the wait command.

  When a command offers both waiting for completion and returning after acceptance, selecting the latter MUST change only how long the command waits, not the work it starts. Its flag SHOULD follow H1. A command that waits for the work it started MUST fail through F2-F3 when that work does not succeed.

  A `deploy` that waits for its deployment fails when the deployment fails and carries the identifier; the wait command observing the same terminal state exits `0` under M2:

  ```console
  $ mytool deploy api --env prod --yes --json
  {"error":{"kind":"deployment_failed","message":"Deployment dep_123 failed: image pull error","context":{"deployment_id":"dep_123"}}}

  $ mytool deployments wait dep_123 --json
  {"deployment_id":"dep_123","status":"failed"}
  ```

- **M2: Managed work MUST expose status and wait.** The tool MUST provide commands, usable in a non-interactive context, for inspecting current status and waiting for a terminal state. Both MUST accept the identifier returned under M1; D4 covers their names.

  - Both commands MUST declare `effects: read_only`.
  - The status command MUST report the current state without waiting for a terminal state.
  - Structured results from both commands MUST contain `status` and the identifier under the same field name. The D8 output schema MUST declare `status` as a finite enum containing terminal values `succeeded` and `failed`, plus `canceled` when cancellation exists. It MAY add values for unfinished states and MUST add `unknown` when an existing operation's current state can be indeterminate. `unknown` MAY be returned only when the tool successfully observes an underlying state that explicitly represents indeterminacy. A timeout, transport error, or other failure to read state MUST fail through F2-F3 and MUST NOT return `unknown`.
  - Any retention or expiry policy for managed operations MUST be documented. An unrecognized or expired identifier MUST fail through F2-F3 with `kind` `not_found` and MUST NOT be reported as an operation state.
  - The wait command MUST exit `0` when it successfully observes any terminal state. The operation outcome MUST be reported by `status` and MUST NOT change that exit code. Failure to observe the operation MUST fail through F2-F3.
  - The wait command MUST follow I8 and return immediately when the operation is already terminal. Timing out or terminating it MUST NOT cancel or otherwise change the operation, and MUST NOT be reported as a terminal operation outcome.

  Operation logs and events MAY supplement status and wait, but MUST NOT replace them.

- **M3: Cancellation MUST be honest.** If a managed operation can be canceled, the tool MUST provide a cancellation command, usable in a non-interactive context, whose name follows D4. It MUST accept the identifier returned under M1, declare `effects: idempotent`, and follow Stage R. Structured success MUST contain `status` and the identifier under the same field name; R5 supplies `changed`. Exit `0` means cancellation was accepted or a terminal state was observed, not necessarily that the operation was canceled. The command MUST NOT report `canceled` until it observes that state; if the operation wins the race, it MUST report the actual terminal state.

  ```console
  $ mytool jobs status job_123 --json
  {"job_id":"job_123","status":"running"}

  $ mytool jobs cancel job_123 --json
  {"job_id":"job_123","status":"canceling","changed":true}

  $ mytool jobs wait job_123 --timeout 5m --json
  {"job_id":"job_123","status":"canceled"}
  ```

- **M4: Resumable suspension MUST remain distinct from cancellation.** If managed work can be suspended and later resumed from the same point, the tool MUST expose suspension and resumption commands, usable in a non-interactive context, whose names follow D4. Both MUST accept the identifier returned under M1, declare `effects: idempotent`, and return the identifier, `status`, and `changed` in structured success. They MUST report only a status they observed. While suspended, `status` MUST be `paused` and non-terminal. Cancellation under M3 remains terminal and MUST NOT mean suspension.

## Stage H: Human interface

A person at the terminal should find familiar flag names, standard environment behavior, and output that remains readable without color.

- **H1: Greenfield flags MUST have canonical long names.** A greenfield flag MUST use kebab-case, and each concept MUST have one canonical long name. When the tool supports a concept below, it SHOULD use the listed long name; a requirement that names a flag keeps its own keyword. A listed alias MAY be added when it has no conflicting local meaning. Every accepted alias MUST behave exactly like its canonical flag and appear in the I1 descriptor.

  | Concept | Long name | Common alias | Related rule |
  |---|---|---|---|
  | Help | `--help` | `-h` | D3 |
  | Version | `--version` | `-V` | D4 |
  | Select a configuration file | `--config PATH` | `-c PATH` | I2 |
  | Supply one secret | `--token-file PATH` | No recommendation | I4 |
  | Supply structured credentials | `--credentials-file PATH` | No recommendation | I4 |
  | Bound a wait | `--timeout DURATION` | No recommendation | I8, M2 |
  | Override a documented precondition | `--force` | `-f` | R3 |
  | Confirm a prompt | `--yes` | `-y` | R3 |
  | Preview a mutation | `--dry-run` | `-n` | R4 |
  | Keep a repeat from duplicating its effect | `--idempotency-key KEY` | No recommendation | R5 |
  | Select JSON or NDJSON output | `--json` | No recommendation | O2 |
  | Select a named format | `--format NAME` | No recommendation | O2 |
  | Write the result to a path | `--output-file PATH` | `-o PATH` | O2 |
  | More diagnostics | `--verbose` | `-v` | O3 |
  | Less diagnostics | `--quiet` | `-q` | O3, F2 |
  | Bound returned items or records | `--limit N` | No recommendation | O6, O7 |
  | Resume a collection | `--cursor CURSOR` | No recommendation | O6 (`continuation`) |
  | Resume a stream after a record | `--after-cursor CURSOR` | No recommendation | O7 (`continuation`) |
  | Keep reading new records | `--follow` | No recommendation | O7 |
  | Return after accepting managed work | `--background` | `--bg` | M1 |
  | Control color | `--color WHEN` | No recommendation | H4 |
  | One item per line | `--plain` | No recommendation | H5 |

  `-n` follows the established no-op and dry-run convention. `-d` and `-l` are too overloaded to recommend for dry-run or limit.

- **H2: Tools with nested commands SHOULD provide shell completions.** When provided, static command, flag, and alias candidates MUST match the installed interface.

- **H3: External editors and pagers MUST respect user selection.** A tool that starts an editor MUST prefer `VISUAL` to `EDITOR` unless a documented setting overrides them. A tool that starts a pager MUST honor `PAGER` unless a documented setting overrides it. I5 defines when an editor or pager may start.

- **H4: Color MUST remain optional.** A tool that emits color MUST disable it when `NO_COLOR` is non-empty, `TERM` is `dumb`, or the output stream is not a TTY, unless a flag or a documented setting overrides that default on human-readable output. Color MUST NOT be the only carrier of information. If provided, the color flag MUST be `--color` with the values `auto`, `always`, and `never`: `auto` applies that default, and the other two override it. `--no-color` MAY be provided as `--color=never`.

  At a terminal, `NO_COLOR=1 mytool services list` and `TERM=dumb mytool services list` print no color. In a pipe, `mytool services list --format text --color always | less -R` keeps color because the output is human-readable, while `mytool services list --color always | jq .` emits none because stdout is then machine-readable under O2 and O3.

- **H5: List-like commands with complete results SHOULD offer `--plain`.** A paginated command MAY offer it only for a page explicitly selected with `--limit` or, when the tool declares `continuation`, `--cursor`. `--plain` MUST emit one item per LF-terminated line, with no heading or terminal decoration. The line format MUST be documented and stable; if items can contain LF, its escaping MUST be documented. If `--format` exists, `--plain` MUST equal `--format plain`.

  ```console
  $ mytool services list --plain
  api
  worker
  scheduler
  ```
