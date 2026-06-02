---
name: openwrt-backup-restore
description: "Back up or restore OpenWrt 24+ routers from sysupgrade config backups, package manifests, and custom-file archives. Use for OpenWrt backup/restore, apk/opkg package ordering, zrób backup OpenWrt, przywróć router z backupu. Do not trigger for generic networking, router shopping, firmware flashing, or unrelated Linux backups."
version: 0.2.0
---

# OpenWrt Backup Restore

## Core rules

- Start by asking which mode applies: `backup` or `restore`, then keep that workflow separate.
- Do not assume `192.168.1.0/24` or that the agent network equals the router upstream network.
- Restore order: packages, config, then companion custom files. Package restore requires target WAN internet.
- Use `sysupgrade -k` package metadata first. Treat `/etc/apk/world` as diagnostic only.
- Do not make network, firewall, Wi-Fi, reboot, reset, or LAN-IP changes without approval when they can cut access. If SSH drops, stop and wait for reconnect.
- Prefer Ethernet when access is over target Wi-Fi.
- Use the bundled router-side collector script for backup collection. Keep restore interactive and approval-driven.
- In restore mode, determine whether the operator machine is already connected to the target router before treating the local default gateway as upstream.
- Before any cabling step that may cut internet, give one complete offline-safe handoff prompt.

## Scope

- Back up and restore OpenWrt 24+ routers using `sysupgrade` config archives, package metadata, and companion custom-file archives.
- Support both `apk` and `opkg`.
- Check backup and target compatibility before restore.
- End with a short operational report.

Out of scope:

- firmware flashing
- partial restore
- blind install from `/etc/apk/world`

Treat backups as sensitive because they may contain password hashes, Wi-Fi keys, VPN credentials, private keys, tokens, and scripts with secrets.

## Mode selection

If the user has not said which mode they want, ask:

1. `backup`, for a working router that needs a backup set.
2. `restore`, for a fresh or recovered router that needs packages and config restored.

If the router is already broken, start in `restore` mode and inspect it before changing anything.

## Backup workflow

Goal: create a backup set that can be validated before restore.

### 1) Establish SSH access

Infer the router SSH target from user input or the current default gateway when the user says to back up the router currently in use.
Try SSH with existing keys first.
If authentication fails, ask the user for the router SSH username/password or a temporary access method, then retry.
Do not continue to backup collection until read-only SSH commands work.

### 2) Confirm the router is working

Collect at least:

- `ubus call system board`
- `/etc/openwrt_release`
- package manager detection with `command -v apk` and `command -v opkg`
- `df -h`

### 3) Run the router-side backup collector

Copy bundled [`scripts/collect-backup.sh`](scripts/collect-backup.sh) to `/tmp`, run it, then transfer `/tmp/openwrt-backup-bundle.tar.gz`.
It creates `config-backup.tar.gz`, `custom-files.tar.gz`, and `manifest.txt`.

Example:

```sh
scp -O scripts/collect-backup.sh root@<router-ip>:/tmp/openwrt-collect-backup.sh
ssh root@<router-ip> 'sh /tmp/openwrt-collect-backup.sh'
```

The bundle contains:

- `config-backup.tar.gz`, created with `sysupgrade -k -b`
- `custom-files.tar.gz`, selected custom files not already in `config-backup.tar.gz`
- `manifest.txt`, firmware, board, storage, routing, package metadata, custom file list, `sysupgrade -l`, `/etc/sysupgrade.conf`, `apk audit`, and installed-package diagnostics

The custom archive is limited to known custom-file locations: `/etc/hotplug.d`, `/etc/profile.d`, `/root/bin`, `/usr/local`, and `/etc/rc.local`.

### 4) Transfer the backup off the router

Ask the user for a concrete local destination path, then transfer `/tmp/openwrt-backup-bundle.tar.gz` there.
Name the local copy `openwrt-backup-<model-slug>-<date>-<time>.tar.gz`, for example `openwrt-backup-zte-mf289f-2026-05-26-1430.tar.gz`.
Build `<model-slug>` from the board/model metadata and sanitize it to lowercase `a-z0-9-`.
Prefer `scp -O` for Dropbear/OpenWrt; otherwise use the simplest available user-approved method such as SFTP or a mounted share.

