# CLI Design Standard for Humans and Agents

**Version:** 0.1.0-draft.4

**Status:** Working draft. This document is not yet a conformance target.

## Scope

This document defines the contract for command-line tools, new or adapted, for reliable use by people and software agents. It includes human-facing behavior, machine-readable introspection, and the minimum safety contract for repeated and mutating operations.

The standard is independent of the operating system, shell, implementation language, framework, and backend. Arguments, standard streams, environment variables, exit codes, and TTY refer to the equivalent process interfaces on each platform. Command examples use POSIX-like notation for readability and are non-normative.

## Design principles

This section is non-normative. It records the decisions that shape the standard.

- **A process contract.** The standard binds arguments, the standard streams, environment variables, exit codes, and one introspection command. It requires no daemon, socket, or protocol library, so any tool that can be executed can conform.
- **A testable contract.** Each requirement has an observable pass or fail. A preference without a test belongs in guidance.
- **An introspection command, not `--help --json`.** D7 and D8 form a versioned contract (D9), fetched without credentials, configuration, or network (D6), and carry `effects`, `confirm`, and an output schema. Help output is a rendering for people and stays free to change.
- **Context from the stdin TTY, the selected stdout format, and `NO_INPUT`.** Terms define the interactive context once. A caller forces the non-interactive context with `--json`, by withholding a TTY on stdin, or with `NO_INPUT` when it cannot change either. Each signal can only force the non-interactive context, so none can contradict a TTY; a tool-defined signal for the same context would let two signals disagree.
- **Conditional requirements and one extension, no profiles.** Applicability is stated per requirement: Stage R when a command mutates, Stage M when work outlives the command that started it, O6 when a collection has no documented finite maximum. `continuation` is the only extension because resumable pagination is a guarantee a tool cannot provide by accident.
- **`--json`, not `--output`.** `--json` is one flag a caller can pass without knowing the tool's format names. `--output` means a file path in some tools and a format in others, so a caller who sees it cannot tell which.
- **An open table of error kinds.** Names in the F3 error table keep their meanings everywhere; any other `kind` is tool-defined and unprefixed. A caller acts on the names it knows either way, and a prefix would only cost the tool.

## Terms

- **Greenfield, brownfield.** These words describe a command path, flag, environment variable, or F3 `kind`, not a tool. It is brownfield when it preserves a released contract and greenfield otherwise.
- **Interactive context, non-interactive context.** A call runs in an interactive context when stdin is a TTY and the selected stdout format is human-readable, and in a non-interactive context otherwise; a non-empty `NO_INPUT` environment variable forces the non-interactive context under I5a. These terms govern prompts and consent; the stream a prompt is written to, interactive sessions, and pagers carry further conditions under I5a, I5b, and I5d.
- **Machine-readable, human-readable.** `json` and `ndjson` are machine-readable formats, as is any other format the tool documents as machine-readable. Every other format, including `text`, `plain`, Markdown, and a native document format, is human-readable.
- **Introspection command.** The arguments, excluding the program name, that return the D7 index. It is `schema` unless another form is required under D6a.
- **Caller.** The person or program that runs the tool and consumes its output.
- **Managed operation.** Work that continues after the command that started it exits.
- **Core requirement.** A normative statement not labeled with an extension name, including an unlabeled clause within a requirement that also contains extension clauses.
- **Extension.** A named set of clauses labeled with that name. An extension is an optional guarantee that a tool enables by declaring it in D7.

## Conformance

A conforming tool MUST satisfy every applicable core requirement in this standard. A conditional requirement applies only when its stated condition is true.

A conformance claim is the D7 `conformance` field. It MUST identify this document's version and every extension the tool claims. This version defines one extension, `continuation`. A tool MAY claim it only if every applicable clause under that name is satisfied on every conforming path.

A brownfield path MAY preserve established behavior when changing it would break existing callers. A retained incompatible command MUST carry `conforming: false` in its D7 entry, and its retained behavior MUST be documented. The claim covers every command not so marked. A tool that retains such a command SHOULD also provide a documented conforming path for the same operation.

Tests and conformance tools can verify these requirements, but this document remains authoritative if they disagree.

## Normative language

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals. Synonymous BCP 14 terms are not used.

## Maintenance

The non-normative [maintenance guide](cli-design-standard-maintenance.md) defines the admission policy and verification workflow for changes to this standard. It is not part of conformance.

## Stage D: Discovery and introspection

A caller should be able to choose a command and construct a valid call without reading source code or probing commands that may change state.

### D1: Published interfaces MUST match actual behavior.

Help, introspection output, documentation for the installed tool version, and shipped agent guidance MUST agree with the tool and with each other.

### D2: Discovery MUST be layered.

Discovery is layered: `--help` under D3, the introspection command under D6, and optional shipped guidance under D10.

### D3: `--help` MUST be a standalone cheat sheet at every level.

**D3a** Root `--help` MUST state the tool's purpose, list its named commands or groups, if any, and state the literal invocation of the introspection command. When any command returns success data beyond its exit status, root help MUST also point to `--json` under O2b.

**D3b** Each command MUST provide `--help` that states its purpose and usage and describes its arguments, command-specific flags, and applicable defaults. When the command list grows, help MUST group commands rather than omit them.

### D4: Command and flag names MUST be predictable.

**D4a** Related commands MUST follow a predictable structure (`tool <noun> <verb>` or `tool <verb>`).

**D4b** For equivalent operations, greenfield commands SHOULD prefer `get`, `list`, `create`, and `delete` to `info`, `ls`, and `add`. Managed-operation commands SHOULD use `status`, `wait`, and `cancel`, plus `pause` and `resume` for resumable suspension.

**D4c** A canonical flag name MUST keep the same meaning wherever it appears; aliases MAY remain for compatibility.

**D4d** Root `--version` MUST exist.

### D5: A workflow with one unambiguous next step SHOULD expose it as a breadcrumb.

