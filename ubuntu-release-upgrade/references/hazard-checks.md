# Pre-flight hazard checks (DKMS, autoremove, foreign packages)

These checks are done by reading raw tool output and reasoning, not by a wrapper
script: the tools' output drifts across releases, and seeing the real output lets you
catch that drift instead of trusting a silently-wrong parse. Record findings in the
runbook.

## DKMS modules

Out-of-tree kernel modules (GPU drivers, VirtualBox, ZFS, SR-IOV, etc.) are rebuilt
against the new kernel. A module that does not support the target kernel series will fail
to build, and you can lose that driver at boot (no GPU, no network).

1. List modules and their state:
   ```bash
   dkms status
   ```
2. For each module, read its build constraints:
   ```bash
   cat /var/lib/dkms/<module>/<version>/source/dkms.conf 2>/dev/null \
     || cat /usr/src/<module>-<version>/dkms.conf
   ```
   - `BUILD_EXCLUSIVE_KERNEL="<regex>"` - the module only builds when `uname -r` matches
     this regex. If the target kernel will NOT match, the module is at risk.
   - Some modules encode the supported range in a `PRE_BUILD` script instead - check the
     project's README / release notes for the supported kernel range.
3. Find the target kernel: it is the kernel shipped by the target release (check the
   target release notes, e.g. "ships kernel X.Y"). If you cannot determine it pre-upgrade,
   note that DKMS compatibility is unverified and rely on Phase 5 (`dkms status` after the
   upgrade) as the backstop.
4. For any at-risk module: update it to a release that supports the target kernel BEFORE
   the upgrade, then `sudo dkms autoinstall`. Record it in the runbook.

Secure Boot: a rebuilt module must be re-signed. If MOK enrollment is prompted at the
next boot, complete it, or the module will be blocked.

`dkms status` only lists DKMS-registered modules. Some vendor packages build their kernel
modules their own way (e.g. Oracle VirtualBox via `vboxconfig`) and never appear here -
whether installed from a third-party repo or a standalone `.deb`. Watch for them in the repo
inventory and the foreign / local package check below, then rebuild for the target kernel
like any out-of-tree module.

## Autoremove candidates

After a release upgrade, `apt autoremove` can sweep away tools that got marked `auto` and
that nothing in the new release depends on - including third-party software you still use
(e.g. a Node.js from a vendor repo, ffmpeg, a hand-installed CLI).

1. Simulate (no changes made):
   ```bash
   apt-get autoremove --purge -s
   ```
   The `Remv <pkg>` lines are the removal candidates.
2. Classify each candidate. The deciding signals:
   - Old kernels (`linux-image/headers/modules-*`) - safe to remove.
   - Pure libraries / `-dev` / `-doc` / `-common` with no executables - safe.
   - Ships executables (`dpkg -L <pkg>` lists `/usr/bin`, `/usr/sbin`, ...) AND comes from
     a non-distro origin - PROTECT. Check origin:
     ```bash
     apt-cache policy <pkg>
     ```
     If the installed version's source host is not an `*.ubuntu.com` archive (e.g.
     `ppa.launchpadcontent.net`, `deb.nodesource.com`, or locally installed), it is
     third-party and worth keeping.
   - Ships executables from the distro - review with the user; usually not a candidate.
3. Protect the keepers BEFORE the upgrade (Phase 2):
   ```bash
   sudo apt-mark manual <packages>
   ```
   The pre-upgrade simulation is mainly for this: identify what to protect. `apt-mark
   manual` persists across the upgrade, and `do-release-upgrade` itself can remove
   obsolete packages mid-flight, so the protection must be in place first.

4. Run the real cleanup AFTER the upgrade (Phase 4), and re-simulate first - the orphan
   set is different post-upgrade (old libs, transitional and obsolete packages, old
   kernels), so the pre-upgrade list is stale:
   ```bash
   apt-get autoremove --purge -s     # fresh post-upgrade simulation
   ```
   Confirm the protect list still holds and nothing you rely on is in the list, then:
   ```bash
   sudo apt autoremove --purge
   ```

This is a judgement call, not a mechanical rule: present the list to the user and confirm
before marking or removing anything.

## Foreign / local packages

Packages installed outside any APT repo - a standalone `.deb`, or a package whose repo was
later removed - are invisible to the repo inventory. `do-release-upgrade` will not update
them, and if they ship kernel modules or pin a specific ABI they can break after the
upgrade (a hand-installed virtualization or GPU package is the classic case).

1. List them:
   ```bash
   apt list --installed 2>/dev/null | grep -F '[installed,local]'
   ```
   The `,local` tag means the installed version is not offered by any configured source.
2. For each, decide BEFORE the upgrade:
   - Has an official APT repo? ADD the repo now (Phase 2) so the package upgrades normally
     and Phase 4 can migrate its suite. Prefer this over a standalone `.deb`.
   - No repo? Record it to REINSTALL / rebuild manually after the upgrade (Phase 4), and
     note whether it ships a kernel module - then it also needs the DKMS-style rebuild above.
3. These do NOT migrate like repo suites: there is no codename to bump. The post-upgrade
   action is "reinstall the current build", not "re-enable a source".

Judgement call: present the list and agree the plan per package before continuing.
