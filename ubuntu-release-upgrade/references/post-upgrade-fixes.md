# Post-upgrade fixes

Catalog of fixes for common breakage after `do-release-upgrade`. Apply only what
matches the system (flavor, desktop, installed tools). All sudo commands are for
the USER to run; the agent inspects and explains, it does not run sudo.

## 1. Third-party repositories

`do-release-upgrade` disables third-party repos and does not migrate their codename
suites. After the upgrade:

1. For each repo you want back, verify the new codename suite EXISTS before enabling
   it (the inventory probe reports `target_available`). Enabling a suite the vendor
   has not published yet breaks `apt update`.
2. Migrate the suite from the old to the new codename:
   - one-line `.list`: change the codename token, re-enable the line.
   - deb822 `.sources`: set `Suites:` to the new codename and `Enabled: yes`.
   - re-enable a disabled file by renaming `*.list.disabled` -> `*.list` (or flipping
     `Enabled:` in `.sources`).
3. Leave purged PPAs (e.g. a backports PPA you reverted with `ppa-purge`) DISABLED.
4. `sudo apt update` and resolve every error before moving on.

Benign notices to ignore: "Skipping acquire of configured file ... i386" when a
repo does not ship i386 - harmless. Duplicate-source warnings mean the same repo is
listed twice (e.g. in both `sources.list` and a `.sources` file); remove one.

## 2. KDE / Plasma (only on KDE)

### SDDM session

A new SDDM config can drop the X11 session or reset the default. If login only
offers Wayland (or the wrong default), check the drop-ins under
`/etc/sddm.conf.d/` for a session lock and adjust.

### Carried-over desktop config

After a big Plasma version jump, config carried over from the old release can misbehave
(panels, theme, widgets, shortcuts). After the first login, check that the desktop works as
expected and reconfigure anything that looks off. No need to wipe `~/.config` up front -
just verify and fix what actually broke.

## 3. DKMS / kernel

The upgrade installs a new kernel and rebuilds DKMS modules against it. Verify:

```bash
dkms status
```

Every module should show `installed` for the new kernel. If one failed to build,
it likely needs a newer module release that supports the new kernel series (check
the project's required-kernel range). On Secure Boot, a rebuilt module must be
re-signed; enroll the MOK if prompted at the next boot.

## 4. Audio / PipeWire

A brief audio dropout or a one-time PipeWire/WirePlumber restart crash during the
package swap is benign. After reboot, confirm playback and inputs. If a device is
missing, restart the user services:

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

## 5. Final autoremove

Only after marking the protect list `manual` (see the runbook hazards), simulate first, then
clean up:

```bash
apt-get autoremove --purge -s     # preview - the orphan set differs post-upgrade
sudo apt autoremove --purge
```

Re-check the list it proposes; nothing you rely on should be there.

## 6. Verification checklist

- `lsb_release -a` shows the new release
- `apt-get check` and `sudo dpkg --audit` are clean
- GPU/display correct, passthrough/SR-IOV works if used
- VMs / containers start
- Snaps (`snap refresh`) and Flatpaks (`flatpak update`) current if used