**D5a** In structured output, `next` MUST be a non-empty array of strings forming a complete argv vector that can be executed without a shell. `next[0]` is the tool's canonical executable name; a caller that invoked the tool by path substitutes it. A command that may emit `next` MUST declare it as an optional field in its D8 output schema.

**D5b** Human-readable output SHOULD render the same invocation as `Next: ...` and safely quote caller-controlled values.

**D5c** Output MUST omit `next` when there is no natural continuation.

A queued deployment renders the breadcrumb at a terminal:

```console
$ mytool deploy service-a --env prod --yes
Deployment queued: dep_123
Next: mytool deployments wait dep_123
```

The same call under `--json` carries it as `next`:

```json
{
  "deployment_id": "dep_123",
  "status": "queued",
  "changed": true,
  "next": ["mytool", "deployments", "wait", "dep_123"]
}
```

### D6: The introspection command MUST expose the command interface as JSON.

**D6a** Entry: the introspection command MUST be unambiguous from the arguments alone and MUST NOT dispatch to a retained domain operation. On greenfield paths, `schema` as the first argument MUST be reserved for introspection. When a retained contract already uses `schema` as its first argument, the tool MUST provide introspection in another form, such as a prefix (`tool contract schema`) or a flag (`tool --schema`).

**D6b** Consistency: command paths, arguments, flags, and defaults exposed by the introspection output MUST match the parser used at runtime. Shared definitions, generation, and conformance tests are all valid ways to enforce this.

**D6c** Execution: the introspection command MUST write only JSON to stdout and require no application authentication, configuration, network access, or prompts.

**D6d** Routing: the introspection command alone MUST return the D7 index, and followed by a command path it MUST return D8 detail. A command path's segments are the parts of D7 `commands[].name` split on U+0020; each segment MUST be passed as a separate argument in that order. A tool with exactly one command and no command path MUST list that command with `name` `""` and include its D8 detail as D7 `command`. In that case, any argument after the introspection command is an unknown path.

**D6e** Errors: an unknown path MUST be a usage error and name the nearest valid paths, if any.

### D7: The introspection index MUST let callers choose a command safely.

**D7a** The index MUST contain the fields in the table below.

| Field | Type | Contract |
|---|---|---|
| `schema_version` | string | Introspection format version. |
| `tool_version` | string | The version string, which `--version` MUST print. |
| `global_flags` | array | I1 flag descriptors accepted by every command. D8 `flags` MUST NOT repeat them. |
| `format_defaults` | object | O2 default format for each output context. |
| `exit_codes` | object | F1 tool-wide exit code meanings. |
| `conformance` | object | Conformance claim; see D7c. |
| `commands` | array | Flat routing list of every command the tool itself dispatches, by full path, sorted by `name` in Unicode code point order; excludes the introspection command. Commands provided by external executables MAY be omitted, and the tool MUST document that they are. |
| `command` | object | Present exactly when the tool has one unnamed command: that command's D8 detail. |

**D7b** Each command entry MUST contain `name`, `description`, and `effects`, and MUST NOT contain invocation details. `name` MUST consist of non-empty segments separated by exactly one U+0020, or be `""` for the unnamed command, and MUST be unique within `commands`. `description` MUST distinguish neighboring commands, and `effects` MUST be declared under R1. An entry MAY contain `conforming: false` to mark a retained command outside the conformance claim; omitted, it means `true`, and a marked entry itself remains subject to this clause. Command detail, not a command entry, MUST contain enough information to construct a call.

**D7c** In `conformance`, `name` MUST equal `cli-design-standard` and `standard` MUST equal this document's version. `extensions` MUST contain each claimed extension exactly once; a caller that does not recognize an extension name MUST NOT rely on that extension.

### D8: Command detail MUST expose the command contracts.

Fields marked `always` in the table below MUST be present. A conditional field MUST be present when its condition is true and MUST NOT be present otherwise.

| Field | JSON type | Presence | Contract |
|---|---|---|---|
| `name` | string | always | Full command path, or `""` for a tool with one unnamed command. |
| `description` | string | always | One-line purpose. |
| `args` | array | always | I1 positional argument descriptors. |
| `flags` | array | always | I1 command-specific flag descriptors. Effective flags are D7 `global_flags` plus this array. |
| `effects` | string | always | MUST equal `read_only`, `idempotent`, or `non_idempotent` under R1a. |
| `confirm` | boolean | always | MUST be `true` when any valid call may require `--yes` under R3a. |
| `interactive` | boolean | always | MUST be `true` when any valid call starts an interactive session under I5b and `false` otherwise. |
| `stream` | boolean | success emits a record stream | MUST be `true`. `output` describes one record; see O7. |
| `output` | object | success conveys data beyond the exit status, or `changed` is required under R5a | O4 JSON Schema for the success document or one O7 record. |
| `exit_codes` | object | adds or refines tool defaults | F1 additions or refinements that preserve tool-wide meanings. |
| `format_defaults` | object | differs from tool default | O2 output defaults. |

This non-normative example shows how the index and command detail fit together; the contract is in D7 and D8. The `mytool` examples in this document are independent fragments; each agrees with its own requirement, not with the others.
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
  "conformance": {"name": "cli-design-standard", "standard": "0.1.0-draft.4", "extensions": []},
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
  "description": "Deploy a service to an environment and return after acceptance",
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
        "enum": ["queued", "running"]
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
  "conformance": {"name": "cli-design-standard", "standard": "0.1.0-draft.4", "extensions": []},
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

`hashfile README.md` runs the command. `hashfile schema README.md` is an unknown path under D6d.

### D9: The introspection contract MUST be stable and versioned.

**D9a** `schema_version` MUST be a positive decimal integer encoded as a string. Callers should ignore unknown fields. A change that adds an optional introspection or output field MAY keep `schema_version` unchanged. A change that adds a required introspection field, removes an introspection field, or changes an introspection field's type or meaning MUST increment it.

**D9b** Tool versions documented as compatible MUST preserve existing command paths, input meanings and defaults, exit code meanings, F3 `kind` meanings, and structured output fields. An incompatible change MUST document its replacement and migration; changing `schema_version` alone is insufficient.

