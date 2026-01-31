# Focus Questions - TG Digest

## Available Focus Areas

Prezentuj użytkownikowi do wyboru. Może wybrać kilka lub zdefiniować własny.

---

### 1. 🎯 Główne tematy i wątki

**Co wyciągnąć:**
- Najczęściej poruszane tematy (grupuj podobne posty)
- Główne narracje i wątki przewodnie
- Ile postów dotyczy każdego tematu
- Jak tematy ewoluowały w czasie

**Format output:**
```markdown
### 🎯 Główne tematy i wątki

1. **[Temat]** (X postów)
   - [Krótki opis o czym]
   - Kluczowe punkty: ...

2. **[Temat]** (X postów)
   ...
```

---

### 2. 🔗 Kluczowe linki i zasoby

**Co wyciągnąć:**
- Wszystkie udostępnione linki
- Artykuły, narzędzia, repozytoria
- Filmy, podcasty
- Kategoryzuj po typie

**Format output:**
```markdown
### 🔗 Kluczowe linki i zasoby

#### Artykuły
| Tytuł | URL | Data | Kontekst |
|-------|-----|------|----------|

#### Narzędzia
| Nazwa | URL | Opis |
|-------|-----|------|

#### Inne
...
```

---

### 3. 📰 Najważniejsze newsy/wydarzenia

**Co wyciągnąć:**
- Znaczące wydarzenia branżowe
- Breaking news
- Ważne ogłoszenia
- Chronologicznie

**Format output:**
```markdown
### 📰 Najważniejsze wydarzenia

| Data | Wydarzenie | Kontekst |
|------|------------|----------|
| 2025-01-15 | [Co się stało] | [Dlaczego ważne] |
```

---

### 4. 💡 Insights i wnioski autora

**Co wyciągnąć:**
- Opinie i analizy autora kanału
- Predykcje i prognozy
- Porady i rekomendacje
- Lessons learned

**Format output:**
```markdown
### 💡 Insights autora

- **[Temat]**: "[cytat lub parafraza]"
  - Kontekst: ...

- **[Temat]**: ...
```

---

### 5. ⚠️ Kontrowersje i drama

**Co wyciągnąć:**
- Konflikty i spory
- Krytyka projektów/osób
- Ostrzeżenia
- Scamy i red flags

**Format output:**
```markdown
### ⚠️ Kontrowersje i drama

#### [Temat kontrowersji]
- **Co:** [opis]
- **Strony:** [kto vs kto]
- **Status:** [rozwiązane/ongoing]
- **Źródło:** [link do posta]
```

---

### 6. 📅 Timeline wydarzeń

**Co wyciągnąć:**
- Chronologiczna lista wszystkich znaczących wydarzeń
- Daty, opisy, wpływ
- Grupuj po tygodniach/miesiącach jeśli długi okres

**Format output:**
```markdown
### 📅 Timeline

#### Tydzień 1 (1-7 Jan)
- **01-02**: [wydarzenie]
- **01-05**: [wydarzenie]

#### Tydzień 2 (8-14 Jan)
...
```

---

### 7. 🛠️ Narzędzia i produkty

**Co wyciągnąć:**
- Wspomniane narzędzia/produkty
- Nowe launche
- Rekomendacje
- Krytyka/problemy

**Format output:**
```markdown
### 🛠️ Narzędzia i produkty

| Nazwa | Typ | Sentiment | Notatki |
|-------|-----|-----------|---------|
| [Tool] | [SaaS/OSS/...] | 👍/👎/😐 | [co autor mówi] |
```

---

### 8. 💰 Finansowe (ceny, projekty, inwestycje)

**Co wyciągnąć:**
- Wspomniane projekty/tokeny
- Analizy cenowe
- Sygnały inwestycyjne
- Risk assessments

**Format output:**
```markdown
### 💰 Finansowe

#### Wspomniane projekty
| Projekt | Ticker | Sentiment | Kontekst |
|---------|--------|-----------|----------|

#### Analizy/Sygnały
- **[Data]**: [co autor mówi o rynku/projekcie]
```

