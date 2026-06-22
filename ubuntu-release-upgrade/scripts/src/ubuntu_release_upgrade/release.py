"""Upgrade-path gating via the Ubuntu meta-release file.

The meta-release file lists every release with a `Supported:` flag. `Supported: 1`
means upgrades to that release are open. The flag flips to 1 only after the
release is ready for upgraders (for LTS, typically around the .1 point release).
Using `do-release-upgrade -d` reaches the *development* release instead and must
never be used to reach a stable target.
"""

from __future__ import annotations

import configparser
import re
import urllib.error
import urllib.request

from ubuntu_release_upgrade import system

META_BASE = "https://changelogs.ubuntu.com/"
META_FILES = {
    "normal": "meta-release",
    "lts": "meta-release-lts",
    "normal-dev": "meta-release-development",
}
_VERSION_RE = re.compile(r"(\d+\.\d+)")


def _prompt_setting(path: str = "/etc/update-manager/release-upgrades") -> str:
    """Read the Prompt= policy (lts/normal/never). Defaults to 'normal'."""
    parser = configparser.ConfigParser()
    try:
        parser.read(path)
    except (configparser.Error, OSError):
        return "normal"
    return parser.get("DEFAULT", "Prompt", fallback="normal").strip().lower()


def _fetch(name: str, timeout: int = 15) -> str:
    url = META_BASE + name
    req = urllib.request.Request(url, headers={"User-Agent": "ubuntu-release-upgrade-skill"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https host)
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise system.NetworkError(f"Failed to fetch {url}: {exc}") from exc


def _parse_meta(text: str) -> list[dict[str, str]]:
    """Parse the RFC822-style meta-release file into a list of dist blocks."""
    blocks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            if current:
                blocks.append(current)
                current = {}
            continue
        if ":" in line and not line[0].isspace():
            key, _, value = line.partition(":")
            current[key.strip()] = value.strip()
    if current:
        blocks.append(current)
    return blocks


def _version_of(block: dict[str, str]) -> float:
    match = _VERSION_RE.search(block.get("Version", ""))
    return float(match.group(1)) if match else -1.0


def _select_target(
    dists: list[dict[str, str]], current_codename: str, target: str | None
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """Return (current_block, target_block). Target is explicit or the next release."""
    ordered = sorted(dists, key=_version_of)
    current_block = next((b for b in ordered if b.get("Dist") == current_codename), None)
    if target:
        target_block = next(
            (
                b
                for b in ordered
                if b.get("Dist") == target or b.get("Version", "").split(" ")[0] == target
            ),
            None,
        )
        return current_block, target_block
    if current_block is None:
        return None, None
    idx = ordered.index(current_block)
    target_block = ordered[idx + 1] if idx + 1 < len(ordered) else None
    return current_block, target_block


def _next_under_normal(current_codename: str) -> dict[str, str] | None:
    """The immediate next release under Prompt=normal (interim or LTS), if any."""
    try:
        dists = _parse_meta(_fetch(META_FILES["normal"]))
    except system.NetworkError:
        return None
    _, nxt = _select_target(dists, current_codename, None)
    return nxt


def _interim_alternative(
    prompt: str, current_codename: str, lts_target: dict[str, str] | None
) -> dict[str, object] | None:
    """Under Prompt=lts, surface an interim release that lts would skip."""
    if prompt != "lts":
        return None
    nxt = _next_under_normal(current_codename)
    if not nxt or (lts_target and nxt.get("Dist") == lts_target.get("Dist")):
        return None
    return {
        "codename": nxt.get("Dist", ""),
        "version": nxt.get("Version", ""),
        "path_open": nxt.get("Supported", "0") == "1",
    }


def _dev_only(target: str | None, target_block: dict[str, str] | None) -> bool:
    """True if the target exists only in the development meta-release (needs -d)."""
    if target_block is not None:
        return False
    try:
        dev = _parse_meta(_fetch(META_FILES["normal-dev"]))
    except system.NetworkError:
        return False
    if target:
        return any(b.get("Dist") == target for b in dev)
    return False


def check_path(target: str | None = None) -> dict[str, object]:
    """Detect current/target release and whether the upgrade path is open."""
    osr = system.read_os_release()
    current_codename = osr.get("UBUNTU_CODENAME") or osr.get("VERSION_CODENAME", "")
    prompt = _prompt_setting()
    meta_name = META_FILES["lts"] if prompt == "lts" else META_FILES["normal"]

    dists = _parse_meta(_fetch(meta_name))
    if (
        not any(b.get("Dist") == current_codename for b in dists)
        and meta_name != META_FILES["normal"]
    ):
        meta_name = META_FILES["normal"]
        dists = _parse_meta(_fetch(meta_name))

    if not dists:
        raise system.HelperError(
            f"meta-release ({meta_name}) parsed to zero entries; its format may have changed. "
            f"Verify the upgrade path manually before proceeding."
        )
    current_found = any(b.get("Dist") == current_codename for b in dists)

    current_block, target_block = _select_target(dists, current_codename, target)
    supported = bool(target_block) and target_block.get("Supported", "0") == "1"
    dev_only = _dev_only(target, target_block)
    interim = _interim_alternative(prompt, current_codename, target_block) if not target else None
    advice = _advice(supported, dev_only, target_block, interim, current_found)
    if prompt == "never":
        advice = (
            "Prompt=never: do-release-upgrade will not offer an upgrade. Set Prompt=normal "
            "(any release) or Prompt=lts (LTS only) in /etc/update-manager/release-upgrades "
            "first. " + advice
        )

    return {
        "flavor": system.detect_flavor(osr),
        "prompt_policy": prompt,
        "meta_file": meta_name,
        "from": {
            "codename": current_codename,
            "version": osr.get("VERSION_ID", ""),
            "name": current_block.get("Name", "") if current_block else "",
        },
        "to": {
            "codename": target_block.get("Dist", "") if target_block else (target or ""),
            "version": target_block.get("Version", "") if target_block else "",
            "name": target_block.get("Name", "") if target_block else "",
        },
        "path_open": supported and current_found,
        "development_only": dev_only,
        "current_release_found": current_found,
        "interim_alternative": interim,
        "advice": advice,
    }


def _advice(
    supported: bool,
    dev_only: bool,
    target_block: dict[str, str] | None,
    interim: dict[str, object] | None,
    current_found: bool,
) -> str:
    if not current_found:
        return (
            "Current release was not found in the meta-release file. The format may have "
            "changed or this is an unsupported release. Verify the upgrade path manually."
        )
    base = _base_advice(supported, dev_only, target_block)
    if interim:
        state = "available now" if interim["path_open"] else "not open yet"
        base += (
            f" Note: Prompt=lts skips interim releases; {interim['codename']} "
            f"{interim['version']} is {state} under Prompt=normal (interim targeting is the "
            f"Prompt= setting, NOT -d)."
        )
    return base


def _base_advice(supported: bool, dev_only: bool, target_block: dict[str, str] | None) -> str:
    if supported:
        return "Path is OPEN. Run `do-release-upgrade` (NEVER -d). Confirm your backup first."
    if dev_only:
        return (
            "Target exists only as a development release. Do NOT use -d to reach a stable "
            "target: -d upgrades to the unreleased devel series. Wait for Supported: 1."
        )
    if target_block is None:
        return "No next release found in the meta-release file yet. Wait and re-check."
    return "Path is CLOSED (Supported: 0). Wait until the flag flips; do NOT force with -d."
