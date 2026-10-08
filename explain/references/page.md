# Page rung: three phases, in this order

**Phase 1.** Build the page with the `visual-explainer` skill exactly as that skill would on its own: its `project-recap` flow, style guide, figures and fact-check. Skip its sections about recent activity, hot spots and next steps: this is a "how does it work" request, not a recap for a returning reader. Do not plan phase 2 yet.

**Phase 2.** Add to the finished page. Remove nothing, reorder nothing, rewrite no existing sentence or figure.

- Insert the instance (item 1) as its own section right after the section that explains the unit the instance is (the claim, the request, the record); if no such section exists, before the sources.
- Add the labels (item 2) to each step's sublabel in existing figures and touch nothing else in them.
- Append the one sentence per check (item 3) where each check is named.
- Put the scope line (item 4) under the sources; if a verification panel sits at the top, move it down above the scope line, the only move allowed.

**Phase 3.** Hand the finished page to a fresh agent that did not write it (a cheap model is enough), read-only on the material, allowed to edit the page only. It checks every `path:line` anchor and every sentence that states a limit, a rule, a count, a date or a result, each against its source; for a rule it also reads the lines next to the source, because the usual miss is a true sentence with the condition or the ordering that stands beside it dropped. Verdicts: match, partial, mismatch. It rewrites a partial to what the source says (restoring a condition the source states beside the claim is a repair, not an addition), fixes a wrong number or anchor, removes what it cannot fix, and never softens a claim into a hedge or a `code`/`agent`/`human` label into a vaguer word. It judges nothing else and adds no new claims. It updates the verification panel's counts and change list and returns a table of items with verdict, evidence and action, flagging any removal that leaves one of the four things missing.
