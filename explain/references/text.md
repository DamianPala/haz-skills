# Text rung

## Form

Markdown as a chat client renders it (Claude Code, Codex): headings, bold, lists, fenced blocks, tables narrow enough for a terminal; a text map in a fenced block instead of figures; no Mermaid, no HTML, no images.

Write it to `docs/explain/<topic>.md` (or the path the user gives) only when the user asks for a file or the reply would run past a few screens; the file is then the whole deliverable, and the reply keeps the answer, the scope line and the path.

## Order

1. The answer: what it is, who uses it, what goes in and what comes out, in one or two sentences.
2. The text map: one node per line, `name · what it is · performer`, edges with `->`. A whole project gets as many nodes as a reader meets on the way through it, grouped by stage; a single function gets its steps.
3. The instance (item 1) as numbered steps or a table.
4. The rules and who enforces them, with the sentence per check (item 3).
5. The scope line (item 4).

## Sentences

Write the way a maintenance manual is written: one idea per sentence, about twenty words, active voice with the acting thing as subject, present tense for behaviour, one term for one thing everywhere, numbers as digits with a unit, no filler and no hedging where an anchor does the job. At most one analogy, with the sentence where it stops being true.