## Restore workflow

Goal: restore packages first, then config, then companion custom files, without losing operator access.

### 1) Locate and confirm the backup bundle

Before inspecting cabling or touching the target router, select the backup bundle.
Use one short prompt:

> Which OpenWrt backup bundle should I restore?
> Give me the exact file path, or tell me which local directories to search for `openwrt-backup-*.tar.gz`.

If the user gives directories, list candidates and ask which one to use.
If one obvious bundle is found, ask for confirmation.
Read the backup's restored LAN IP/netmask later on the router side (step: Inspect the backup before restore), where `uci` is available, rather than extracting the nested archive on the operator machine. If the user already knows the restored LAN, note it now for cabling-recovery LAN selection.

### 2) Determine current topology

Before touching the target router, determine what the operator machine is connected to now.
Ask one direct question before running local topology checks, probing the default gateway, or opening SSH/LuCI:

> Before I infer upstream or ask you to move cables: what is this operator machine connected to right now?
> Is it on the existing upstream router, on the target OpenWrt router LAN, on the target OpenWrt Wi-Fi, or another path?

Do not skip this question because model, firmware, LAN IP, hostname, or SSH identity appear to match the backup; the operator may have multiple identical routers, cloned firmware, or a temporary topology.

Verify with read-only local checks:

- active interface, local IP/subnet, default gateway, gateway MAC when available
- whether internet works from the operator machine

Do not assume the operator machine default gateway is the upstream router.
It may be the target OpenWrt router LAN address.

If the default gateway looks like OpenWrt, identify it before deciding the topology.
Use read-only SSH or LuCI metadata and collect:

- `ubus call system board`
- `/etc/openwrt_release`
- package manager detection
- `ip -br addr`
- `ip route`
- `ifstatus wan`
- current LAN IP and netmask with `uci -q get network.lan.ipaddr` and `uci -q get network.lan.netmask`

Classify the operator machine as already connected to the target only when the user has explicitly confirmed it in the topology question above.
Identity signals alone (model, firmware, LAN IP, hostname, SSH key) do NOT establish this; they can match a coincidentally identical router, so never classify on identity match without the user's confirmation.
Once confirmed, skip the cabling handoff, infer upstream from the target WAN state (`ifstatus wan`, WAN address/mask, gateway, DNS), and continue with target inspection.

If the operator machine is connected directly to the existing upstream router, continue with upstream discovery and cabling handoff.

### 3) Inspect upstream when not already on the target

Run this only when the operator machine is not already connected to the target router.
Inspect the operator machine network and treat internet-working networks as upstream candidates.
Use available local network tools first; ask the user only for networks the agent cannot inspect.

Present the detected networks to the user and ask which one will be used as the target router WAN upstream.
If the answer matches one of the detected networks, use its inferred subnet as the upstream subnet.
If none of the detected networks will be used, ask the user to make the intended upstream network visible temporarily or provide its router LAN IP and subnet mask.
If the upstream subnet remains unknown, stop before WAN connection.

Assume the operator machine has one Ethernet port.
Do not use WAN-exposed SSH/LuCI as a recovery path.
Single-port recovery may interrupt the agent, so stop after giving the handoff prompt.

### 4) Give one complete cabling and conflict-recovery prompt

Show the user one concrete cabling prompt before asking them to move cables.
Run this only when the operator machine is not already connected to the target router.
Adapt interface names and IP ranges to the detected environment.
Write the prompt in the language the user is currently using in the conversation.
The prompt must be self-contained because the agent may lose internet while the user follows it.
Do not continue issuing commands until the user returns.

Use this structure:

