# cli-design

Skill wrapping the CLI Design Standard for Humans and Agents (`references/`). Work on the standard is tracked in `build/draft-4-plan.md` (dev notes, gitignored).

## Rules

- **Review:** when working in Claude Code, reviews go to Codex via `acpc run reviewer --effort high` (gpt-5.6-sol), unless the user says otherwise.
- **Spec edits:** discuss first, edit second. Every edit maps to an item in the current plan and gets a line in `build/draft-4-changelog.md`.
- **Checks before commit:** the verification list in `references/cli-design-standard-maintenance.md`.
