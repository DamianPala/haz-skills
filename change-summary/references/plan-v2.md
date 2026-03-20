# change-summary v2: net-diff pipeline

## Założenia

### 1. Net diff jest source of truth

Używamy `git diff base..head` (z rozwinięciem submodułów). To pokazuje CO FAKTYCZNIE się zmieniło między dwoma punktami. Nie interesuje nas droga (per-commit journey), interesuje nas wynik (net delta).

Uzasadnienie: każdy konsument (merge-message, pr-create, changelog, release-create) potrzebuje net delta. Żaden nie potrzebuje per-commit breakdown. Potwierdzone researchem: PR-Agent, CodeRabbit, Copilot, GitLab Duo, wszystkie production tools używają net diff.

### 2. Nie ufamy commit messages

Commit messages mogą być: "wip", "stuff", "fix", ".", albo po prostu błędne. Nie są source of truth. Używamy ich jako **hints** (podpowiedzi) z niskim zaufaniem, nie jako fakty.

Uzasadnienie: PR-Agent explicite demotuje commit messages jako "partial, simplistic, non-informative or out of date" (issue #179). Nasz E2E test potwierdził: commit message mówi "[FIX] Fix calibration" ale w diffie nie ma zmian kalibracyjnych.

### 3. Diff czytamy sami, interpretujemy sami

LLM czyta surowy diff i sam identyfikuje logiczne zmiany z kodu. Nie polegamy na żadnych zewnętrznych opisach. To jest nasza kluczowa wartość: interpretacja zmian na podstawie faktycznego kodu, nie metadanych.

Future enhancement: context enrichment (issue tracker, PR descriptions, class summaries) jak CodeRabbit. Na razie poza scope.

### 4. Chunking po plikach, sortowanie po kategorii i alfabetycznie

Net diff dzielimy na chunki po granicach plików (`diff --git`). Kolejność:

1. **source** (alfabetycznie wewnątrz kategorii)
2. **test**
3. **config/ci**
4. **docs/chore**

Greedy packing z budżetem tokenowym (100k tokens per chunk). Jeśli jeden plik przekracza budżet, dostaje własny chunk.

Uzasadnienie: PR-Agent pattern zaadaptowany. Alfabetyczne sortowanie wewnątrz kategorii trzyma powiązane pliki (ten sam katalog) blisko siebie. Brak module detection (language-dependent, zawodne, żaden production tool tego nie robi).

### 5. Commit log jako sidebar, nie struktura

`git log --oneline base..head` dołączamy do każdego chunku jako lekki kontekst. Nie jest to struktura diffa, jest to sekcja "hints". LLM może z niego wyciągnąć intent (dlaczego coś się zmieniło), ale nie musi mu ufać.

### 6. Zero collapsingu, cross-chunk dedup zostaje

Net diff naturalnie daje net delta. Jeśli feat został dodany i potem fixnięty na tym samym branchu, net diff pokazuje tylko finalny poprawny stan. Nie ma co kolapsować. Eliminujemy cały net delta collapsing z final eval.

Cross-chunk dedup **zostaje** w Step 5 (Merge): jeśli ten sam plik wyląduje na granicy chunków, dwa interpretery mogą opisać tę samą zmianę. Merge dedupuje. To nie jest collapsing (łączenie różnych zmian), to jest dedup (usuwanie duplikatów).

### 7. Lightweight metadata z classify.py — tylko pewne fakty

Dla każdego pliku w diffie generujemy deterministyczne metadane (Python, zero tokenów LLM):
- path, status (A/M/D), +lines, -lines
- category (source/test/config/docs/generated) — oparte na ścieżce pliku, wiarygodne

**NIE dajemy** `likely_type` (feat/fix/refactor). Te heurystyki są zbyt grube i mogą bias'ować LLM:
- `likely_fix` dla małych zmian → LLM może nie sprawdzić czy to nie feat
- `likely_feat` dla nowych plików → może to refaktor (extract to new file)
- `extract_likely_from_message()` bierze typ z commit message, a my im nie ufamy

LLM ma sam zdecydować o typie zmiany z kodu. Nagłówki mają wyłącznie fakty obiektywne.

### 8. Submoduły rozwijamy do net diff

Dla submodułów robimy `git diff old_hash..new_hash` wewnątrz submodule directory. Prefixujemy ścieżki plików. Traktujemy jak zwykłe pliki w diffie. Konfiguracja (summarize/ignore/expand) z AGENTS.md per-repo zostaje.

### 9. Output format się nie zmienia, semantyka `commits` się poszerza

YAML output (`changes.yaml`) ma ten sam schemat co v1. Konsumenci (merge-message, pr-create, release-create) nie wymagają zmian.

Pole `commits` zostaje ale zmienia semantykę:
- **v1:** hash commitu który wprowadził zmianę (1:1 mapping commit→change)
- **v2:** lista commitów które dotknęły plików danej zmiany (N:1 mapping)

Mechanizm: `git log --name-only --pretty=format:"%h" base..head` daje mapping commit→pliki. Python buduje odwrotną mapę plik→commity. Gdy LLM przypisuje pliki do zmiany, commits wypełniane z tej mapy.

To jest mniej precyzyjne niż v1 (nie wiesz "który commit wprowadził tę zmianę"), ale wystarczające dla traceability (wiesz "które commity ruszały te pliki").

### 10. Maksymalnie deterministyczny pipeline

LLM robi tylko to, czego nie da się zrobić kodem: interpretację kodu (Step 2) i semantyczną weryfikację (Step 4). Reszta to Python.

```
1. Collect       (Python)  → diff-N.txt + prompts + file→commits map
2. Interpret     (acpc)    → raw YAML per chunk (type, description, detail, files)
3. Post-process  (Python)  → schema fix, category fill, commits fill, cross-check
4. Verify        (acpc)    → semantic check only (osobny agent, świeży kontekst)
5. Merge         (Python)  → dedup, sort, consistency, bump → changes.yaml
6. Deliver
```

**Co robi Python (deterministyczne):**

| Co | Gdzie | Jak |
|---|---|---|
| `category` field | Step 3 | Mapping z `type` (feat→Added, fix→Fixed, ...). LLM nie wypełnia |
| `commits` field | Step 3 | File→commits mapa z `git log --name-only`. LLM nie wypełnia |
| Schema validation | Step 3 | Required fields, types, format. validate.py |
| File coverage cross-check | Step 3 | Każdy plik z diff ma YAML coverage. crosscheck.py |
| Cross-chunk dedup | Step 5 | File overlap + description similarity. Python |
| Consistency | Step 5 | Type/category mapping, required fields. Python |
| Bump computation | Step 5 | breaking→major, feat→minor, else→patch. Python |
| Breaking flag hints | Step 1 | Deleted source files = possible breaking. Python |

**Co robi LLM (semantyczne):**

| Co | Gdzie | Dlaczego nie da się deterministycznie |
|---|---|---|
| Identyfikacja logicznych zmian | Step 2 | Wymaga rozumienia kodu |
| Opis end-user (description) | Step 2 | Wymaga abstrakcji z kodu do user language |
| Opis techniczny (detail) | Step 2 | Wymaga rozumienia mechanizmów |
| Typ zmiany (type) | Step 2 | Wymaga rozumienia intencji (feat vs fix vs refactor) |
| Brakujące zmiany | Step 4 | Diff pokazuje zmianę, YAML jej nie ma. Wymaga rozumienia kodu |
| Hallucynacje | Step 4 | YAML opisuje coś czego nie ma w diffie |
| Poprawność typów | Step 4 | Czy type pasuje do tego co diff faktycznie pokazuje |
| Poprawność opisów | Step 4 | Czy description oddaje realną zmianę w kodzie |

**Verify (Step 4) skupia się wyłącznie na semantyce.** Nie sprawdza schema, category mapping, file coverage (to już zrobił Python w Step 3). Dostaje YAML po walidacji i cross-check. Jego jedyne zadanie: czy LLM dobrze odczytał KOD.

acpc-always dla interpret i verify (confirmation bias prevention).

### 11. Reverty i usunięte-przywrócone pliki są niewidoczne

Świadoma decyzja. Net diff nie pokazuje:
- Feature dodana w commit A, usunięta w commit B → net diff = zero zmian, nie pojawia się w output
- Plik usunięty w commit 3, przywrócony w commit 7 → net diff pokazuje tylko net zmianę (jeśli jest)

To jest **pożądane zachowanie** dla net delta. Konsumenta nie interesuje że coś było i nie ma, interesuje go co jest teraz vs co było na base.

## Plan implementacji

Iteracyjny: implementacja → test na małych golden files → fix → test na dużych.

### Etap 1: Taski

Rozpisać flat listę tasków implementacyjnych. Zakres:
- Collect: net diff, file→commits map, chunking po plikach, format, commit log sidebar
- Interpret: nowe prompt rules (file-based zamiast commit-based)
- Post-process: category fill, commits fill, cross-check na file coverage
- Verify: prompt rules skupione na semantyce (bez mechanical checks)
- Merge: cross-chunk dedup, consistency, bump
- SKILL.md: aktualizacja pipeline description
- Testy jednostkowe

### Etap 2: Implementacja

Iteracyjna realizacja tasków. Po każdej większej iteracji (logiczny milestone, nie po każdym tasku):

1. **Implementacja** — kod, prompty, testy jednostkowe
2. **Testy automatyczne** — `uv run pytest`, ruff
3. **Self-review** — przeczytaj zmiany, sprawdź spójność, czy niczego nie brakuje
4. **Bird's-eye review** — świeże spojrzenie na cały skill z lotu ptaka (nie tylko zmiany)
5. **Sonnet review w tle** — odpal agenta (Agent tool), niech na świeżym kontekście przeczyta cały skill i sprawdzi spójność, logikę, zrozumiałość
6. **Fix** — napraw issues z review 3-5
7. **E2E test** — odpal agenta (Agent tool, świeży kontekst) na tier 1 golden files
8. **Ewaluacja** — odpal agenta (Agent tool, świeży kontekst) z promptem YAML → merge message. Porównaj wynik z golden file merge message
9. **Commit** — gdy czysto

### Etap 3: Testy E2E tier 2

Tier 2 dopiero gdy tier 1 (z etapu 2, punkty 7-8) przechodzi stabilnie.

| Repo | Zakres | Typ | Priorytet |
|------|--------|-----|-----------|
| trs-programmer-sw | master..TPL-199 | Qt/C++ MR (49KB diff) | **tier 1** (etap 2) |
| dr203-recorder-fw | 5.3.0..5.4.0 | embedded C (60KB diff) | **tier 1** (etap 2) |
| dr203-recorder-fw | 5.0.0..5.4.0 | embedded C (1.1MB diff) | **tier 2** (etap 3) |
| openwhispr | v1.6.2..v1.6.3 | Electron/TS (560KB diff) | **tier 2** (etap 3) |

Golden files w `lab/projects/test-repos/golden-outputs/` (nie commitowane). Generowane przez Opus 1M czytającego net diff bezpośrednio.

**Zasady testowania:**
- Testy E2E zawsze na agencie w tle (Agent tool, świeży kontekst). Nigdy inline
- **Tier 2 dopiero gdy tier 1 przechodzi.** Output tier 1 musi być wyraźnie zgodny z golden files (pokrycie zmian, typy, jakość opisów). Jeśli nie, wracamy do implementacji
- Porównanie: ilość zmian, typy, pokrycie plików, jakość opisów, brak hallucynacji

**Porównanie z golden files:**

Golden files zawierają YAML + merge message. Skill change-summary produkuje YAML, nie merge message. Aby porównać, po każdym E2E teście przetwórz YAML na merge message prostym promptem:

```
Przeczytaj <workdir>/changes.yaml. Na jego podstawie napisz merge message
w formacie Conventional Commits:

type(scope): subject

Changes:
- type: description
- type: description

Nie dodawaj nic od siebie. Użyj tylko danych z YAML.
Nie wymieniaj konkretnych nazw produktów.
```

Konwersję YAML → merge message zawsze odpalaj przez Agent tool (świeży kontekst), nie inline. Agent nie może mieć kontekstu z implementacji ani z E2E testu, żeby nie bias'ować wyniku.

Porównaj wynikowy merge message z golden file merge message. Kluczowe: czy te same zmiany zostały wyłapane, czy typy się zgadzają, czy nic nie brakuje i nic nie jest zhallucynowane.

### Web research

Jeśli coś nie działa lub potrzeba inspiracji, można użyć web searcha (WebSearch/WebFetch, agent-browser, context7) do sprawdzenia jak inni rozwiązują podobne problemy. Szczególnie przydatne dla: chunking strategies, diff parsing edge cases, YAML schema design.

### Stary kod v1

Development v2 na osobnym branchu. Stary per-commit kod (git_ops collect_commits, chunk build_commit_texts, format format_commit_section, virtual commits) można usuwać na bieżąco. Nic nie ginie, historia jest na main.