> I detected the current internet/upstream network as `{upstream_subnet}` via gateway `{upstream_gateway}`.
> I will stop here while you move cables because this may temporarily disconnect this agent.
>
> Connect the target OpenWrt router WAN port to the existing upstream router.
> Connect the operator machine Ethernet port to a LAN port of the target OpenWrt router.
>
> Wait about 1-2 minutes.
>
> If this machine gets internet through the target router, return to this conversation and I will continue the restore.
>
> If internet does not come back, assume a possible LAN/WAN subnet conflict.
> This commonly happens when both routers use the same LAN network, for example `192.168.1.0/24`.
> Fix it offline with these steps:
>
> 1. Disconnect the target router WAN cable from the upstream router.
> 2. Keep the operator machine connected to a LAN port of the target router.
> 3. Open a browser and try the usual OpenWrt address first: `http://192.168.1.1/`.
> 4. If the page does not open, find the router address from the computer network details.
>    On Windows: open the Start menu, type `cmd`, press Enter, type `ipconfig`, press Enter, find the Ethernet adapter, then copy the number shown as `Default Gateway`.
>    On macOS: open Terminal, type `route -n get default`, press Enter, then copy the value shown after `gateway:`.
>    On Linux: open Terminal, type `ip route | awk '/default/ {print $3; exit}'`, press Enter, then copy the printed address.
>    Then open `http://<gateway-address>/` in the browser.
>    If there is no DHCP address or gateway, set a temporary manual address such as `192.168.1.2/24` on the operator machine and try `http://192.168.1.1/` again.
> 5. In LuCI (OpenWrt Dashboard), go to `Network > Interfaces > LAN > Edit`, change `IPv4 address` to `{new_lan_ip}`, keep DHCP enabled on LAN, then `Save` and `Save & Apply`.
> 6. LuCI will disconnect after the LAN address changes. Unplug and reconnect the operator machine Ethernet cable, or disable and re-enable the wired connection, so it gets a fresh LAN address.
> 7. Open the router again using the new address, for example `http://{new_lan_ip}/`.
> 8. Connect the target router WAN port back to the upstream router.
> 9. Keep the operator machine connected to a LAN port of the target router.
> 10. Wait 1-2 minutes. If internet starts working through the target router, return to this conversation.
> 11. If internet still does not work, reconnect the operator machine directly to the upstream router and return here with the gateway/IP values you saw.

Choose `{new_lan_ip}` from a simple private subnet that does not overlap the detected upstream subnet.
This is only a temporary recovery address; the backup's actual restored LAN is reconciled later (step: Inspect the backup before restore) and patched if it overlaps the upstream.
If the restored LAN is already known and does not overlap the upstream subnet, prefer that LAN IP so the later config restore does not change it again.
For LuCI, use an address without CIDR notation, for example `192.168.10.1`, with netmask `255.255.255.0`.

If access is over the target router Wi-Fi:

- warn that Wi-Fi config restore or reload may cut the session
- prefer Ethernet before any wireless changes
- ask for explicit approval before any Wi-Fi-related restore action

If the target router still cannot get internet after the handoff, stop before package restore.

### 5) Inspect the target router

Run this after either:

- the user returns from the cabling handoff and the agent can reach the target router through the new cabling
- topology discovery found that the operator machine is already connected to the target router

Collect and compare:

- `ubus call system board`
- `/etc/openwrt_release`
- package manager detection
- free overlay space with `df -h`
- current LAN IP and netmask with `uci -q get network.lan.ipaddr` and `uci -q get network.lan.netmask`
- WAN state and internet reachability
- whether the current LAN subnet overlaps the target WAN upstream subnet

Compare target identity with backup metadata.
If LAN and WAN overlap, report it as a routing risk and verify router-side internet before package restore.
If router-side internet fails because LAN and WAN overlap, ask for approval to move the target LAN to a non-overlapping private subnet before package restore.
Before applying the change, give the operator this self-contained recovery prompt, because the reload will likely drop this connection:

> I will change the target router LAN from `{old_lan}` to `{new_lan_ip}` and reload its network. This connection will probably drop. After it does:
>
> 1. Unplug and reconnect the operator machine Ethernet cable, or disable and re-enable the wired connection, to get a fresh DHCP lease on the new subnet.
> 2. Wait 1-2 minutes, then open `http://{new_lan_ip}/` to confirm the router responds.
> 3. If no address arrives, set a temporary manual address on the operator machine in the new subnet, for example `{new_lan_host_ip}` with netmask `255.255.255.0`, then open `http://{new_lan_ip}/`.
> 4. If unsure which gateway you landed on:
>    On Windows: open `cmd`, run `ipconfig`, read `Default Gateway`.
>    On macOS: open Terminal, run `route -n get default`, read `gateway:`.
>    On Linux: open Terminal, run `ip route | awk '/default/ {print $3; exit}'`.
> 5. Return to this conversation once you can reach the router again.

