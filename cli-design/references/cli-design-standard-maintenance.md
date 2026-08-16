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

## Change workflow

1. Make the smallest change that resolves the caller-facing problem.
2. Read the affected stage in full and inspect every referenced requirement.
3. Recheck terminology, examples, data flow, brownfield impact, and compatibility.
4. For a material contract change, review one stable draft independently and deduplicate the findings before editing again.
5. Run the checks below and review the rendered document before changing its version.

## Verification

Run these checks from the `haz-skills` repository root:

- `git diff --check` detects whitespace errors.
- `rg -n '—|[ \t]+$' cli-design/references/cli-design-standard.md` detects prose em dashes and trailing whitespace. No matches are expected.
- `rg -n '^\|' cli-design/references/cli-design-standard.md` detects table rows that escaped their containing list. No matches are expected with the current layout.
- `pandoc -f gfm -t html cli-design/references/cli-design-standard.md -o /tmp/cli-design-standard.html` renders the document for inspection.
- A short `uv run --no-project python` check parses every fenced `json` block, verifies unique requirement IDs, and rejects unresolved references to requirement IDs.

Tests and build steps are N/A unless executable conformance tooling is added later.