### D10: Agent guidance MUST add context, not repeat the interface.

The tool MAY ship `SKILL.md` or `AGENTS.md` when domain knowledge or workflows need explanation. Guidance MUST point to commands and the introspection output, and MUST NOT duplicate their catalogs.

## Stage I: Invocation and input

A caller may be a sandboxed process with no keyboard, a producer of generated bytes, or both. Input handling treats those bytes as data, not shell syntax. The tool resolves declared inputs, validates them before acting, and keeps external work bounded.

### I1: Every accepted argument and flag MUST have a defined input contract.

**I1a** D7 `global_flags` and D8 `args` and `flags` MUST expose it as a descriptor with the fields in the table below.

| Field | Type | Rule |
|---|---|---|
| `name` | string | MUST be present. Flag names omit leading hyphens; one character renders as `-n`, while longer names render as `--name`. |
| `description` | string | MUST be present. One line stating what the input controls. |
| `type` | string | MUST be present and equal `string`, `integer`, `number`, or `boolean`. |
| `required` | boolean | MUST be present. `true` means the caller must provide the input. |
| `default` | scalar or array | MUST be present when the parser supplies an actual default; see I1d. |
| `enum` | array | MUST be present and list every choice when the parser declares a closed choice set. Every item MUST match `type`. |
| `aliases` | array | MAY appear on flags and contain alternative names without leading hyphens. Alias rendering follows `name`. |
| `variadic` | boolean | MAY be `true` only on the last argument. It consumes the remaining positional values as an ordered array; with `required: true`, it consumes at least one. |
| `repeatable` | boolean | MAY be `true` only on flags. It allows repeated occurrences and resolves their values to an ordered array. |
| `accepts_stdin` | boolean | MUST be `true` when `-` selects stdin instead of a file. |

**I1b** Arguments MUST appear in argument order.

**I1c** A flag with `type: boolean` MUST set its value to `true` when given by its bare name and MUST NOT consume the following argument as its value; it MAY also accept both `--name=true` and `--name=false`.

**I1d** `default` is the built-in default. Scalar defaults MUST match `type`; variadic and repeatable defaults MUST be arrays whose items match `type`. Required inputs MUST NOT have a default. A value resolved at run time, from I2 sources or from the environment, such as the working directory or the newest available version, MUST be omitted and described in `description`. A parser sentinel meaning "not provided", including `null`, is not a default and MUST be omitted.

**I1e** Omitted `variadic`, `repeatable`, and `accepts_stdin` mean `false`; omitted `aliases` means no aliases.

**I1f** Any accepted value syntax, bound, path-resolution rule, dependency, conflict, or dynamic value-discovery path not expressed by another descriptor field MUST be stated in `description`.

Example descriptors:

- Argument: `{"name": "file", "description": "Files to upload", "type": "string", "required": true, "variadic": true}`
- Flag: `{"name": "tag", "description": "Tag to attach", "type": "string", "required": false, "aliases": ["t"], "repeatable": true}`

Together they accept `mytool upload --tag docs -t archive a.txt b.txt` and resolve both `file` and `tag` to ordered arrays.

### I2: Configuration MUST be declared, deterministic, and inspectable.

**I2a** Sources: accepted configuration files and tool-specific environment variables MUST be documented, and an undeclared tool-specific variable MUST NOT change behavior. Greenfield variables SHOULD use a consistent `<TOOL>_<OPTION>` prefix, such as `MYTOOL_LOG_LEVEL`. If a flag selects a configuration file, the tool MUST document whether that file replaces or augments project and user configuration and where it sits in the precedence.

**I2b** Precedence: when more than one source provides a value, resolution MUST be deterministic and documented. Greenfield paths SHOULD resolve in this order: `flags > environment > project configuration > user configuration > built-in defaults`.

**I2c** Inspection: layered configuration SHOULD expose each resolved value and its source while masking secrets.

Example: `--log-level debug` overrides `MYTOOL_LOG_LEVEL=info`, which overrides `log_level = "warning"` in project configuration and `log_level = "error"` in user configuration.

### I3: Long or generated input MUST use files or stdin, never argv.

**I3a** A command that accepts a document, script, request body, template, or other unbounded text MUST accept a file path and `-` for stdin.

**I3b** The tool MUST reject a call that selects stdin for more than one input.

The same manifest can come from a file or stdin. Its quotes, newlines, and flag-like text remain data rather than argv:

```console
$ mytool deploy service-a --env prod --manifest manifest.json
$ mytool deploy service-a --env prod --manifest - < manifest.json
```

### I4: Secrets MUST NOT be passed as argument or flag values.

**I4a** A command that needs a secret MUST provide a source usable in a non-interactive context, such as a credential store, file, stdin, or environment variable. Greenfield commands SHOULD use `--token-file PATH` for one secret and `--credentials-file PATH` for structured credentials; either flag SHOULD accept `-` for stdin. Secret sources and their precedence MUST be documented.

**I4b** A secret MUST NOT appear in help, introspection output, logs, errors, or normal output unless retrieval is the command's documented purpose.

With `--token-file token.txt` under `--verbose`, a diagnostic may name the source, such as `Using token from token.txt`, but not the token.

### I5: Behavior in a non-interactive context MUST be explicit and fail safely.

**I5a** Prompts: a command MAY prompt only in an interactive context and only by writing the prompt to a stream that is a TTY; otherwise it MUST NOT prompt. When the environment variable `NO_INPUT` is non-empty, the context is non-interactive regardless of the stdin TTY. If required input or confirmation remains unresolved, the command MUST fail with an error that names a flag, file, stdin form, or environment variable that can supply it. A command MUST NOT prompt while stdin supplies an input. The absence of a prompt, an unanswered prompt, and end of input MUST NOT be treated as consent.

**I5b** Interactive sessions: a command MAY start an interactive session only when stdin and stdout are TTYs and the selected stdout format is human-readable; otherwise it MUST fail before side effects. A command that offers such a session MUST declare `interactive: true` in D8. Starting an external editor is an interactive session.

