---
name: tg-digest
description: "Export and summarize Telegram channels for a given time period. AI-driven flow asks for channel, date range, and focus areas, then generates a structured digest. Triggers: $tg-digest, telegram summary, podsumuj kanał TG, tg digest."
---

# TG Digest Skill

## Quick Start

1. Check environment: `TG_API_ID` and `TG_API_HASH` must be set
2. Ask user for **channel** (name or @handle)
3. Ask user for **time range** (e.g., "last 7 days", "last 3 months", specific dates)
4. Show focus questions from `references/focus-questions.md` - user picks or customizes
5. Execute PHASE 0 → PHASE 1 → PHASE 2 → PHASE 3

## Status Output

**Always print current phase:** `📍 PHASE X: [action]...`

---

## Requirements

- **uv** - Python package manager (https://docs.astral.sh/uv/)
- **TG_API_ID** and **TG_API_HASH** env vars

```bash
# Get credentials at: https://my.telegram.org → API development tools
export TG_API_ID="your_api_id"
export TG_API_HASH="your_api_hash"
```

First run will prompt for phone number + SMS code (session saved locally at `~/.tg-digest-session.session`).

---

## Workflow

### PHASE 0: Environment Check

```
📍 PHASE 0: Sprawdzam środowisko...
```

1. Check if `uv` is available (`which uv`), if not → show install instructions and STOP
2. Check if `TG_API_ID` and `TG_API_HASH` are set, if missing → show setup instructions and STOP
3. Check if session file exists (`~/.tg-digest-session.session`)
   - If no session → inform user they'll authenticate on first export

---

### PHASE 1: Gather Parameters

```
📍 PHASE 1: Zbieram parametry...
```

**Ask user for:**

1. **Channel** (required)
   - Accept: `@channelname`, `channelname`, or full URL `t.me/channelname`
   - Normalize to channel identifier

2. **Time range** (required)
   - Natural language: "ostatnie 7 dni", "last 3 months", "od 1 stycznia"
   - Parse to: `start_date` and `end_date` (ISO format)
   - Default end_date: today

3. **Focus areas** (show options from `references/focus-questions.md`)
   - Display available focus presets
   - User can pick multiple or define custom focus
   - Store as list of focus questions for PHASE 3

4. **Output language** (default: PL)

**Example interaction:**
```
📍 PHASE 1: Zbieram parametry

Kanał: @examplechannel
Okres: ostatnie 30 dni (2025-01-01 → 2025-01-31)
Język: PL

Wybierz fokus (można kilka, oddziel przecinkami):
1. 🎯 Główne tematy i wątki
2. 🔗 Kluczowe linki i zasoby
3. 📰 Najważniejsze newsy/wydarzenia
4. 💡 Insights i wnioski autora
5. ⚠️ Kontrowersje i drama
6. 📅 Timeline wydarzeń
7. 🛠️ Narzędzia i produkty
8. 💰 Finansowe (ceny, projekty, inwestycje)
9. 🎓 Edukacyjne (tutoriale, explainery)
C. Custom (opisz własny fokus)

Twój wybór:
```

---

### PHASE 2: Export

```
📍 PHASE 2: Eksportuję wiadomości...
```

Run the export script:

```bash
uv run ~/.agents/skills/haz-skills/tg-digest/scripts/tg_export.py \
  --channel "@channelname" \
  --start-date "2025-01-01" \
  --end-date "2025-01-31" \
  --output "./export_channelname_20250101_20250131.json"
```

Note: First `uv run` will cache telethon (~5-10s), subsequent runs are instant.

**Handle errors:**
- `SessionPasswordNeededError` → ask user for 2FA password
- `FloodWaitError` → inform user about wait time
- `ChannelPrivateError` → user doesn't have access
- First run → guide through phone auth

**Output:** JSON file with messages in working directory

**Inform user:**
```
✅ Wyeksportowano X wiadomości do: export_channelname_20250101_20250131.json
→ Przechodzę do analizy...
```

---

### PHASE 3: Generate Digest

```
📍 PHASE 3: Generuję digest...
```

#### Strategy based on export size:

| Messages | Strategy |
|----------|----------|
| < 500 | Direct analysis - read JSON, analyze inline |
| 500 - 2000 | Grep/jq extraction - search for keywords per focus area |
| > 2000 | **Parallel subagents** - spawn Task agents for each topic |

#### For large exports (>2000 messages): Use Parallel Subagents

**CRITICAL:** Do NOT try to read full JSON into context. Use Task tool with `subagent_type=general-purpose` to spawn parallel analysis agents.

**Spawn 3-5 agents in parallel**, each analyzing a specific aspect:

```
Agent 1: Wallets, portfele, apps - szukaj nazw portfeli, linków, instrukcji setup
Agent 2: Trading, DEX, exchange - szukaj platform tradingowych, par, cen
Agent 3: Tokens, memecoins - szukaj nazw tokenów, kontraktów, jak kupić
Agent 4: DeFi, staking, bridge - szukaj protokołów, APY, yield
Agent 5: [Custom based on user focus]
```

**Agent prompt template:**
```
Przeanalizuj plik [EXPORT_PATH] pod kątem [TOPIC].

Szukaj:
- [specific keywords]
- [what to extract]

Użyj grep/jq żeby przeszukać plik. Zwróć konkretne cytaty i linki.

Output: szczegółowa lista z opisami i linkami.
```

**Example jq commands agents should use:**
```bash
# Extract all unique URLs
jq -r '[.messages[] | select(.urls) | .urls[]] | unique | .[]' export.json

# Search text content
jq -r '.messages[] | select(.text | length > 0) | .text' export.json | grep -i "keyword"

# Messages with specific pattern, excluding others
jq -r '.messages[] | select(.text | length > 0) | .text' export.json | grep -i "wallet" | grep -v -i "validator"
```

**After all agents return:** Combine their findings into the final digest.

---

#### Semantic Search Mode (dla pytań otwartych)

Gdy user zadaje pytania semantyczne (np. "jaki jest sentiment społeczności?", "jakie są obawy?"), użyj chunk-based analysis:

**Step 1: Split export na chunki**
```bash
uv run ~/.agents/skills/haz-skills/tg-digest/scripts/tg_semantic.py split export.json --size 500 --output /tmp/chunks
```

Tworzy: `chunk_001.json`, `chunk_002.json`, ... + `manifest.json`

**Step 2: Spawn subagentów na chunki**

Przy 30 chunkach - spawn 5-6 agentów, każdy dostaje ~5-6 chunków:

```
Agent 1: chunki 1-6   (pytanie + ścieżki do chunków)
Agent 2: chunki 7-12
Agent 3: chunki 13-18
Agent 4: chunki 19-24
Agent 5: chunki 25-30
```

**Agent prompt template (semantic):**
```
Przeczytaj chunki: [CHUNK_PATHS]

Pytanie: [USER_QUESTION]

Dla każdego chunka:
1. Przeczytaj wiadomości (Read tool)
2. Znajdź fragmenty odpowiadające na pytanie
3. Wyciągnij konkretne cytaty z datami

Output: lista relevantnych cytatów z kontekstem.
```

**Step 3: Merge wyników**

Połącz odpowiedzi wszystkich agentów, usuń duplikaty, stwórz spójną odpowiedź.

**Kiedy używać semantic vs grep:**

| Pytanie | Metoda |
|---------|--------|
| "znajdź wszystkie portfele" | grep (keyword) |
| "jaki jest sentiment o projekcie" | semantic (chunki) |
| "wylistuj DEXy" | grep |
| "jakie są obawy społeczności" | semantic |
| "pokaż linki" | jq (URL extraction) |

---

#### Analysis Structure:

```markdown
# 📊 TG Digest: [CHANNEL_NAME]

**Okres:** [START_DATE] → [END_DATE]
**Wiadomości:** [COUNT]
**Wygenerowano:** [TODAY]

---

## 📋 Podsumowanie

[2-3 zdania overview - co się działo w tym okresie]

---

## [FOCUS SECTIONS - based on user selection]

### 🎯 Główne tematy i wątki
- **[Temat 1]**: [opis, ile postów]
- **[Temat 2]**: [opis, ile postów]
...

### 🔗 Kluczowe linki i zasoby
| Zasób | Opis | Data |
|-------|------|------|
| [nazwa](url) | opis | data |

### 📰 Najważniejsze wydarzenia
1. **[DATA]**: [wydarzenie]
2. **[DATA]**: [wydarzenie]

[...inne sekcje wg wybranego fokusu...]

---

## 📈 Statystyki

- Łączna liczba wiadomości: X
- Średnio dziennie: X
- Posty z linkami: X%
- Posty z mediami: X%

---

*Digest wygenerowany przez tg-digest skill*
```

**Save as:** `[CHANNEL]_digest_[START]_[END].md`

---

## Focus Questions Reference

See `references/focus-questions.md` for full list of focus areas and what to extract for each.

---

## Error Handling

| Error | Action |
|-------|--------|
| `uv` not found | Show install link: https://docs.astral.sh/uv/, STOP |
| Missing env vars | Show setup instructions, STOP |
| No session | Guide through first-time auth |
| Channel not found | Ask user to verify channel name |
| No access | Inform user they need to join channel first |
| FloodWait | Show wait time, optionally retry |
| Empty export | Inform user, check date range |

---

## Files

| File | Purpose |
|------|---------|
| `scripts/tg_export.py` | Telethon export script |
| `references/focus-questions.md` | Focus areas and extraction rules |
