# Changelog

## [0.2.0-draft.12] - 2026-10-20

Draft published on `main` so tools can pin it. A draft claim names that draft only (Conformance); a tool claiming `0.1.0` checks the contract changes below before updating its claim. The per-clause record with the compatibility verdict for each change becomes the `0.2.0` section when the drafts close.

### Added

- `conversational` extension: session and turn identity, follow-up and correction, limits and automatic continuation, answer presentation with counted answer tags (`<answer-N>`), and queue requirements.
- R2d: an explicit resource and action policy as an alternative to plan preview and confirmation for agent actions.
- R7a multi-field work identifiers documented in `output_description`; R7d deadline semantics for synchronous work; M1g selector-based status and wait; M2c cancel stops scheduled automatic resumption.
- Maintenance guide: identifier map (old to new) whenever a change reletters clauses.

### Changed

- Loosened: D4a noun-verb structure and I8b heartbeat interval to SHOULD; D10 catalog duplication to SHOULD NOT; I3a `-` required only for text the tool itself interprets; R5c idempotency keys only when the client can send them; R2b narrow overwrite of the call's own target enabled by `--force` alone; I4b limited to secrets the tool uses; I1a a spelling mapped onto a listed `enum` choice is that choice; D5d introspection routing for a tool with an unnamed command plus named commands; O3d escaping mandate defined as ESC-introduced sequences and C1 controls.
- Clarified: O2e `--output-file` is result delivery (replaces the destination without confirmation, no file when there is no result); O2c the TTY default also applies to a machine caller on a PTY; D8a points to the tool-version rules (D8b) for command output changes; D7 `output_description` names fields that do not add up or share a name with a different meaning; D10 guidance may describe tool-defined error kinds; O5a a JSON document may be indented on a TTY.
- Relettered: the I5d pager rule is now I5e; a new I5d covers input needed after work was accepted.

## [0.1.0] - 2026-09-12

### Added

- Initial CLI Design Standard for Humans and Agents, defining discovery, input, mutation safeguards, output, failure handling, and human interface requirements.
- Machine-readable command introspection, structured errors and recovery commands, and rules for reporting partial results.
- Conformance declarations and adoption rules for tools with existing released interfaces.
- Optional `continuation` and `managed` extensions for resumable reads and observable accepted work.
- A maintenance guide and a checker for the standard's document invariants. The checker does not certify tool behavior.

[0.2.0-draft.12]: https://github.com/DamianPala/haz-skills/releases/tag/cli-design-standard-v0.2.0-draft.12
[0.1.0]: https://github.com/DamianPala/haz-skills/releases/tag/cli-design-standard-v0.1.0