**I5c** Human action: a workflow MAY require an out-of-band human action. Its entry point MUST work in a non-interactive context and be discoverable through D7 and D8. Work that continues after that command exits falls under Stage M. In a non-interactive context, a command MUST NOT wait for a human action outside the call, such as a browser or device approval, unless that wait is the command's documented purpose; it MUST instead fail before side effects and name the entry point or I4 source that resolves it.

**I5d** Paging: a pager MAY start only when stdout is a TTY and the selected stdout format is human-readable; see H3.

While stdin supplies the manifest, the command cannot prompt for confirmation, so it fails and names `--yes`:

```console
$ mytool deploy api --env prod --manifest - < manifest.json
Error: Deploying 'api' to prod requires confirmation
Run: mytool deploy api --env prod --manifest - --yes
```

### I6: Invalid input MUST fail before side effects.

**I6a** The tool MUST reject unknown flags, unsupported arguments, invalid values, and conflicting inputs as usage errors. A usage error MUST use F3 `kind` `invalid_input`.

**I6b** `--` MUST end flag parsing; later tokens MUST NOT be interpreted as flags. A greenfield command SHOULD accept flags before, between, and after positional arguments up to `--`.

**I6c** The tool MUST validate every locally checkable input before changing state.

**I6d** A usage error SHOULD identify the invalid input and show the accepted form or nearest valid name.

### I7: Input MUST stay within its declared bounds.

**I7a** Buffered data: a command that buffers caller-controlled input MUST document and enforce a maximum size before side effects.

**I7b** Restricted paths: a command limited to declared roots MUST resolve each supplied path and reject it when it escapes those roots, including through `..` or a symbolic link.

For example, assume `mytool upload` accepts at most 10 MiB and may read files only from `./dist`; both calls fail with an F3 object on stderr:

```console
$ mytool upload ../secrets.txt --json
{"error":{"kind":"invalid_input","message":"Path must resolve inside ./dist"}}

$ cat 20-mib.bin | mytool upload - --json
{"error":{"kind":"invalid_input","message":"Input exceeds the 10 MiB limit"}}
```

### I8: External work MUST be bounded or explicitly unbounded.

**I8a** Connection establishment and non-streaming network operations MUST use finite default timeouts. A command that waits for external state, when waiting is not its documented purpose, MUST use a finite default deadline. A wait for a human action falls under I5c.

**I8b** A command whose documented purpose is to wait, watch, follow, or run external work to completion MAY be unbounded by default, but MUST accept `--timeout`; its I1 descriptor MUST carry a finite default deadline as `default` or state in `description` that the wait is unbounded by default. `--timeout` MUST accept an integer immediately followed by `s`, `m`, or `h` and MAY accept other forms, such as a bare integer with a documented unit.

**I8c** Any other unbounded mode MUST require explicit selection.

A bounded call that sets a deadline, and an unbounded call that explicitly selects that mode:

```console
$ mytool jobs wait job_123 --timeout 5m
$ mytool logs job_123 --follow
```

The `--timeout` descriptor of a wait that is unbounded by default carries no `default` and says so:

```json
{"name": "timeout", "description": "Give up after this duration, such as 30s or 5m; unbounded by default", "type": "string", "required": false}
```

## Stage R: Repeatability and mutation safety

This stage covers calls that mutate state or may be repeated. Safeguards follow the possible damage, not merely whether a command changes state. A tool whose every command declares `effects: read_only` has no mutation requirements under R2-R5. R6 applies when the tool retries requests internally.

### R1: Effect metadata MUST be conservative.

**R1a** Every D7 command entry and D8 command detail MUST declare one value from the table below.

| `effects` | Contract |
|---|---|
| `read_only` | The command does not change intended state managed or targeted by the tool. |
| `idempotent` | The command may change intended state, but repeating a successful call with the same inputs, without an intervening change to the targeted state, MUST succeed without another intended state transition. |
| `non_idempotent` | The command meets neither preceding guarantee; a repeat may cause another intended effect or return a stable conflict. |

**R1b** The declaration MUST cover every valid call. Declare `non_idempotent` when any call lacks the repeat guarantee. Otherwise declare `idempotent` when any call can change intended state. Otherwise declare `read_only`. A changing response, incidental telemetry, logs, caches, metering, or rate limiting do not alone change the classification.

For example, a delete by stable identifier whose repeat succeeds with `changed: false` is `idempotent`; a delete whose repeat fails with `not_found`, or whose targets are resolved at run time and may differ on a later repeat, such as the newest item or every stale item, is `non_idempotent`.

### R2: Mutation safeguards MUST match the blast radius.

**R2a** A mutation is wide when it can affect existing targets the caller did not name individually. It is irreversible when the tool provides no documented operation that restores the prior state.

**R2b** A mutation MUST carry at least the minimum safeguard listed for its operation in the table below; idempotence does not reduce these safeguards.

| Operation | Minimum safeguard |
|---|---|
| `effects: "read_only"` | None |
| Narrow, reversible mutation | None |
| Narrow, irreversible mutation | Confirmation under R3b |
| Wide mutation | Confirmation under R3b, and `--dry-run` under R4 |

**R2c** An M3 cancellation of exactly one managed operation by its M1 identifier does not require an additional confirmation. Any wider cancellation follows the table.

### R3: Safety gates MUST fail closed and be discoverable.

**R3a** Every command that can require `--yes`, including those required under R2b, MUST declare `confirm: true` in D8. A command that declares `confirm: true` MUST accept `--yes`.

**R3b** Without `--yes`, a call in a non-interactive context that would perform the gated effect MUST stop before side effects and fail with `kind` `confirmation_required`, naming `--yes`. The gate applies after every check the call performs before side effects: a call that would fail before reaching the gated effect, such as on a missing target, MUST fail with that `kind` and MUST NOT require `--yes`.

