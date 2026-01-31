---
name: technical-blog
description: Write human-sounding technical blog tutorials for Linux tools: concise, accurate, and practical.
---

# Technical Blog (Linux)

## Overview
Write practical technical tutorials with clear steps and human tone.
Balance brevity with clarity: skip filler words, but include context that helps readers understand *why*, not just *how*.

## When to use
- Linux tool tutorials, setup guides, troubleshooting notes
- Any post where steps + verification matter

## Inputs to collect (ask if missing)
- Tool/topic + goal
- Distro + version, shell, privilege (sudo?)
- Constraints (avoid snap, offline, etc.)
- Existing config/state or errors (if any)

## House style (match linux-guides)
- Direct, pragmatic, no marketing.
- Context before commands — reader should know "what" before "how".
- Short intro, then sections with headings.
- Commands in fenced bash blocks.
- Add "Verification" after meaningful steps (unless another section covers it).
- "Notes" and "References" at end.

## Document flow
Readers should understand *what* and *why* before *how*:

1. **Context first** — explain the tool/concept before diving into commands
2. **Show the destination** — describe the end result or directory structure early
3. **Then the steps** — now the reader knows where they're headed
4. **Verify at milestones** — not just at the end

Avoid: jumping straight into `apt install` without explaining what you're installing or why.

## Structure template (use or adapt)
1) Title: "Install <Tool> on <Distro>"
2) 2-4 sentence intro (what it does, why you'd want it)
3) Overview / How it works (optional, for complex topics)
   - Architecture, key concepts, or directory structure
   - What the end result will look like
4) Prerequisites / Requirements
5) Install / Step-by-step
6) Configuration (if needed)
7) Verification / Health check
8) Usage examples (if not obvious)
9) Notes / Troubleshooting
10) References with raw URLs

**Skip sections that aren't needed.** If Usage examples already verify the install works, drop the separate Verification section. Don't add empty or redundant sections just to match the template.

## Context guidelines
Add explanation when:
- A step might confuse intermediate users (not just beginners)
- There are multiple approaches and you chose one — briefly say why
- Understanding "why" helps readers adapt the solution to their setup
- A command has non-obvious flags worth mentioning

Skip explanation when:
- The step is self-evident (`mkdir`, `cd`, `git clone`)
- You already explained a similar pattern earlier in the post

## Clarity rules (from writing-clearly-and-concisely)
- Use active voice.
- Prefer concrete, specific language.
- Omit filler words, but keep explanatory context.
- Keep related words together.
- Use parallel phrasing in lists.

## Humanizer pass (after draft)
- Vary sentence length.
- Remove filler (very, really, simply, etc.).
- Add one small, natural aside if helpful.
- Never mention being an AI.

## Refinement pass (after draft)
- Remove redundancies (especially repeated verification blocks).
- Merge duplicate steps or notes across install methods.
- Tighten filler and redundancy, but preserve context that aids understanding.
- Drop sections that don't add value for this particular post.

## AI writing patterns to avoid
- Puffery: pivotal, crucial, vital, testament, enduring legacy
- Empty "-ing" phrases: ensuring reliability, showcasing features, highlighting capabilities
- Promotional adjectives: groundbreaking, seamless, robust, cutting-edge
- Overused AI vocabulary: delve, leverage, multifaceted, foster, realm, tapestry
- Formatting overuse: excessive bullets, emoji decorations, bold on every other word

Be specific, not grandiose. Say what it actually does.

## Safety + accuracy
- Warn before risky commands and suggest safer alternatives.
- Provide reversible steps or backups.
- Prefer official, universal install methods.
- Never fabricate command output; say "You should see...".
- Ask at most 3 clarifying questions when critical info is missing; otherwise list assumptions.

## Quick checklist
- [ ] Context/overview before step-by-step commands
- [ ] Steps run in order; commands are copy/pasteable
- [ ] Verification included (explicit section or via usage examples)
- [ ] Notes cover top 1-3 gotchas
- [ ] No redundant or empty sections
- [ ] Tone feels like a human blog post
