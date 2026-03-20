---
name: good-research
description: "Run web research with live web search via multiple backends. Two modes: default (thorough) and quick (focused). Triggers: 'research [topic]', 'zbadaj [temat]', 'zrób research [temat]', 'odpal research [temat]', 'research codexem [temat]', 'codex research [topic]', 'zbadaj codexem [temat]', 'research sonetem [temat]', 'sonnet research [topic]', 'research opusem [temat]', 'opus research [topic]', 'research haiku [temat]', 'quick research [topic]', 'szybki research [temat]', 'szybko zbadaj [temat]'. DO NOT TRIGGER for simple questions without research intent."
---

# Research

Dispatch a web research task to a chosen backend, then present findings.

## Backends

| Backend | Trigger keywords | Execution method |
|---------|-----------------|------------------|
| **self** (default) | no backend specified | Agent tool, inherits current model |
| **codex** | "codexem", "codex" | `codex exec` via Bash |
| **sonnet** | "sonetem", "sonnet" | Agent tool, model: sonnet |
| **haiku** | "haiku" | Agent tool, model: haiku |
| **opus** | "opusem", "opus" | Agent tool, model: opus |

Default to **self** when no backend is mentioned.

## Modes

| Mode | Trigger keywords | Timeout (codex) | Searches per angle |
|------|-----------------|-----------------|-------------------|
| **default** | "research", "zbadaj" | 30 min | 6-10 |
| **quick** | "quick", "szybki", "szybko", "fast", "krótki" | 10 min | 3-5 |

Default unless the user explicitly asks for quick.

## Workflow