**R3c** A `--dry-run` call MUST NOT require `--yes`. A command that accepts `--yes` MUST accept it with `--dry-run` and ignore it.

**R3d** `--yes` confirms a prompt; `--force` overrides a documented precondition. Accepting one MUST NOT enable the other.

A documented precondition that `--force` overrides is not met, so the call fails with an F3 object on stderr and names the override:

```console
$ mytool services delete api --json
{"error":{"kind":"precondition_failed","message":"Service 'api' still has 2 running deployments","hint":"Repeat with --force to delete it anyway"}}
```

A gated call in a non-interactive context, here with `--json` and no TTY on stdin, stops before side effects and fails with an F3 object on stderr; under R4, the same command previews without `--yes`:

```console
$ mytool services prune --env staging --json < /dev/null
{"error":{"kind":"confirmation_required","message":"Pruning staging services requires confirmation","hint":"Repeat with --yes"}}
```

### R4: Wide mutations MUST be previewable.

**R4a** The command MUST provide `--dry-run`.

**R4b** On any command that accepts it, a `--dry-run` call MUST leave intended state unchanged, SHOULD apply the same permission checks as the mutating call, and MUST fail with the `kind` the mutating call would fail with before side effects, except `confirmation_required`.

**R4c** The structured success of a `--dry-run` call MUST conform to the same D8 `output`, list each target the mutating call would affect as observed during that call in an array field `targets`, whose item schema is tool-defined, and return `changed: false`. A value produced only by performing the mutation MUST be omitted or `null`.

Preview and mutation share one output schema; this tool also lists `targets` in the mutation's own result, which R4c does not require:

```console
$ mytool services prune --env staging --dry-run --json
{"targets":["api","worker"],"changed":false}

$ mytool services prune --env staging --yes --json
{"targets":["api","worker"],"changed":true}
```

### R5: Mutating commands MUST report what happened.

**R5a** Every command whose `effects` is not `read_only` MUST declare a boolean `changed` in its D8 output and return it in every structured success response. `changed` reports whether this call caused a new intended state transition, not whether background work completed.

**R5b** When authoritative state reports a concurrent conflict, the tool MUST fail with `kind` `conflict` and MUST NOT silently overwrite it.

**R5c** A `non_idempotent` command whose repetition could duplicate an effect SHOULD accept `--idempotency-key` when the backing service supports idempotency keys.

For example, an idempotent create-or-get may return `changed: true` and then `changed: false`. A strict create may return `changed: true` and then fail with `kind` `conflict`. Under O3c, human-readable output of a repeated idempotent delete reports absence rather than deletion, for example `Already absent: api`.

### R6: Built-in retries MUST be safe and bounded.

A tool that retries requests internally MUST retry only failures that would be reported with `retryable: true` under F3b, and only for `read_only` or `idempotent` commands, or requests protected by an idempotency key. It MUST preserve the original inputs, limit the number of attempts, and remain within the I8 timeout. It SHOULD honor `Retry-After` when the timeout allows.

## Stage O: Output

A caller should be able to select a representation before execution, parse stdout without filtering diagnostics, and consume large results without mistaking one page for the whole result.

### O1: The standard streams MUST be classified independently.

The TTY state of stdin is one input to the prompt policy under I5a, stdout controls the default format under O2c, and stderr controls diagnostic decoration under O3b and whether F2 requires the structured error object. Redirecting one stream MUST NOT change how another is classified.

### O2: Output format selection MUST be explicit and predictable.

**O2a** Declaration: D7 `format_defaults` MUST declare `tty` and `non_tty` format names. D8 `format_defaults` MUST appear only when a command differs from those tool-wide defaults. For a `stream: true` command the machine-readable format name is `ndjson`.

**O2b** Machine access: every command MUST accept `--json`. On a command without `output`, `--json` selects the `json` format, and a success MUST write no bytes to stdout. If a command also accepts `--format`, `--json` MUST produce the same output as `--format json` or, when D8 declares `stream: true`, as `--format ndjson`. A retained `--json` that requires a value is an incompatible path under Conformance; the same command conforms once bare `--json` selects the D8 `output` document.

**O2c** Defaults: a greenfield command with D8 `output` SHOULD default to human-readable output on a TTY. On non-TTY stdout, a command with D8 `output` MUST default to JSON or NDJSON, except that a command whose primary result is a textual document rather than a set of fields or records MAY default to a declared native format such as text or Markdown. A brownfield command MAY retain an established non-TTY default when it is declared in `format_defaults`.

**O2d** Precedence: an explicit format flag MUST override the detected default. Conflicting explicit format flags MUST be usage errors.

**O2e** Names: a greenfield command MUST NOT accept `--output`. If it accepts a destination path, the flag MUST be named `--output-file`. Under `--output-file`, the file receives exactly what stdout would have received, O5 applies to that file, and a success writes no bytes to stdout. Formats use `--json` or `--format`.

A command without `output` under `--json`, and a command with `output` under `--output-file`; both exit `0` and write no bytes to stdout, and the second leaves the result in `services.json`:

```console
$ mytool config validate --json
$ mytool services list --json --output-file services.json
```

### O3: The output streams MUST have separate roles.

**O3a** Channels: stdout MUST contain only the result; stderr MUST carry logs, warnings, progress, prompts, and errors. `--quiet` and `--verbose`, when accepted, change only stderr diagnostics.

**O3b** Decoration: machine-readable stdout MUST contain only output in the selected stdout format, without banners, terminal decoration, or ANSI escapes. Terminal decoration MAY appear only when its stream is a TTY or a documented flag or environment variable forces it. Animated progress MAY appear only when stderr is a TTY. On non-TTY stderr, progress MUST use complete plain lines or be omitted.

**O3c** Consistency: human and machine renderings MAY differ in detail but MUST NOT contradict each other. When human-readable output is only a bounded preview of the result, it MUST say so and identify how to retrieve the complete result.

**O3d** Untrusted content: machine output MUST serialize caller-controlled and remote values through the selected stdout format. Human output MUST escape terminal control sequences in those values.

