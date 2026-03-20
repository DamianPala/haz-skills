# release-create: plan

## Cel

Skill do tworzenia release'ów (tag + release notes + opcjonalnie CHANGELOG.md). Nie CI/CD automation, nie publishing do registry.

## Scope

### Robi

- Znajduje ostatni tag, zbiera commity od niego
- Parsuje commity (Conventional Commits i niestandardowe konwencje jak `[FEAT]`, `[FIX]`, `[DEV]`)
- Grupuje zmiany (Added, Fixed, Changed, etc. - Keep a Changelog)
- Proponuje semver bump (major/minor/patch) na podstawie typów zmian
- Generuje release notes (treść do tag message / GitHub Release / GitLab Release)
- Aktualizuje CHANGELOG.md (jeśli istnieje lub user chce go utworzyć)
- Tworzy git tag (annotated, z release notes jako message)
- Tworzy GitHub/GitLab release (`gh release create` / `glab release create`)
- Respektuje istniejącą konwencję tagów (z `v` / bez `v`)

### Nie robi

- Setup CI/CD pipeline
- Publishing do npm/pypi/cargo/docker
- Bump wersji w plikach projektu (package.json, pyproject.toml)
- Automatyczny push (pyta o potwierdzenie)
- Monorepo (wiele pakietów/wersji w jednym repo)

## Konwencje

- **Tag format** (schemat decyzyjny):
  1. `git tag --list` - są istniejące tagi?
  2. Tak → sprawdź konwencję: większość z `v` prefix → użyj `v`. Większość bez → nie dodawaj `v`
  3. Nie (brak tagów, nowe repo) → domyślnie semver z `v` prefix (`v1.0.0`)
  4. Mieszane tagi → **blocking prompt**: "Mixed tag convention (vX.Y.Z and X.Y.Z). Which to use?"
- **Changelog**: Keep a Changelog (keepachangelog.com). Jeśli repo nie ma CHANGELOG.md lub ma inny format, blocking prompt z propozycją
- **Semver**: MAJOR (breaking), MINOR (feat), PATCH (fix/refactor/perf)

## Mapowanie niestandardowych commit prefixów

Skill musi parsować nie tylko Conventional Commits, ale też inne konwencje:

| Prefix | CC equivalent | Keep a Changelog |
|--------|--------------|-----------------|
| `[FEAT]` | `feat` | Added |
| `[FIX]` | `fix` | Fixed |
| `[IMP]` | `refactor`/`perf` | Changed |
| `[DEV]` | `chore` | Changed (lub pomijane) |
| `feat:`, `feat(scope):` | - | Added |
| `fix:`, `fix(scope):` | - | Fixed |
| `BREAKING CHANGE` / `!` | - | Changed/Removed z `**BREAKING:**` prefix + MAJOR bump |

Nierozpoznane commity: pytaj usera o kategoryzację (nie twórz kategorii "Other").

## Dependency: merge-message

Release-create bazuje na CC commit messages na master/main. Przy squash merge historia brancha jest tracona. Skill **merge-message** (osobny, ~40-50 linii) zapewnia jakość squash commit messages:

1. Czyta commity na branchu od base (`git log base..HEAD`)
2. Opcjonalnie czyta MR/PR description
3. Generuje CC squash message: subject + body z listą zmian (każda z CC prefixem)
4. User wkleja w merge dialog (GitLab/GitHub GUI)

Bez merge-message release-create wciąż działa, ale jakość changelog zależy od tego co dev wpisał ręcznie w squash message.

Fallback dla repo z RC tagami: release-create może zbierać RC tag messages jako alternatywne źródło danych (RC tagi mają structured `[FEAT]`/`[FIX]` info).

## Struktura skilla

```
release-create/
├── SKILL.md          (rules, workflow, constraints - sandwich pattern)
├── plan.md           (ten plik - do usunięcia po implementacji)
├── scripts/
│   └── detect-platform.py  (kopia z pr-create, self-contained)
└── references/
    └── keep-a-changelog.md  (loaded at Step 3)
```

