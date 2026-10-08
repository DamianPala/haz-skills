---
name: explain
description: "Use when a person wants to understand how something works: a module, an app, an algorithm, a pipeline, a knowledge base, a process, a set of documents, including things an agent built for them. Triggers: 'explain how X works', 'how does this work', 'walk me through', 'help me understand', '/explain'. Not for debugging a failure, writing docs or a README, code review, change summaries or one-line factual questions."
version: 0.7.0
---

# Explain

Before anything, note the revision of the material (commit hash or date, and whether tracked files are modified). Explain only what you opened or ran; run only read-only commands on the material.

## Pick the rung

- **Text**: Markdown in the chat reply. Pick it when the user asks for it ("in the terminal", "as text", "briefly", "no page"), when `visual-explainer` is not installed, or when the thing has few parts worth drawing. Then follow `references/text.md`.
- **Page**: an HTML page built with the `visual-explainer` skill. Pick it when that skill is installed and the thing has several parts and relationships worth drawing; the default for systems, pipelines, knowledge bases and processes. Then follow `references/page.md`.

Either rung can cover a whole project; the rung changes the form, not the scope. State the choice in the first line of the reply and go. Ask only when the two rungs would produce different explanations and the request does not settle it.

## The four things every rung carries

1. **One real instance, end to end.** Pick the smallest real thing that moves through the system (a request, a record, a question, a file) and follow it from its real input to its real output, through every file or store it passes, the ones a maintainer sees included. At every step show the content that matters there (the sentence, the record, the value), not an id or a hash; a step that carries only an id shows the id and what it resolves to; `path:line` under each step. End with the one branch it did not take, on a second real instance (a rejected input, an unmatched question, a failed check); when no such instance exists in the material, take the branch from the code and say it was not run.
2. **Who does each step**: `code`, `agent` or `human`, on every step of any pipeline, flow or map.
3. **One sentence per check**: wherever a check, test or validator is named, what a pass leaves unchecked; a tool with many checks gets one sentence per group of checks.
4. **Scope line** at the end: the revision stamp, and the files and commands a reader would expect you to have used and you did not.
