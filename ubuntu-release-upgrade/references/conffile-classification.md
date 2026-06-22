# Conffile prompt classification

During the upgrade, dpkg pauses on config files that changed both on disk and in
the new package. The prompt offers:

- `Y` / `I` - install the package maintainer's version (overwrites your file)
- `N` / `O` - keep your currently-installed version (default)
- `D` - show the diff between the two
- `Z` - drop to a shell to inspect manually

The decision hinges on one question: **did you edit this file?**

## How to decide

The agent runs the classifier (read-only) on the path dpkg names in the prompt, using the
invocation from SKILL.md "How this works":

```bash
uv run --project <skill-dir>/scripts ubuntu-release-upgrade classify-conffile /etc/PATH
```

It compares the on-disk md5 against the md5 dpkg recorded for the installed
package (`/var/lib/dpkg/status`). The result drives the call:

| `user_modified` | Meaning | Recommendation |
|-----------------|---------|----------------|
| `false` | You never touched it; only the maintainer changed it | Take maintainer's version (`Y`) |
| `null` | dpkg's record could not be read | KEEP yours (`N`); review the diff (`D`) |
| `true`, comments only | You edited it, but the diff is comments | Likely `Y`; view diff (`D`) first |
| `true`, real changes | You have meaningful local edits | KEEP yours (`N`), or `D` then merge |

Most conffiles are world-readable, so the agent runs the classifier itself. If a file is
root-only (e.g. `0600`) the classifier exits 3; the user re-runs it with sudo. Because uv
is user-installed and not in root's PATH, pass uv's absolute path:

```bash
sudo "$(command -v uv)" run --project <skill-dir>/scripts ubuntu-release-upgrade classify-conffile /etc/PATH
```

(This runs uv as root, using root's cache; harmless for a one-off read.)

## Safe default

When unsure, choose `N` (keep your version). Keeping is reversible: the new
version is saved alongside as `*.dpkg-new`, so you can merge later. Overwriting a
file you customized is destructive and silent.

## Worked examples

- `apparmor.d/*` profiles you never edited -> `user_modified: false` -> `Y`. These
  are maintainer-shipped security profiles; the new version usually fixes denials.
- A daemon config you customized (e.g. virtualization, networking, mounts) ->
  `user_modified: true` with real changes -> `N`, then re-apply maintainer changes
  by hand if any matter.
- `updatedb.conf`, ABI lists, and similar maintainer-managed files you never
  touched -> `Y`.

## What NEVER to do

- Do NOT blanket-answer every prompt with `Y` ("just take new") - it wipes your
  customizations (firewall rules, daemon tuning, mount options).
- Do NOT blanket-answer `N` either - you can miss security-relevant maintainer
  updates to files you never edited.
- Decide per file, using the classifier.