### O4: A command schema MUST describe its JSON success value.

**O4a** The D8 `output` field describes one success document, or one record when D8 declares `stream: true`. It MUST follow JSON Schema Draft 2020-12 and use only `type`, `enum`, `properties`, `required`, and `items`.

**O4b** Every schema MUST contain `type`, except that a schema MAY be the empty object `{}`, meaning any JSON value, where the value's shape depends on the input. `type` MUST be `string`, `integer`, `number`, `boolean`, `array`, or `object`, or a two-element array containing one of those types and `null`.

**O4c** `enum` MAY restrict a value to a finite set. Every member MUST conform to the same schema. `enum` MUST list only values the current version can return.

**O4d** An array schema MUST contain `items`. An object schema MUST contain `properties`, which lists every field the current version may return, and `required`, which lists every always-present field.

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

### O5: JSON output MUST match its declared contract.

**O5a** Document: unless D8 declares `stream: true`, a `--json` success of a command with `output` MUST contain exactly one JSON value conforming to that schema, encoded as UTF-8 and followed by LF. A failed document call MUST NOT write a JSON value to stdout.

**O5b** Values: values MUST keep their declared JSON types. Machine output MUST NOT silently truncate a value.

**O5c** Bounded values: a command that may cap a single inline value MUST declare a required boolean `truncated` and an optional string `output_file` in its D8 output schema. Every result MUST return `truncated`. When `truncated` is `true`, `output_file` MUST identify a file that holds the complete value. The file SHOULD NOT be accessible to other users. The inline value is a preview, and the file's retention MUST be documented. Collections and record streams MUST use O6 and O7 instead.

**O5d** Time: timestamps MUST use RFC 3339 with a numeric offset or `Z`. Numeric duration field names MUST state their unit.

Output matching the O4 example schema:

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

### O6: Potentially unbounded document collections MUST be bounded.

**O6a** An R4 target list, in a preview or in the mutation's own result, is not a collection under this requirement; a command that caps it falls under O5c.

**O6b** Window: a collection without a documented finite maximum MUST use a finite default limit and accept `--limit`. The tool MUST bound the number of items, not silently omit fields from individual items. An explicit `--limit` is the maximum number of items returned by that call.

**O6c** Shape: a bounded collection MUST be an object with an `items` array and a boolean `has_more` that is `true` exactly when matching items exist beyond those returned. A collection with a documented finite maximum MAY use a bare array. An empty collection MUST use the same shape with an empty array, not `null` or absent output.

**O6d** Under the `continuation` extension: the command MUST accept `--cursor`, and each JSON page MUST contain `next_cursor`, an opaque string that the caller passes unchanged to `--cursor`, or `null` on the final page. `has_more` MUST be `true` if and only if `next_cursor` is not `null`. Source, filters, and order MUST remain unchanged when using `--cursor`; the limit and output format MAY change. If the cursor is invalid, expired, incompatible, or cannot continue the same result set, the command MUST fail with `kind` `cursor_unavailable`. It MUST NOT silently restart from another position. Pagination MUST use a stable, documented order and document whether pages read live state or one fixed snapshot.

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

### O7: Record streams MUST be bounded and framed.

This requirement applies to a command with D8 `stream: true`.

**O7a** Framing: `--json` MUST emit UTF-8 NDJSON with one complete JSON object per LF-terminated line and no blank lines. Each record MUST conform to D8 `output` and become readable before the command waits for another record or exits. Each record falls under O5b, O5d, and D9.

**O7b** Window: without `--follow`, the command MUST terminate. A stream without a documented finite maximum MUST use a finite default limit and accept `--limit`. `--follow` removes that default limit. An explicit `--limit` remains effective with or without `--follow` and ends the read after that many records. Reaching a limit ends that read, not the record source.

**O7c** Ordering: the stream MUST use a stable, documented order and MUST NOT stop before the effective limit while matching records are available.

**O7d** Following: a follow mode MAY exist, SHOULD be named `--follow`, and MUST require explicit selection under I8c.

**O7e** Completion: exit `0` means the requested read ended successfully, not that the record source is exhausted; empty stdout is valid. After a non-zero exit, prior LF-terminated records remain valid. An unterminated final fragment is not a record. This standard defines no end record; EOF and the exit status are authoritative.

**O7f** Under the `continuation` extension: `output` MUST be an object schema with `cursor` as a required string property, and each `cursor` MUST be a non-empty opaque string. The command MUST accept `--after-cursor` and resume strictly after that record without skipping any matching record in the same logical stream. Inputs selecting the source, filters, or order MUST remain the same; limits, following, timeouts, and output format MAY change. If this continuation cannot be guaranteed because the cursor or required history is invalid, expired, or incompatible, the command MUST fail with `kind` `cursor_unavailable`; it MUST NOT silently resume elsewhere.

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

### O8: Output MUST survive normal pipeline closure.

When a downstream reader closes a pipe, a command that has not otherwise failed MUST stop writing and emit no stack trace or broken-pipe diagnostic. Its exit status MAY follow the platform's pipe-closure convention; any non-zero meaning MUST be documented under F1c.

## Stage F: Failure

Failures need a stable machine signal and enough information for the caller to choose its next action. Success must not hide incomplete or uncertain work.

### F1: Exit codes MUST be stable and documented.

**F1a** Unless a released contract assigns another meaning to `1` or `2`, tool-wide D7 `exit_codes` MUST contain the decimal-string keys in the table below with these meanings. A tool that retains such a released meaning MUST document, in `exit_codes`, the code it uses for each meaning in the table.

| Code | Meaning |
|---|---|
| `0` | Success, including an empty result or no differences. |
| `1` | Generic failure. |
| `2` | Usage error. |

**F1b** Exit `0` MUST mean the command observed its documented postcondition through the interface it used. Independent re-verification is not required. For managed operations, acceptance and completion fall under M1 and M2.

**F1c** Additional codes MUST each have one stable meaning. Fine-grained failures MUST use F3 `kind` instead.

