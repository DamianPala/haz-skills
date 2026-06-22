---
name: ubuntu-release-upgrade
description: "Guide a safe Ubuntu/Kubuntu release upgrade (interim->LTS or LTS->LTS) end to end: pre-flight checks (upgrade path, third-party repos, DKMS), run do-release-upgrade, then post-upgrade fixes and verification. Generates a stateful runbook that survives the mid-upgrade reboot. Triggers: 'upgrade Ubuntu/Kubuntu to <version>', 'do-release-upgrade', 'release upgrade', 'zrob upgrade systemu do <wersja>', 'aktualizacja do nowego wydania'. DO NOT TRIGGER for routine package updates ('apt upgrade'), fresh installs, or non-Ubuntu distros."
version: 0.1.0
---

# Ubuntu Release Upgrade

You GUIDE a release upgrade: run only read-only inspection yourself, hand every
privileged/destructive command to the user. Six phases, each ending at a gate. The runbook
is the single source of truth and survives the mid-upgrade reboot.

## Rules

- GUIDE, do not execute. Run only the read-only helpers below. EMIT every `sudo` /
  destructive command for the USER to paste. NEVER run sudo yourself.
- Backup gate. DO NOT pass Phase 0 until the user confirms a full, RESTORABLE backup.
- NEVER use `-d`. It targets the unreleased *development* series, not a stable release,
  and is NOT how you reach interim (non-LTS) releases. Interim-vs-LTS targeting is the
  `Prompt=` setting (`normal` = next release of any kind; `lts` = next LTS only). Run plain
  `do-release-upgrade` only when the path is open.
- Runbook is the source of truth. On start, look for an existing runbook and RESUME from
  its first unchecked phase. Update its checkboxes and Decision log as you go.
- Verify before destructive. Never migrate a repo suite before confirming it exists,
  never autoremove before the safety analysis, never blind-answer a conffile prompt.
- Gate every destructive phase. Present findings and the exact commands, then WAIT for
  the user's explicit go-ahead before they run anything.
- Flavor/DE-aware. Apply KDE-specific fixes only when the desktop is Plasma.

`[GATE]` below means: present what you have, then STOP and wait for the user's explicit
response. Never present and act in the same message.

## How this works

Run read-only helpers (no sudo, no system changes) with:

```bash
uv run --project <skill-dir>/scripts ubuntu-release-upgrade <subcommand> [args]
```

`<skill-dir>` = this skill's directory. Requires `uv` (the helpers run via `uv run`). Each
subcommand prints JSON; read it, discuss with the user, record findings in the runbook.

| Subcommand | What it inspects |
|------------|------------------|
| `check-path [--target X]` | Upgrade path open? (meta-release `Supported:` flag) |
| `inventory-repos [--target-codename X] [--no-probe]` | APT sources: status, codename vs generic, target availability (`--no-probe` skips network check) |
| `classify-conffile <path>` | Pending conffile: maintainer-only vs user-modified |
| `generate-runbook [--target X] [--no-probe] [--force]` | Collect findings, write runbook (`--force` regenerates over existing) |

Three hazard checks (DKMS, autoremove, foreign packages) are NOT scripted: run raw tools
and reason, because output drifts across releases and seeing it lets you catch drift. See
`references/hazard-checks.md`.

Phases: **0** preconditions/backup, **1** pre-flight inspection, **2** prep, **3** the
upgrade, **4** post-upgrade fixes, **5** verification.

## Runbook & resume

The runbook lives at `~/.local/state/ubuntu-release-upgrade/runbook-<from>-to-<to>.md`.

On every invocation:
1. Look for an existing runbook at that path (or ask the user for it).
2. If one exists, READ it and resume at the first unchecked phase. Do not redo earlier
   phases.
3. If none exists, start at Phase 0.

`generate-runbook` never overwrites an existing runbook (it holds your progress); use
`--force` only to rebuild from scratch.

## Phase 0 - Preconditions & backup

1. Confirm a full, restorable backup (BorgMatic, image, or snapshot). `[GATE]` - do NOT
   continue until user explicitly confirms.
2. Run `check-path`. Read `path_open`:
   - `true` -> proceed.
   - `false` -> STOP. Report `advice`. If `development_only` is true, explain that `-d`
     targets the unreleased devel series, never a stable target. Tell the user to wait for
     `Supported: 1`. Offer to generate the runbook as a reference.
   - Check `prompt_policy`. `lts` = next LTS only; `normal` = next release of any kind;
     `never` = do-release-upgrade will NOT offer an upgrade, so tell the user to set
     `Prompt=normal` or `Prompt=lts` in `/etc/update-manager/release-upgrades` first. If
     `interim_alternative` is set, an interim release exists that `lts` would skip - tell
     the user it requires `Prompt=normal` in `/etc/update-manager/release-upgrades`, NOT `-d`.
3. Confirm AC power, a stable wired network, and 1-2h of time. If upgrading over SSH, run
   inside `screen` or `tmux`: `do-release-upgrade` refuses a plain SSH session and opens a
   backup sshd on port 1022.
4. System readiness (run the raw tools, reason with the user):
   - Disk space: `df -h / /var /boot`. A full or nearly-full `/boot` (or `/`) breaks the
     kernel install mid-upgrade - free space first.
   - Held/pinned packages: `apt-mark showhold` and `ls /etc/apt/preferences.d/`. These cause
     partial upgrades - resolve or note them before proceeding.
   - Clean state: `sudo dpkg --audit` and `apt-get check` must be clean; fix any
     half-configured packages before upgrading.
5. Ask the user about anything non-standard the checklist cannot cover (encrypted/RAID
   storage, unusual mounts/fstab, services or databases needing a manual stop/backup).
   Record it in the runbook.

