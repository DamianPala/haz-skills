# CLI Design Standard for Humans and Agents maintenance

This document governs changes to the standard. It is non-normative and does not affect tool conformance. Its keywords describe admission decisions, not requirements for conforming tools.

## Requirement policy

A candidate requirement must satisfy P1-P6 before it enters the standard.

- **P1: A requirement MUST address a material caller contract, failure mode, safety risk, or interoperability need.** It SHOULD be supported by an established convention, an observed failure, or explicit engineering reasoning. Aesthetic preferences and implementation taste belong in guidance, not the standard.
- **P2: A requirement MUST define a verifiable outcome.** Its pass or fail condition MUST be observable through behavior, a contract test, or a deterministic audit. Otherwise it belongs in implementation guidance.
- **P3: A requirement MUST be placed according to its scope.** It belongs in the standard only if it applies to every conforming tool or states an observable applicability condition explicitly. An isolated narrow recommendation belongs in implementation guidance.
- **P4: A requirement MUST state the minimum necessary contract once.** It specifies an outcome rather than an implementation mechanism unless the mechanism is necessary for interoperability, safety, or verification. Other rules cross-reference it instead of restating it. Examples and rationale clarify a requirement but do not expand it.
- **P5: A requirement MUST use the weakest normative keyword that preserves its purpose.** Its strength and implementation cost MUST be proportionate to the consequence of non-conformance.
- **P6: A requirement MUST be practical to implement, verify, and maintain throughout the tool's lifecycle.** A requirement that demands disproportionate engineering effort, predictably drifts out of conformance, or lacks a credible implementation path belongs in implementation guidance or MUST be rejected.

A candidate extension name enters the standard only when it names one guarantee a tool cannot provide by accident, and the name alone tells a caller what it may rely on without inspecting each command. A guarantee a caller can only use after reading command detail stays a conditional requirement.

A new reserved field name or `kind` MUST be a multi-word `snake_case` name; a new reserved flag MUST be a multi-word kebab-case long name under H1a. A draft.6 audit of output fields from AWS service models, `gh`, and npm found collisions among the reviewed single-word candidates and none among the multi-word `snake_case` candidates the standard reserved.

A candidate requirement is checked against existing tools that never read this document. One that most such tools already satisfy records a convergence, and the convergence is its justification. One that no such tool satisfies and none contradicts is an addition; it may be right, and it carries an adoption cost a convergence does not. One that several unrelated tools independently decided against needs an argument beyond this document's internal consistency. The kinds are not labels in the standard; the scoring of each version's requirements lives in the maintainers' notes.

## Known limits

Shapes the conformance claim cannot express in this version, each seen in one real tool:

- A unit of effect smaller than a command, such as a subcommand whose argument shape decides whether it mutates (`npm version` versus `npm version patch`). R1 classifies the whole command as `non_idempotent`, so its read-only invocation inherits that declaration.
- A suite of binaries sharing one flag vocabulary (`systemctl` and the other `*ctl` tools). Each binary claims on its own.
- A claim per upstream service inside one tool (`aws`). `scope` covers command-path prefixes, which matches services only where the path does.
- A collection returned in an upstream shape without a boolean equivalent to `has_more` (`aws` `NextToken`). O5e can map a reserved name only when that name already collides, and it cannot supply a missing meaning, so such a command stays outside the claim.

## Document policy

The standard stays short. Text that neither states a requirement, nor resolves an ambiguity in one, nor shows one working belongs elsewhere or nowhere. Design principles is the one non-normative section and stays short.

Requirement and clause identifiers are scoped to a version of this document: after inserting, splitting, or removing a clause, later clauses are relettered in reading order and internal references are updated; an external citation names the version.

## Change workflow

1. Make the smallest change that resolves the caller-facing problem.
2. Read the affected stage in full and inspect every referenced requirement.
3. Recheck terminology, examples, data flow, brownfield impact, and compatibility.
4. For a material contract change, review one stable draft independently and deduplicate the findings before editing again.
5. Run the checks below and review the rendered document before changing its version.

## Verification

Run these checks from the `haz-skills` repository root:

- `uv run --no-project python cli-design/scripts/check-standard.py` parses every fenced `json` block, reads requirement IDs from `### ID:` headings and verifies they are unique and in stage order, reads clause markers (`**R3c**` at the start of a paragraph) and verifies they belong to the enclosing requirement and run without gaps, rejects unresolved references to requirement or clause IDs, verifies that every `"standard"` value in examples equals the version in the header, and rejects em dashes, trailing whitespace, and indented table rows. It prints `file:line` for each problem and exits `1` when any check fails.
- `git diff --check` detects whitespace errors in the change itself.
- Read every clause the `core-behavior` profile retains that names a D7 or D8 field, and confirm that it states the behavior independently and that any declaration duty it carries can be satisfied by the prose substitute in Conformance. The profile excludes D6, D7, D8, D9a, and the introspection references Conformance names, so a declaration duty that leaks into another stage silently changes what the profile requires. This check is manual.
- `pandoc -f gfm -t html cli-design/references/cli-design-standard.md -o /tmp/cli-design-standard.html` renders the document for inspection.

The script checks document invariants only. Conformance of a tool against the standard is not automated.