## Workflow (draft)

**Blocking prompt**: one per call, one question. Use platform's prompting tool (AskUserQuestion, ask_user, prompt). Plain text only if none exists. Never batch multiple questions.

### Step 1: Detect state

- Platform detection (gh/glab) - reuse `detect-platform.py` z pr-create
- Branch detection: `git branch --show-current`
  - main/master/develop → **final release**
  - inny branch → **RC release** (proponuj `X.Y.Z-rc.N`)
- Ostatni tag: `git describe --tags --abbrev=0`
  - Jeśli brak tagów (pierwszy release): **blocking prompt** "No tags found. First release. Version? (v1.0.0 / v0.1.0 / custom)"
- Konwencja tagów: `v` prefix czy nie (z istniejących tagów)
- Commity od tagu: `git log <tag>..HEAD --format='%H %s'`
  - Dla final release na master: dodatkowo zbierz RC tag messages między ostatnim finalem a HEAD (fallback gdy squash merge stracił historię)
- Jeśli 0 commitów: abort "Nothing to release since <tag>"

### Step 2: Analyze changes (via change-summary)

Spawn sub-agent z change-summary skill:
- "Use the Skill tool to invoke 'change-summary'. Analyze changes between <last_tag> and HEAD. Platform: <detected>. Host: <detected>"
- Sub-agent produkuje YAML output z: `type`, `category` (KaC ready), `description`, `commit`, `confidence`, `migration` (breaking)
- Read YAML output. `category` jest gotowe do użycia w Keep a Changelog (Added/Fixed/Changed/Removed/Deprecated/Security)
- `suggested bump` z YAML → propozycja semver
- Jeśli YAML ma `skipped` internal changes: **blocking prompt** "N internal changes skipped. Include? (all / summarize / skip)"

Fallback: jeśli change-summary nie zainstalowany, parsuj commit messages inline (basic CC + custom prefix matching)

### Step 3: Generate release notes

- Keep a Changelog format (keepachangelog.com v1.1.0)
- Reguły i template w bundled reference: `references/keep-a-changelog.md`. Skill czyta ten plik w runtime (progressive disclosure per skill-creator standard)
- SKILL.md zawiera instrukcję: "Before generating, read `references/keep-a-changelog.md` for formatting rules and template"
- Changelog skill (gdy powstanie) będzie miał własną kopię tego samego pliku w swoim `references/`. Duplikacja OK, standard się praktycznie nie zmienia

**Perspektywa klienta:** Release notes mogą wymagać perspektywy end-usera, nie developera. Np. firmware recorder: user chce wiedzieć "dodano regulację jasności ekranu" a nie "dodano BrightnessTimer z 5-level contrast switching na SSD1306". Skill powinien wykryć kontekst projektu (embedded/B2B/open-source/library) i dopasować ton:
- **Library/SDK/API:** developer-facing, technical, migration guides
- **Firmware/hardware/B2B product:** customer-facing, user benefit, no implementation details
- **Open-source tool:** mix, power users chcą detale, casual users chcą "what's new"

Domyślnie: user perspective. Blocking prompt jeśli niepewny: "Release notes for developers or end users?"

**Output variants:**
- CHANGELOG.md: pełny format z headerem, compare linkami, sekcja [Unreleased]
- Tag message: tylko sekcja danej wersji, plain text (bez markdown linków)
- Release body (gh/glab): sekcja danej wersji z markdown linkami

### Step 4: Verify (internal checklist)

Change-summary skill already verifies its YAML output via a dedicated sub-agent before returning it. Release-create trusts that data and only verifies the formatting layer (Keep a Changelog compliance).

**Internal checklist (no sub-agent needed):**
1. Every item from change-summary YAML present in the changelog?
2. `category` → correct KaC section (Added/Fixed/Changed/Removed/Deprecated/Security)?
3. Breaking changes have migration notes?
4. Compare links correct for the platform (GitHub/GitLab)?
5. Version number consistent (tag, header, compare link)?
6. Date is today?
7. Format matches `references/keep-a-changelog.md` rules?