1. Extract the research topic from the user's message
2. **Scope Check** — decide whether to clarify before researching

   ### When to skip (just go)
   - Topic has explicit research questions ("compare X vs Y", "what are tradeoffs of")
   - Topic includes constraints (timeframe, audience, scope, exclusions)
   - Conversation context already provides scope (prior messages narrow the topic)
   - User flags: "skip questions" / "nie pytaj", "no clarification" / "bez dopytywania"
   - **Quick mode requested** — always skip when user triggers quick/szybki/fast. Speed over precision, no quiz

   ### When to ask
   - Topic is short/vague (1-5 words, e.g. "AI agents") AND no conversation context narrows it
   - Multiple plausible research directions exist that would produce very different reports
   - User flags: "let me clarify" / "doprecyzuję", "help me scope" / "pomóż sformułować"

   **Rule**: skip by default. Only ask when the topic is genuinely ambiguous and you cannot resolve it from conversation context or a quick discovery read.

   ### How to ask

   **Scale questions to vagueness.** Assess how underspecified the topic is and adjust:

   | Vagueness | Example | Questions |
   |-----------|---------|-----------|
   | Slightly vague (direction clear, details missing) | "research new Claude models" | 1 question |
   | Moderately vague (area known, direction unclear) | "research remote work tools" | 2-3 questions |
   | Very vague (just a domain) | "research AI" | 3-5 questions |

   Rules:
   - Open-ended questions. Let the user describe the direction in their own words
   - Focus on: intent (what do you want to learn?), goal (what will you do with this?), scope (what's in/out?)
   - Keep it concise — the user asked for research, not a quiz
   - Do NOT ask about things you can infer from conversation context, user profile, or a quick discovery read

   ### Verify before proceeding

   After user responds, check: do I now have enough to produce a focused report?
   - **Yes** → restate scope in 1 sentence, proceed to research
   - **No** → ask 1-2 follow-up questions on the remaining gaps. Max 1 follow-up round (do not loop)

3. Detect backend from trigger keywords (self if none specified)
4. Detect mode (default or quick)
5. Detect topic language (PL/EN/other) for the output language instruction
6. Inject variables into the appropriate research prompt: `{TOPIC}`, `{LANG}`, `{YEAR}`, `{PREV_YEAR}`
7. Dispatch to backend (see below)
8. Inform the user that research is running (mention backend + mode)
9. On completion, present results: brief summary first, then full report

## Backend: Agent (self, sonnet, haiku, opus)

Use the Agent tool:

```
name: "research"
subagent_type: "general-purpose"
model: <omit for self | "sonnet" | "haiku" | "opus">
run_in_background: true
prompt: <research prompt with {TOPIC}, {LANG}, {YEAR}, {PREV_YEAR} injected>
```

The agent has access to WebSearch and WebFetch tools for web research.

After the agent completes, present its result to the user.

## Backend: Codex

Pass the prompt via stdin heredoc to avoid escaping issues.

### Default mode

```bash
OUTPUT="/tmp/codex-research-$(date +%s).md"

codex exec \
  --skip-git-repo-check \
  --ephemeral \
  --full-auto \
  -s read-only \
  -c 'model_reasoning_effort="xhigh"' \
  -o "$OUTPUT" \
  - <<'RESEARCH_PROMPT'
<INSERT RESEARCH PROMPT HERE>
RESEARCH_PROMPT
```

Run with Bash tool: `run_in_background: true`, `timeout: 900000`.

### Quick mode

```bash
OUTPUT="/tmp/codex-research-$(date +%s).md"

codex exec \
  --skip-git-repo-check \
  --ephemeral \
  --full-auto \
  -s read-only \
  -c 'model_reasoning_effort="xhigh"' \
  -o "$OUTPUT" \
  - <<'RESEARCH_PROMPT'
<INSERT QUICK RESEARCH PROMPT HERE>
RESEARCH_PROMPT
```

Run with Bash tool: `run_in_background: true`, `timeout: 600000`.

### Codex notes

- The `-` argument reads prompt from stdin. `<<'RESEARCH_PROMPT'` prevents shell expansion
- After completion, read `$OUTPUT` with Read tool, present to user, then `trash-put "$OUTPUT"`

## Research Prompts

Same prompts for all backends. Inject variables before use:
- `{TOPIC}` - user's research topic
- `{LANG}` - detected output language (e.g. "Polish", "English")
- `{YEAR}` - current year (e.g. "2026")
- `{PREV_YEAR}` - previous year (e.g. "2025")

### Default Research Prompt

```
You are a research analyst with live web search. Investigate the topic below thoroughly.

## Protocol

1. **Scope**: Identify 3-5 distinct angles (current state, key players, technical approaches, tradeoffs, community opinion). If topic is broad, prioritize the 2-3 most actionable angles and go deep rather than covering everything shallowly.

2. **Search**: For each angle, run 6-10 web searches with varied queries. Depth over breadth.
   - Mix expert and layman terminology
   - Include specific names: products, companies, benchmarks, conferences, researchers
   - Include recent timeframes ("{PREV_YEAR}", "{YEAR}", "latest")
   - Search for comparisons, alternatives, known problems
   - Prioritize primary sources: official docs, release notes, papers, author posts
   - Search aggressively. More searches = better coverage. Do not stop at first results
   - When a search reveals a key player or benchmark, do follow-up searches on that specific name

3. **Diversify perspectives**: Search from multiple angles for the same question. Look for industry reports, academic benchmarks, vendor comparisons, independent developer blogs, Reddit/HN discussions, and case studies. Different source types reveal different truths.

4. **Cross-reference**: Verify claims across multiple sources. Flag single-source claims as [single-source]. Note disagreements. Major claims require 2+ independent sources.

5. **Synthesize**: Combine into the output format below. Prioritize actionable over background, recent over outdated (last 12 months), facts over opinions (label opinions), specifics over generalities.

6. **Self-critique**: Before writing the final output, review your findings. Ask: Are there obvious gaps? Did I miss a major player or perspective? Are any claims under-sourced? If yes, do targeted follow-up searches to fill the gaps.

## Output Format

Write in {LANG}. Use inline citations [N] throughout the text, referencing the numbered Sources list.

### TL;DR
2-3 sentences. The most important takeaway.

### Key Findings
Organize by angle. For each:
- **What**: 1-3 sentences with inline citations [N]
- **Evidence**: supporting sources by number
- **Confidence**: high (3+ reliable sources agree) / medium (2 sources or mixed signals) / low (single source or speculative)

Clearly label what is source-grounded fact vs your own synthesis. Use "Based on [N], ..." for facts and "Synthesizing across sources, ..." for inferences.

### Perspectives
Where experts disagree, present each position fairly with reasoning and citations. Do not pick a winner unless evidence is overwhelming.

### Practical Implications
What this means for someone acting on it. Concrete next steps if applicable.

### Sources
Numbered list: [N] [Title](URL) - one-line description.
Mark primary (official docs, original research) vs secondary (blogs, summaries).
Aim for 10+ distinct sources. If fewer exist, note the topic's limited coverage.

### Gaps
What could not be determined or needs hands-on testing.

## Rules
- No filler, no hedging. Be direct
- If topic is too broad, narrow to the most actionable subset and note exclusions. Depth always beats breadth
- Distinguish "widely adopted" vs "emerging" vs "experimental"
- Include version numbers, dates, concrete figures where available
- Every factual claim must have an inline citation [N]. No uncited claims
- Never fabricate sources. If you cannot find information, say so

Topic: {TOPIC}
```

### Quick Research Prompt

```
You are a research analyst with live web search. Investigate the topic below with a focused scope.

## Protocol

1. **Scope**: Identify the 2-3 most important angles. Skip background, go straight to the core question.

2. **Search**: For each angle, run 3-5 web searches with targeted queries.
   - Prioritize primary sources: official docs, release notes, author posts
   - Include recent timeframes ("{PREV_YEAR}", "{YEAR}", "latest")
   - Do follow-up searches when a result reveals something important

3. **Cross-reference**: Verify key claims across 2+ sources. Flag single-source claims as [single-source].

4. **Synthesize**: Combine into the output format below. Prioritize actionable over background, recent over outdated.

## Output Format

Write in {LANG}. Use inline citations [N] throughout the text.

### TL;DR
2-3 sentences. The most important takeaway.

### Key Findings
Organize by angle. For each:
- **What**: 1-3 sentences with inline citations [N]
- **Confidence**: high (3+ sources) / medium (2 sources) / low (single source)

Label facts vs synthesis: "Based on [N], ..." for facts, "Synthesizing across sources, ..." for inferences.

### Sources
Numbered list: [N] [Title](URL) - one-line description.
Aim for 5+ distinct sources.

### Gaps
What was out of scope or needs a full research pass.

## Rules
- No filler, no hedging. Be direct
- Depth over breadth, even in quick mode
- Include version numbers, dates, concrete figures where available
- Every factual claim must have an inline citation [N]
- Never fabricate sources. If you cannot find information, say so

Topic: {TOPIC}
```

## Error Handling

| Symptom | Backend | Action |
|---------|---------|--------|
| Timeout | codex | Inform user, suggest narrowing the topic |
| Auth error in stderr | codex | Show stderr, suggest `codex login` |
| Output file missing/empty | codex | Check `which codex`, show stderr |
| `codex` not found | codex | Tell user: `npm i -g @openai/codex` |
| Agent returns error | agent | Show error, suggest retrying with different backend |
| Agent timeout (no output) | agent | Inform user, suggest quick mode or narrower topic |
