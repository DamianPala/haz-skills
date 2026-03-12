---
name: good-research
description: "Run web research with live web search via multiple backends. Two modes: default (thorough) and quick (focused). Supports: current model, Codex, Sonnet, Haiku, Opus. Triggers: $good-research, 'research [topic]', 'zbadaj [temat]', 'zrób research [temat]', 'odpal research [temat]', 'research codexem [temat]', 'codex research [topic]', 'zbadaj codexem [temat]', 'research sonetem [temat]', 'sonnet research [topic]', 'research opusem [temat]', 'opus research [topic]', 'research haiku [temat]', 'quick research [topic]', 'szybki research [temat]', 'szybko zbadaj [temat]'. DO NOT TRIGGER for simple questions without research intent."
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
2. Detect backend from trigger keywords (self if none specified)
3. Detect mode (default or quick)
4. Detect topic language (PL/EN/other) for the output language instruction
5. Inject variables into the appropriate research prompt: `{TOPIC}`, `{LANG}`, `{YEAR}`, `{PREV_YEAR}`
6. Dispatch to backend (see below)
7. Inform the user that research is running (mention backend + mode)
8. On completion, present results: brief summary first, then full report

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
