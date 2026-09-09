# CLI Design Standard for Humans and Agents maintenance

This document governs changes to the standard. It is non-normative and does not affect tool conformance. Its keywords describe admission decisions, not requirements for conforming tools. It states tests, not procedures, and stays as short as the standard.

## Requirement policy

A candidate requirement must satisfy P1-P6 before it enters the standard.

- **P1: A requirement MUST address a material caller contract, failure mode, safety risk, or interoperability need.** It SHOULD be supported by an established convention, an observed failure, or explicit engineering reasoning. Aesthetic preferences and implementation taste belong in guidance, not the standard.
- **P2: A requirement MUST define a verifiable outcome.** Its pass or fail condition MUST be observable through behavior, a contract test, or a deterministic audit. Otherwise it belongs in implementation guidance.
- **P3: A requirement MUST be placed according to its scope.** It belongs in the standard only if it applies to every conforming tool or states an observable applicability condition explicitly. An isolated narrow recommendation belongs in implementation guidance.
- **P4: A requirement MUST state the minimum necessary contract once.** It specifies an outcome rather than an implementation mechanism unless the mechanism is necessary for interoperability, safety, or verification. Other rules cross-reference it instead of restating it, in the form Document policy gives. Examples and rationale clarify a requirement but do not expand it.
- **P5: A requirement MUST use the weakest normative keyword that preserves its purpose.** Its strength and implementation cost MUST be proportionate to the consequence of non-conformance.
- **P6: A requirement MUST be practical to implement, verify, and maintain throughout the tool's lifecycle.** A requirement that demands disproportionate engineering effort, predictably drifts out of conformance, or lacks a credible implementation path belongs in implementation guidance or MUST be rejected.

A candidate extension name enters the standard only when it names one guarantee a tool cannot provide by accident, and the name alone tells a caller what it may rely on without inspecting each command. A guarantee a caller can only use after reading command detail stays a conditional requirement.

A new reserved field name or `kind` MUST be a multi-word `snake_case` name. A new reserved flag MUST be a multi-word kebab-case long name under H1a unless an established single-word CLI term is necessary for interoperability and the standard defines its meaning. A draft.6 audit of output fields from AWS service models, `gh`, and npm found collisions among the reviewed single-word candidates and none among the multi-word `snake_case` candidates the standard reserved.

A candidate requirement is checked against existing tools that never read this document. One that most such tools already satisfy records a convergence, and the convergence is its justification. One that no such tool satisfies and none contradicts is an addition; it may be right, and it carries an adoption cost a convergence does not. One that several unrelated tools independently decided against needs an argument beyond this document's internal consistency. The kinds are not labels in the standard; the scoring of each version's requirements lives in the maintainers' notes.

## Known limits

Shapes the conformance claim cannot express in this version, each seen in one real tool:

- A unit of effect smaller than a command, such as a subcommand whose argument shape decides whether it mutates (`npm version` versus `npm version patch`). R1 classifies the whole command as `non_idempotent`, so its read-only invocation inherits that declaration.
- A suite of binaries sharing one flag vocabulary (`systemctl` and the other `*ctl` tools). Each binary claims on its own.
- A claim per upstream service inside one tool (`aws`). `scope` covers command-path prefixes, which matches services only where the path does.
- A collection returned in an upstream shape without a boolean equivalent to `has_more` (`aws` `NextToken`). B4c can map a reserved name only when that name already collides, and it cannot supply a missing meaning, so such a command is incompatible under B2a and stays outside the claim.

## Document policy

The standard stays short. Text stays when it helps a reader apply a requirement: it states one, defines a term one uses, resolves an ambiguity in one, shows one working, says why it exists, or says where to read next. Anything else belongs elsewhere or nowhere. Design principles is non-normative and stays short.

Accommodations for released contracts live under Existing tools. A requirement elsewhere states the baseline and carries no brownfield qualifier; what a released path may keep is a row or clause in that section, not a condition in the requirement. D6 and D7 may describe the fields that declare retained behavior, and a requirement may point to the accommodation that applies; the permission to retain and its conditions are defined only in Existing tools.

A cross-reference names in words what the referenced rule requires, as far as the referring sentence needs it, and the identifier follows the words, so the sentence still says what applies with the identifier removed. The words carry no normative keyword and add no condition; the identifier stays the address of the rule. When a table defines whether a field is present, another rule refers to that condition instead of imposing it again and states only the behavior it adds.

Examples are independent fragments unless the text connects them, and an excerpt says that it is one.

A term in Terms names exactly the condition it replaced. When a phrase becomes a term or a definition changes, the old and new conditions are equivalent in both directions, and every use of the term keeps its meaning with the definition expanded in place. A change to a D7 field condition is rechecked against every term that reads that field.

Requirement and clause identifiers are scoped to a version of this document: after inserting, splitting, or removing a clause, later clauses are relettered in reading order and every internal reference still names its intended rule; an external citation names the version.

A readability change keeps every requirement and clause at its identifier and defining place, keeps each field, flag, and `kind` name at the table row that defines it, and keeps tables as the place a reader and an agent look an entry up; an insertion, split, removal, or move of a requirement or clause is its own change under the identifier policy above.

## Change workflow

1. Classify the change as editorial or contractual. For a contractual change, the maintainers' notes record the caller problem and the P1-P6 decision.
2. Make the smallest change that resolves the caller-facing problem.
3. Read the affected stage in full, every requirement it references, and every passage that references a changed rule; the words before an identifier must still match the rule.
4. Recheck terminology, examples, data flow, brownfield impact, and compatibility.
5. For a material contract change, review one stable draft independently and deduplicate the findings before editing again.
6. Run the checks below and review the rendered document. Before changing the version, compare the contract with the previous release against the `0.1.x` promise in Conformance and record the decision.

## Verification

Run these checks from the `haz-skills` repository root:

- `uv run --no-project python cli-design/scripts/check-standard.py cli-design/references/cli-design-standard.md cli-design/references/cli-design-standard-maintenance.md` parses every fenced `json` block, reads requirement IDs from `### ID:` headings and verifies they are unique and in stage order, reads clause markers (`**R3c:**` at the start of a paragraph) and verifies they belong to the enclosing requirement and run without gaps, rejects a reference to a requirement or clause ID that no checked file defines (so this guide's references are resolved against the standard), verifies that every `"standard"` value in examples equals the version in the header, and rejects em dashes, trailing whitespace, and indented table rows. It prints `file:line` for each problem and exits `1` when any check fails; on success it prints each file's keyword counts for the comparison above.
- Normative keyword counts (MUST, SHOULD, MAY; `MUST NOT` and `SHOULD NOT` count under their base keyword) are compared with the text before the change, and every difference is accounted for by requirement. Equal totals do not prove equal meaning.
- `git diff --check` detects whitespace errors in the change itself.
- `pandoc -f gfm -t html cli-design/references/cli-design-standard.md -o /tmp/cli-design-standard.html` renders the document for inspection.

The script checks document invariants only. Conformance of a tool against the standard is not automated.