Apply the LAN config change, verify the committed UCI values, then reload networking as the last SSH action and stop until the operator returns.
Preserve the existing config style: option-style LANs (a `network.lan.netmask` value is set) keep `option ipaddr` + `option netmask`; list/CIDR-style LANs use `list ipaddr`.

```sh
ssh root@<old-lan-ip> '
set -e
stamp=$(date +%Y%m%d-%H%M%S)
cp /etc/config/network /etc/config/network.bak-before-lan-subnet-change-$stamp
if uci -q get network.lan.netmask >/dev/null; then
    uci set network.lan.ipaddr="<new-lan-ip>"
    uci set network.lan.netmask="<new-lan-netmask>"
else
    uci -q delete network.lan.ipaddr
    uci add_list network.lan.ipaddr="<new-lan-cidr>"
fi
uci commit network
uci -q get network.lan.ipaddr
uci -q get network.lan.netmask || true
'

timeout 10 ssh root@<old-lan-ip> '/etc/init.d/network reload'
```

The reload command may return non-zero because SSH drops after the LAN change.
Treat failures before the verified `uci commit` as blocking, but after starting the reload, stop and wait for the operator to reconnect.
After the operator returns, verify the operator machine DHCP lease, SSH to the new LAN IP, WAN state, and router-side internet before continuing.
If target WAN internet is unavailable, stop before package restore.
If the operator machine is already connected to the target router, report the WAN/LAN/routing issue directly instead of referring back to the cabling handoff.
If the agent reached this point after a cabling handoff, refer back to the handoff prompt.

### 6) Inspect the backup before restore

Copy the backup bundle to the router, usually under `/tmp`, then inspect it before restoring anything.
First list the top level with `tar -tzf <bundle.tar.gz>` and classify it before extracting files.

```sh
tar -tzf /tmp/<bundle.tar.gz> | sed -n '1,40p'
```

Then set archive roles explicitly:

- Collector bundle: top level holds `config-backup.tar.gz`, `custom-files.tar.gz`, and `manifest.txt`. Create a fresh temporary directory, extract only those expected wrapper files into it, then set `config_archive="$restore_dir/config-backup.tar.gz"`, `custom_archive="$restore_dir/custom-files.tar.gz"`, and `manifest="$restore_dir/manifest.txt"`.
- Bare `sysupgrade`/LuCI backup: top level holds config paths directly (`etc/config/...`) and no wrapper files. Set `config_archive` to the absolute bundle path, `custom_archive=none`, and `manifest=none`. Warn that companion custom files are not present, skip custom-file restore, and rely on `etc/backup/installed_packages.txt` if present.

Example collector extraction:

```sh
restore_dir="$(mktemp -d /tmp/restore-bundle.XXXXXX)"
tar -xzf /tmp/<bundle.tar.gz> -C "$restore_dir" \
    config-backup.tar.gz custom-files.tar.gz manifest.txt
config_archive="$restore_dir/config-backup.tar.gz"
custom_archive="$restore_dir/custom-files.tar.gz"
manifest="$restore_dir/manifest.txt"
```

Check:

- bundle contents with `tar -tzf <bundle.tar.gz>`
- config archive contents with `tar -tzf "$config_archive"`
- config archive paths for absolute paths, `..` path segments, symlink/device entries, and unexpected top-level paths before `sysupgrade -r`
- custom archive paths and entry types only when `custom_archive` is not `none`
- package metadata with `tar -O -zxf "$config_archive" etc/backup/installed_packages.txt`
- firmware, board, package, and custom-file metadata from `manifest` only when present
- config files that may trigger package dependencies or service issues
- target LAN IP/netmask in `etc/config/network`

Example backup LAN check:

```sh
rm -rf /tmp/backup-uci
mkdir -p /tmp/backup-uci
tar -O -zxf "$config_archive" etc/config/network > /tmp/backup-uci/network
uci -c /tmp/backup-uci -q get network.lan.ipaddr
uci -c /tmp/backup-uci -q get network.lan.netmask
```