If any check fails, fix inline and re-check.

### Step 5: Present for review

- Pokaż: proponowana wersja, release notes, lista plików do zmiany
- **Blocking prompt**: "Version <X.Y.Z>, release notes OK? (y/edit/cancel)"
- Jeśli edit: zrzuć do temp file, czekaj na potwierdzenie

### Step 6: Execute

- Aktualizuj CHANGELOG.md (jeśli w scope): prepend nowej wersji pod nagłówkiem `# Changelog`, zachowaj istniejącą treść. Jeśli plik nie istnieje: utwórz z headerem Keep a Changelog + pierwsza wersja
- Stwórz annotated tag: `git tag -a <version> -m "<release notes>"`
- **Blocking prompt**: "Push tag and create release? (y/n)"
- Push tag: `git push origin <tag>`
- Stwórz release: `gh release create` / `glab release create`

### Step 7: Post-release guidance

Skill nie czeka na CI, nie polluje, nie weryfikuje artefaktów. Zamiast tego daje agentowi kontekst:

- Zawsze: tag name, release URL, "Verify the release page: [URL]"
- Jeśli CI config wykryty w repo (`.gitlab-ci.yml`, `.github/workflows/`): "Pipeline may be running. Check: `glab ci status` / `gh run list`"
- Jeśli brak CI config: "No CI pipeline detected. To attach build artifacts: `glab release upload <tag> ./file` / `gh release upload <tag> ./file`"

To jest output informacyjny, nie blocking prompt. Agent w sesji może potem zaproponować sprawdzenie.

## Description (draft)

```
"Create releases with changelog, tag, and platform release page. Analyzes commits since last tag, generates Keep a Changelog notes, proposes semver bump, creates annotated git tag and GitHub/GitLab release. Handles RC pre-releases on feature branches, custom commit prefixes ([FEAT]/[FIX]/[DEV]), and tag convention detection. Supports GitHub (gh) and GitLab (glab). Triggers: 'create release', 'new release', 'release this', 'make release', 'tag release', 'zrob release', 'nowy release', 'wypusc wersje', 'release notes'. Also trigger when user mentions tagging a version, cutting a release, or generating changelog. DO NOT TRIGGER for commits, PR creation, CI/CD setup, or deployment."
```

## Referencje

- **Struktura**: sandwich pattern z commit/pr-create (Rules, Workflow, Constraints)
- **Platform detection**: `pr-create/scripts/detect-platform.py`
- **Git commands**: changelog-writer (library/patricio0312rev)
- **Blocking prompts**: pattern z pr-create (AskUserQuestion, one-per-call)
- **Changelog format**: Keep a Changelog (keepachangelog.com)

## Test cases

### Case 1: trs-programmer-sw (final release, GitLab self-hosted)

Repo: `gitlab.sentisa.com/software/termoplus/trs-programmer-sw`
- GitLab self-hosted, glab CLI
- Branch: master, 54 commity, 10 tagów (1.6.0 - 2.2.0, bez `v`)
- Konwencja commitów: `[FEAT]`, `[FIX]`, `[IMP]`, `[DEV]`
- Aktualnie 0 commitów od 2.2.0 (MR w trakcie merge)
- Oczekiwany wynik: 2.3.0 lub 2.2.1 (zaleznie od typu zmian w MR)
- Testuje: custom prefix parsing, no `v` convention, GitLab self-hosted, dev commit filtering

### Case 2: dr203-recorder-fw (RC workflow, GitLab self-hosted)

Repo: `gitlab.sentisa.com/firmware/termoplus/dr203-recorder-fw`
- GitLab self-hosted, glab CLI
- Branch: master + feature branches, tagi z RC (5.2.0-rc.1 ... 5.4.0)
- Konwencja commitów: `[FEAT]`, `[FIX]`, `[IMP]`, `[DEV]`
- Testuje: RC tag detection, branch-based final vs RC, RC tag messages jako fallback, semver pre-release