**F1d** D8 command `exit_codes` MUST appear only when they add a code or refine a tool-wide description without changing its meaning.

### F2: Structured errors MUST have one location.

To fail with a `kind` is to exit non-zero and, wherever this requirement demands the object, emit an F3 object with that `kind`; other requirements cite this definition. When the tool exits with an error, stderr MUST contain the F3 `message` and, when the error has one, its `hint`, as human-readable diagnostics or inside the F3 JSON object. The tool MUST emit that object when the selected stdout format is machine-readable or stderr is not a TTY, including under `--quiet`; otherwise the object MAY be omitted. Whenever the object is emitted, it MUST be the last non-empty stderr line, and a requirement that names an F3 `kind` applies to it. The object MUST NOT be written to stdout.

The same failure with `--json`, as an F3 object on stderr, and at a terminal:

```console
$ mytool deploy api --env prod --yes --json
{"error":{"kind":"image_not_found","message":"Cannot deploy 'api': image 'web:v2.1.0' was not found","hint":"Run mytool images list web"}}

$ mytool deploy api --env prod --yes
Error: Cannot deploy 'api': image 'web:v2.1.0' was not found
Run: mytool images list web
```

### F3: Structured errors MUST have a stable envelope.

**F3a** The document MUST contain exactly one top-level field, `error`, whose value is an object with the fields in the table below. Its `kind` is the only stable match target; message text is not a stable interface.

| Field | Presence | Contract |
|---|---|---|
| `kind` | MUST | String with stable machine meaning; the values in the `kind` table below have shared meanings. |
| `message` | MUST | String identifying the failed operation and cause. |
| `retryable` | MAY | Boolean; see F3b. |
| `action` | MAY | `agent` when the caller can recover autonomously, `user` when human action is required, or `none` when no recovery action exists. |
| `hint` | SHOULD | String recovery step; see F3b. |
| `context` | MAY | Object containing machine-readable values needed for recovery. |

**F3b** `retryable` is `true` only when the same call may resolve the failure without duplicating an intended effect; when it is omitted, the caller has no assurance that a retry is safe. `hint` is present when one concrete recovery step is known; omit it rather than guess.

**F3c** A tool MUST NOT use a `kind` listed below with another meaning. It SHOULD use a listed `kind` when its definition applies. A requirement that names a `kind` keeps its own keyword. Any other `kind` is tool-defined. A released `kind` whose meaning conflicts with the table is brownfield: the tool MAY retain it and MUST document it as not conforming.

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
| `operation_failed` | A managed operation reached a terminal state other than `succeeded`; `context` carries the identifier and `status`. | M1, M2 |
| `precondition_failed` | A documented precondition that `--force` overrides is not met. | |

A complete error object with every field:

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

### F4: Fallbacks and uncertain outcomes MUST be explicit.

**F4a** If a failed command may have caused an intended effect and did not observe the outcome, it MUST use F3 `kind` `outcome_unknown` and MUST NOT report completion or absence. Known completed effects SHOULD be listed in `context` under `completed`, an array of the affected targets as the caller named them. Which prior stdout remains valid falls under O5a and O7e.

**F4b** If usable partial results survive a failure, the structured error SHOULD identify them in `context`.

**F4c** After a failure, a command MUST NOT silently replace the requested target, source, or mode. It MUST fail with a `kind` or identify the substitution in its declared structured result.

A timed-out request whose effect was not observed:

```json
{"error":{"kind":"outcome_unknown","message":"The deployment request timed out and its outcome could not be determined","retryable":false,"context":{"deployment_id":"dep_123"}}}
```

### F5: User interruption MUST fail honestly.

A command that receives the platform's normal user-interrupt request MUST exit without a stack trace and fail with `kind` `interrupted`, unless F4 requires `outcome_unknown`. Interrupting observation of managed work MUST NOT cancel or otherwise change that work.

## Stage M: Managed operations

A tool without managed operations has no Stage M requirements.

### M1: Accepted work MUST remain identifiable.

**M1a** A command that exits before requested work finishes MUST return a non-empty canonical identifier in structured success output. Its field name is tool-defined but MUST remain consistent across the command that starts the work and every command that addresses it. If the command that starts the work fails after obtaining the identifier, any F3 object it emits MUST carry the identifier in `context` under the same field name.

**M1b** Exit `0` means the work was accepted, not completed. The identifier MUST remain usable after the initiating process exits and MUST NOT later resolve to a different entity. Its D5 breadcrumb SHOULD name the wait command.

**M1c** When a command offers both waiting for completion and returning after acceptance, selecting the latter MUST change only how long the command waits, not the work it starts. Its flag SHOULD take its name from H1b. The D8 `description` of a command that starts managed work MUST state whether it waits for completion by default. A command that waits for the work it started MUST fail with `kind` `operation_failed` when that work does not succeed. If its deadline passes after the work was accepted, it MUST fail with `kind` `outcome_unknown` and carry the identifier under M1a.

A `deploy` that waits for its deployment, and the wait command observing the same terminal state under M2, both fail on stderr with `operation_failed` and carry the identifier:

```console
$ mytool deploy api --env prod --yes --json
{"error":{"kind":"operation_failed","message":"Deployment dep_123 failed: image pull error","context":{"deployment_id":"dep_123","status":"failed"}}}

$ mytool deployments wait dep_123 --json
{"error":{"kind":"operation_failed","message":"Deployment dep_123 failed","context":{"deployment_id":"dep_123","status":"failed"}}}
```

### M2: Managed work MUST expose status and wait.

**M2a** Commands: the tool MUST provide commands, usable in a non-interactive context, for inspecting current status and waiting for a terminal state. Both MUST accept the identifier returned under M1a; their names fall under D4b. Both commands MUST declare `effects: read_only`. The status command MUST report the current state without waiting for a terminal state.

**M2b** Results: structured results from both commands MUST contain `status` and the identifier under the same field name. The F3 object of a failed wait MUST carry `status` and the identifier in `context`.