## Phase 1 - Pre-flight inspection

1. Run `inventory-repos --target-codename <to>` (codename from `check-path`) and discuss
   results. Note any `warnings` (unparsed source files - verify by hand).
2. Do the three hazard checks from `references/hazard-checks.md` by running the raw tools and
   reasoning with the user:
   - DKMS: `dkms status` + each module's kernel pin vs. the target kernel.
   - Autoremove: `apt-get autoremove --purge -s` + classify protect-vs-drop.
   - Foreign packages: `apt list --installed 2>/dev/null | grep -F '[installed,local]'` +
     decide add-repo-before vs reinstall-after.
3. Run `generate-runbook --target <to>`. It writes the runbook with repo hazards and path
   filled in, blanks for DKMS/autoremove/foreign packages.
4. Record DKMS, autoremove, and foreign-package findings in the runbook. Walk the user
   through all hazards. `[GATE]` before any prep.

## Phase 2 - Prep (every command run by the USER)

Follow the runbook's Phase 2. Emit for the user; do not run:
1. Fully update current release: `sudo apt update && sudo apt full-upgrade`.
2. Update any incompatible DKMS module to a release supporting the target kernel, then
   `sudo dkms autoinstall`. On Secure Boot, rebuilt modules must be re-signed (enroll MOK
   if prompted).
3. Revert conflicting PPAs: `sudo ppa-purge ppa:<owner>/<name>`, one per PPA. Do
   backports/staging PPAs FIRST (they ship newer distro package versions, most common
   blocker). NEVER add `-d` or a suite not yet in sources.
4. Protect third-party tools before autoremove: `sudo apt-mark manual <packages>`. Then
   review the autoremove set; do not blindly purge.

`[GATE]` before the user runs the ppa-purge / autoremove-affecting steps.

## Phase 3 - The upgrade

1. Confirm path still open. Emit: `sudo do-release-upgrade`. NEVER `-d`.
2. Conffile prompts: for each file dpkg asks about, run the classifier yourself
   (`uv run --project <skill-dir>/scripts ubuntu-release-upgrade classify-conffile <path>`)
   and advise per `references/conffile-classification.md`. If exit 3 (root-only), hand the
   user the sudo variant:
   `sudo "$(command -v uv)" run --project <skill-dir>/scripts ubuntu-release-upgrade
   classify-conffile <path>`. Default to KEEPING user's version (N) unless they never edited
   the file. Record every decision in the runbook's Decision log.
3. Reboot expected at end. Runbook persists across it.

## Phase 4 - Post-upgrade fixes

Resume from runbook after reboot. Apply only what matches the system; see
`references/post-upgrade-fixes.md`.
1. Re-enable and migrate third-party repos. Bump codename suite only where
   `target_available` was true; leave purged PPAs and unavailable suites disabled.
2. `sudo apt update` and resolve every error before continuing.
3. Reinstall/rebuild foreign packages that had no repo (from the runbook hazards); rebuild
   their kernel modules for the new kernel if any.
4. KDE only: check SDDM session config.
5. Re-simulate autoremove (`apt-get autoremove --purge -s`): orphan set differs
   post-upgrade, pre-upgrade list is stale. Confirm protect list still holds, then
   `sudo apt autoremove --purge`.

`[GATE]` before autoremove.

## Phase 5 - Verification

Walk the runbook's verification checklist:
- `dkms status`: every module built for new kernel.
- GPU/display correct; SR-IOV/passthrough works if used.
- Audio works (one-time PipeWire restart crash during swap is benign).
- `apt-get check` and `sudo dpkg --audit` clean; no broken packages.
- Snaps (`snap refresh`) / Flatpaks (`flatpak update`) current if used.
- `lsb_release -a` shows new release.

Mark Phase 5 done in runbook and summarize changes and follow-ups.

## Conffile decisions

When `do-release-upgrade` prompts on a config file, use `classify-conffile` and
`references/conffile-classification.md`. Key question: did the user edit it? If not, take
maintainer's version; if yes, keep theirs (or merge). When unsure, keep theirs - reversible.

## Error paths

- Path closed (`path_open: false`): do not upgrade, do not use `-d`. Report advice and wait.
  Optionally generate runbook as reference.
- DKMS module won't build for target kernel: stop before upgrade; update module to a
  target-capable release first, or the driver (GPU/network) may be lost.
- Target repo suite missing (`target_available: false`): keep repo disabled after upgrade;
  do not point at a codename the vendor hasn't published.
- Helper exits non-zero: network error (exit 2) on check-path - retry or verify the path by
  hand; meta-release parsed to nothing (exit 1 on check-path) - format may have changed,
  verify path by hand; permission denied (exit 3) on classify-conffile - re-run with sudo
  (Phase 3); not-applicable (exit 1) on classify-conffile - no pending change.
- Repo probe can't reach the network: it does NOT fail - it sets `target_available: null`
  (unknown). Do not bump that suite until verified; re-run inventory-repos later or pass
  `--no-probe`.
- Tool missing (`do-release-upgrade`, `ppa-purge`, `dkms`): install it (`update-manager-core`,
  `ppa-purge`) or skip the step, note in runbook.
- Runbook missing on resume: ask user for path, or regenerate (loses recorded progress and
  decisions).

## Constraints

- GUIDE only: run read-only helpers; EMIT every sudo/destructive command for the USER.
  NEVER run sudo yourself.
- Backup gate is a hard stop before any prep.
- NEVER use `do-release-upgrade -d` for a stable target.
- The runbook is the source of truth: resume from it, update it, do not clobber it.
- Verify before destructive: confirm suites exist, run the safety analysis, classify each
  conffile. Gate every destructive phase.