Examples of risky config areas:

- wireless features such as `bss_transition`
- protocol configs such as `qmi`
- service helpers such as `usteer`
- VPN and tunnel services
- custom hotplug scripts

If the backup appears to come from a different device family or an incompatible OpenWrt major version, stop unless the user explicitly approves an advanced restore risk.
If `custom_archive` is not `none` and contains logs, shell history, backup archives/dumps, absolute paths, `..` path segments, symlink/device entries, or paths outside the known custom-file locations, stop before extracting it.
Do not reject executable scripts just because their filename contains `backup` when they are inside the known custom-file locations and pass the entry-type checks.
If the backup LAN subnet overlaps the target WAN upstream subnet, stop before config restore and ask the user to choose a replacement restored LAN, for example `192.168.10.1/24`.
Record it as the planned restored LAN override and proceed only with explicit approval to restore config and immediately patch LAN before reboot or network reload.
Use the target WAN upstream subnet from target inspection when already on the target; otherwise use the upstream subnet from operator network discovery.

### 7) Restore packages before config

Use `etc/backup/installed_packages.txt` from `config_archive` as the main package source when available.
Filter it to packages marked `overlay` or `unknown`; packages marked `rom` are normally part of the image and should not be reinstalled blindly.

Example filter:

```sh
tar -O -zxf "$config_archive" etc/backup/installed_packages.txt 2>/dev/null \
    | awk '$2 == "overlay" || $2 == "unknown" { print $1 }'
```

If `installed_packages.txt` is missing, use installed-package lists only as best-effort diagnostics and warn that they may include dependencies or miss manual intent:

```sh
# apk targets
apk list -I

# opkg targets
opkg list-installed
```

Package install rules:

- restore packages before config
- reinstall packages that were user-installed, `overlay`, `unknown`, or otherwise clearly not part of the base image
- normally skip `rom` packages from `installed_packages.txt`
- skip base, kernel, and libc packages unless exact firmware compatibility is confirmed
- do not use `/etc/apk/world` as the install list

Use the active package manager:

```sh
# apk path
apk add --simulate <packages>
apk -U add <packages>

# opkg path
opkg update && opkg install <packages>
```

For `apk`, run `apk add --simulate` first.
If the simulation shows a `wpad-basic-*` conflict with restored `wpad-*`, ask approval to replace the basic package before installing; prefer Ethernet because Wi-Fi may reload.

If package installation fails:

- classify the failure
- treat config-critical packages as a stop condition when the related config is present
- examples: `wpad-*`, QMI, VPN/proto/service packages referenced by the backup
- report optional tools or UI packages and continue only if the core restore remains safe

If the repository does not match the flashed firmware, stop and ask the user for matching package sources or for a separate firmware decision outside this skill.

### 8) Restore config

`sysupgrade -r` restores config files, then exits. It does not flash firmware and does not reliably apply the restored runtime state.

For a normal full restore, prefer:

```sh
sysupgrade -r "$config_archive"
```

Before running restore:

- create a safety backup of the current target config if the router is still reachable
- confirm config-critical packages from the backup were installed successfully
- compare current target LAN IP/netmask with the LAN IP/netmask from the backup
- confirm the planned restored LAN override, if the backup LAN overlaps the target WAN upstream subnet
- ask for explicit approval immediately before restore
- warn if LAN IP, Wi-Fi, firewall, or SSH settings from the backup may cut the session after reboot or reload
- tell the operator to confirm SSH access after restore: use the restored root password, or in LuCI go to `System > Administration > Router Password` to set a temporary password and `System > Administration > SSH Access` to confirm Dropbear is enabled on LAN
- expect SSH host key changes when `/etc/dropbear/*_host_key` is restored; after confirming router identity, continue with a temporary `UserKnownHostsFile` or refresh the known host entry

If a restored LAN override was approved, patch restored `/etc/config/network` immediately after `sysupgrade -r` and before custom files, reboot, or service reload.
Use UCI and preserve the restored config style: `list ipaddr '<new-lan-cidr>'` for CIDR-style LANs, or `option ipaddr` + `option netmask` for netmask-style LANs.
Commit and verify `network.lan.ipaddr` and `network.lan.netmask`.
This is a safety patch after full config restore, not a partial restore path.
Do not run `/etc/init.d/network reload`, `wifi reload`, or `reboot` until the user approves the next step.
If the override fails, stop before rebooting or reloading the restored runtime state.