---

### 9. 🎓 Edukacyjne (tutoriale, explainery)

**Co wyciągnąć:**
- Tutoriale i how-to
- Wyjaśnienia konceptów
- Kursy/materiały edukacyjne
- Tips & tricks

**Format output:**
```markdown
### 🎓 Materiały edukacyjne

#### Tutoriale
1. **[Tytuł/Temat]** - [krótki opis, link jeśli jest]

#### Explainery
1. **[Koncept]** - [o czym, dla kogo]

#### Tips
- [tip 1]
- [tip 2]
```

---

## Custom Focus

Jeśli user wybiera "Custom", zapytaj:

> Opisz na czym chcesz się skupić w tym digestcie.
> Przykłady: "szukam wszystkich wzmianek o AI agentach",
> "interesują mnie tylko posty z linkami do GitHub",
> "chcę wyciągnąć wszystkie krytyczne opinie o projektach"

Następnie dostosuj analizę do custom opisu.

---

## Combining Focus Areas

Jeśli user wybiera kilka focus areas:
1. Generuj sekcję dla każdego wybranego fokusu
2. Zachowaj kolejność jak w wyborze usera
3. Na końcu dodaj sekcję "Statystyki" ze summary liczbowym

---

## Search Patterns for Large Exports (>2000 messages)

When using subagents with grep/jq, use these patterns per focus area:

### Wallets / Apps
```bash
grep -i -E "(wallet|portfel|metamask|phantom|backpack|chrome|extension|app|download|install)"
```
**Exclude if irrelevant:** `grep -v -i -E "(validator|node|server)"`

### Trading / DEX / Exchange
```bash
grep -i -E "(dex|swap|trade|trading|exchange|buy|sell|price|listing|cex|perp|spot|limit.order|amm|liquidity)"
```

### Tokens / Memecoins
```bash
grep -i -E "(token|coin|meme|mint|airdrop|drop|launch|ticker|\$[A-Z])"
```

### DeFi / Staking / Bridge
```bash
grep -i -E "(defi|stake|staking|pool|yield|farm|apy|apr|bridge|wrap|liquid)"
```

### Links extraction
```bash
jq -r '[.messages[] | select(.urls) | .urls[]] | unique | .[]' export.json
jq -r '.messages[] | select(.urls) | select(.text | length > 0) | "\(.text)\n---URLS: \(.urls | join(\", \"))"' export.json
```

### Beginners / How-to
```bash
grep -i -E "(how to|jak|gdzie|where|tutorial|guide|start|begin|nowy|new user|beginner)"
```

### Exclude common noise (validators, nodes)
```bash
grep -v -i -E "(validator|walidator|node|nod|vps|server|serwer|epoch|slot|credits|delinquent|delegation\.mainnet)"
```

---

## Subagent Spawning Guide

For exports >2000 messages, spawn **parallel Task agents** (subagent_type=general-purpose).

**Recommended agent split:**

| Agent | Focus | Key patterns |
|-------|-------|--------------|
| 1 | Wallets & Apps | wallet, app, chrome, extension, download |
| 2 | Trading & DEX | dex, swap, trade, exchange, price, listing |
| 3 | Tokens & Memes | token, coin, mint, airdrop, ticker |
| 4 | DeFi & Staking | stake, pool, yield, bridge, apy |
| 5 | Custom (from user focus) | user-defined keywords |

**Agent prompt template:**
```
Przeanalizuj plik [PATH] pod kątem [TOPIC].

Szukaj:
- [specific items]
- Linków i nazw
- Konkretnych instrukcji/tutoriali

Użyj grep/jq. Zwróć:
- Nazwy z opisami
- Linki (URL)
- Kluczowe cytaty
- Status (live/beta/dev)

Pomiń: [irrelevant topics like validators if not needed]
```

**After agents return:** Combine all findings, deduplicate, format as final digest.
