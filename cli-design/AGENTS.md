# cli-design

Skill wrapping the CLI Design Standard for Humans and Agents (`references/`). Work on the standard is tracked in `build/draft-7-plan.md` (dev notes, gitignored); closed cycles live in `build/archive/`.

## Rules

- **Review:** when working in Claude Code, reviews go to Codex via `acpc run reviewer --effort high` (gpt-5.6-sol), unless the user says otherwise.
- **Spec edits:** discuss first, edit second, and only with evidence (a running implementation, a black-box test, a calling agent, or an audit of an existing CLI). Every edit maps to an item in the current plan and gets a line in the current plan's changelog file (`build/draft-7-changelog.md`).
- **Plan format:** each proposed spec change is its own numbered item (`3.A`, `3.B`, ...) written for a human reader, in this order: **Jest** (current spec text, quoted where it matters), **Zmieniamy na** (the exact change, or "bez zmian"), **Przykład** (before/after snippet or a short table when it makes the change concrete), **Dlaczego** (reasoning, who raised it), **Odrzucone** (alternatives, when any), **Kto** (author decision or user gate). A verdict table alone is not enough; the user reads the plan, not the transcript.
- **Checks before commit:** the verification list in `references/cli-design-standard-maintenance.md`.