If full restore is unsafe, stop. Do not emulate partial restore in v1.

### 9) Restore custom files

After the config restore completes and the agent has reconnected if needed, restore the companion custom archive when `custom_archive` is not `none`.
If `custom_archive=none`, record that companion custom files were not present and skip this step.

```sh
tar -xzf "$custom_archive" -C /
```

Before extracting:

- inspect paths with `tar -tzf "$custom_archive"`
- inspect entry types with `tar -tvzf "$custom_archive"`
- reject absolute paths, `..` path segments, symlink/device entries, logs, shell history, backup archives/dumps, and paths outside the known custom-file locations
- do not reject executable scripts just because their filename contains `backup` when they are inside the known custom-file locations and pass the entry-type checks
- ask for explicit approval if the archive contains anything unexpected but still plausibly intended
- remember that custom files may include executable hotplug scripts and credentials
- if the temporary restore directory disappeared, copy or extract the bundle again before continuing

If the archive is empty, record that there were no custom files to restore.

### 10) Apply restored config

After config and custom files are restored, ask for approval to reboot the router.
Prefer a reboot over ad-hoc service reloads after a full config restore.

If restored LAN IP/netmask differs from the current target LAN, or a restored LAN override was applied, give the user a short reconnect prompt before reboot:

> The restored config changes router LAN from `{old_lan}` to `{new_lan}`.
> After reboot this agent may disconnect.
> If that happens, unplug and reconnect the operator machine Ethernet cable, or disable and re-enable the wired connection.
> Wait 1-2 minutes.
> If internet works through the target router again, return to this conversation and I will continue verification.
> If internet does not work, reconnect the operator machine directly to the upstream router and return here with the gateway/IP values you see.

Then run:

```sh
reboot
```

Stop after reboot and wait for the user or connection to return.

### 11) Verify after restore

Verify the restored state with router-side checks such as:

```sh
ubus call system board
df -h
logread | tail -n 80
uci show network
uci show firewall
wifi status | sed -E "s/(\"key\": )\"[^\"]+\"/\\1\"<redacted>\"/g"
test "$custom_archive" = none || tar -tzf "$custom_archive"
```

Use service-specific checks only when the backup contains related config.
Examples:

```sh
command -v apk >/dev/null && apk info -e <package>
command -v opkg >/dev/null && opkg list-installed | grep -E '^<package> '
logread | grep -Ei 'hostapd|netifd|error|failed' | tail -n 80
test -x /etc/hotplug.d/iface/99-auto-apn-at && echo 'Auto-APN hotplug script is executable'
```

Ask before reloads such as `/etc/init.d/network reload` or `wifi reload`.

## Failure handling

Stop and explain clearly when:

- WAN internet is unavailable
- backup and target appear incompatible
- a config-critical package cannot be installed
- SSH is lost after a network change
- a single-interface cabling handoff interrupts internet and the user has not reconnected yet

If the user wants to continue after a risk gate, restate the risk and ask for explicit approval.

## Final report

Keep the final report short and operational.
Print the report in the conversation first, then ask whether the user wants it saved to a file.
Do not write the report file unless they say yes.

Use this compact structure:

### Summary

- mode, router identity, firmware
- result: success, completed with warnings, or stopped

### Actions

- packages: installed, failed, skipped
- config: restored or not restored
- custom files/scripts: restored or not restored

### Verification

- internet, package manager, network/Wi-Fi, relevant logs

### Risks

- unresolved issues or anything likely to break after reboot

### Next steps

- reboot: done, needed, or not needed
- manual action: needed or not needed
- next safe action, if any

## Constraints

- Package restore comes before config restore; companion custom files come after config restore.
- WAN internet is required before package restore.
- Determine whether the operator machine is already connected to the target router before inferring upstream.
- Do not assume the upstream network matches the agent access network or the operator machine default route.
- Do not cut access without explicit approval.
- Do not attempt partial restore or firmware flashing.