**M2c** Status values: the D8 output schema MUST declare `status` as a finite enum containing terminal values `succeeded` and `failed`, plus `canceled` when cancellation exists. It MAY add values for unfinished states and MUST add `unknown` when an existing operation's current state can be indeterminate. `unknown` MAY be returned only when the tool successfully observes an underlying state that explicitly represents indeterminacy. A timeout, transport error, or other failure to read state MUST fail with the applicable `kind` and MUST NOT return `unknown`.

**M2d** Identifiers: any retention or expiry policy for managed operations MUST be documented. An unrecognized or expired identifier MUST fail with `kind` `not_found` and MUST NOT be reported as an operation state.

**M2e** Wait: the wait command MUST exit `0` only when it observes the terminal state `succeeded`; any other terminal state MUST fail with `kind` `operation_failed`. Failure to observe the operation MUST fail with the applicable `kind`. The wait command MUST accept `--timeout` under I8b; its own deadline fails with `kind` `timeout`. It MUST return immediately when the operation is already terminal. Timing out or terminating it MUST NOT cancel or otherwise change the operation, and MUST NOT be reported as a terminal operation outcome.

**M2f** Listing: the tool SHOULD provide a command, usable in a non-interactive context, that lists managed operations with the identifier under the same field name and `status`; its result falls under O6.

### M3: Cancellation MUST be honest.

**M3a** If a managed operation can be canceled, the tool MUST provide a cancellation command, usable in a non-interactive context, whose name falls under D4b. It MUST accept the identifier returned under M1a, declare `effects: idempotent`, and fall under Stage R.

**M3b** Structured success MUST contain `status` and the identifier under the same field name; `changed` falls under R5a. Exit `0` means cancellation was accepted or a terminal state was observed, not necessarily that the operation was canceled. The command MUST NOT report `canceled` until it observes that state; if the operation wins the race, it MUST report the actual terminal state.

A cancellation that is accepted, then observed by the wait command, which fails on stderr because the terminal state is not `succeeded`:

```console
$ mytool jobs status job_123 --json
{"job_id":"job_123","status":"running"}

$ mytool jobs cancel job_123 --json
{"job_id":"job_123","status":"canceling","changed":true}

$ mytool jobs wait job_123 --timeout 5m --json
{"error":{"kind":"operation_failed","message":"Job job_123 was canceled","context":{"job_id":"job_123","status":"canceled"}}}
```

### M4: Resumable suspension MUST remain distinct from cancellation.

**M4a** If managed work can be suspended and later resumed from the same point, the tool MUST expose suspension and resumption commands, usable in a non-interactive context, whose names fall under D4b. Both MUST accept the identifier returned under M1a, declare `effects: idempotent`, and return the identifier, `status`, and `changed` in structured success.

**M4b** They MUST report only a status they observed. While suspended, `status` MUST be `paused` and non-terminal. Cancellation under M3 remains terminal and MUST NOT mean suspension. On an operation that is already terminal, they fall under M3b.

## Stage H: Human interface

A person at the terminal should find familiar flag names, standard environment behavior, and output that remains readable without color.

### H1: Greenfield flags MUST have canonical long names.

**H1a** A greenfield flag MUST use kebab-case, and each concept MUST have one canonical long name.

**H1b** When the tool supports a concept in the table below, it SHOULD use the listed long name; a requirement that names a flag keeps its own keyword. A listed alias MAY be added when it has no conflicting local meaning. Every accepted alias MUST behave exactly like its canonical flag and appear in the I1 descriptor.

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
| Write the result to a path | `--output-file PATH` | No recommendation | O2 |
| More diagnostics | `--verbose` | `-v` | O3 |
| Less diagnostics | `--quiet` | `-q` | O3, F2 |
| Bound returned items or records | `--limit N` | No recommendation | O6, O7 |
| Resume a collection | `--cursor CURSOR` | No recommendation | O6 (`continuation`) |
| Resume a stream after a record | `--after-cursor CURSOR` | No recommendation | O7 (`continuation`) |
| Keep reading new records | `--follow` | No recommendation | O7 |
| Return after accepting managed work | `--background` | `--bg` | M1 |
| Control color | `--color WHEN` | No recommendation | H4 |
| One item per line | `--plain` | No recommendation | H5 |

### H2: Tools with nested commands SHOULD provide shell completions.

When provided, static command, flag, and alias candidates MUST match the installed interface.

### H3: External editors and pagers MUST respect user selection.

A tool that starts an editor MUST prefer `VISUAL` to `EDITOR` unless a documented setting overrides them. A tool that starts a pager MUST honor `PAGER` unless a documented setting overrides it.

When an editor or pager may start falls under I5b and I5d.

### H4: Color MUST remain optional.

**H4a** A tool that emits color MUST disable it when `NO_COLOR` is non-empty, `TERM` is `dumb`, or the output stream is not a TTY. A flag or a documented setting overrides that default on human-readable output only. Color MUST NOT be the only carrier of information.

**H4b** If provided, the color flag MUST be `--color` with the values `auto`, `always`, and `never`: `auto` applies that default, and the other two override it. `--no-color` MAY be provided as `--color=never`. `--color always` has no effect on `--plain` output.

At a terminal, `NO_COLOR=1 mytool services list` and `TERM=dumb mytool services list` print no color. In a pipe, `mytool services list --format text --color always | less -R` keeps color because the output is human-readable, while `mytool services list --color always | jq .` emits none because stdout is then machine-readable under O2 and O3.

### H5: A command whose result is a complete collection under O6 SHOULD offer `--plain`.

**H5a** A command whose result is bounded under O6b MAY offer it only for a page explicitly selected with `--limit` or, when the tool declares `continuation`, `--cursor`.

**H5b** `--plain` MUST emit one item per LF-terminated line, with no heading or terminal decoration. The line format MUST be documented and stable; if items can contain LF, its escaping MUST be documented. If `--format` exists, `--plain` MUST equal `--format plain`.

Three services, one per line:

```console
$ mytool services list --plain
api
worker
scheduler
```
