"""Inventory APT sources and check whether third-party repos support the target.

Handles one-line (.list) and deb822 (.sources) formats, plus their .disabled
variants. For entries whose suite is the current codename, optionally probes
whether the target codename's Release file exists, so the agent never migrates a
suite to a codename the repo does not publish yet.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from glob import glob
from pathlib import Path

from ubuntu_release_upgrade import system

GENERIC_SUITES = {
    "stable",
    "testing",
    "unstable",
    "any",
    "all",
    "main",
    "release",
    "latest",
    "production",
}
_LIST_RE = re.compile(
    r"^(?P<comment>#\s*)?(?P<type>deb(?:-src)?)\s+(?:\[(?P<opts>[^\]]*)\]\s+)?"
    r"(?P<uri>\S+)\s+(?P<suite>\S+)\s+(?P<components>.+)$"
)


def inventory(target_codename: str | None = None, probe: bool = True) -> dict[str, object]:
    """Inventory all APT sources; classify each and optionally probe the target."""
    current_codename = system.read_os_release().get("UBUNTU_CODENAME", "")
    files = ["/etc/apt/sources.list", *sorted(glob("/etc/apt/sources.list.d/*"))]
    entries: list[dict[str, object]] = []
    warnings: list[str] = []
    for path in files:
        p = Path(path)
        if not p.is_file():
            continue
        if path.endswith((".list", ".list.disabled")) or p.name == "sources.list":
            parsed = _parse_list(path, current_codename)
        elif path.endswith((".sources", ".sources.disabled")):
            parsed = _parse_sources(path, current_codename)
        else:
            continue
        if not parsed and _looks_nonempty(path):
            warnings.append(f"{path}: has source entries but none parsed (format may have changed)")
        entries.extend(parsed)

    if probe and target_codename:
        for entry in entries:
            if entry["kind"] == "codename":
                entry["target_available"] = _probe(str(entry["uri"]), target_codename)

    return {
        "current_codename": current_codename,
        "target_codename": target_codename,
        "entries": entries,
        "warnings": warnings,
    }


def _looks_nonempty(path: str) -> bool:
    """True if the file has lines that look like source entries (deb / Types:)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return bool(re.search(r"(?mi)^\s*#?\s*(deb(-src)?\s|Types:)", text))


def _is_official(uri: str) -> bool:
    """True for Ubuntu's own archives (managed by do-release-upgrade itself)."""
    match = re.search(r"https?://([^/\s]+)", uri)
    host = match.group(1) if match else ""
    return host == "ubuntu.com" or host.endswith(".ubuntu.com")


def _classify_entry(uri: str, suite: str, current_codename: str) -> str:
    if _is_official(uri):
        return "official"
    if suite == current_codename:
        return "codename"
    if suite in GENERIC_SUITES:
        return "generic"
    if re.fullmatch(r"[a-z]+", suite):
        return "codename-other"
    return "other"


def _parse_list(path: str, current_codename: str) -> list[dict[str, object]]:
    file_disabled = path.endswith(".disabled")
    out: list[dict[str, object]] = []
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        match = _LIST_RE.match(line.strip())
        if not match:
            continue
        commented = bool(match.group("comment"))
        suite = match.group("suite")
        out.append(
            {
                "file": path,
                "format": "list",
                "type": match.group("type"),
                "uri": match.group("uri"),
                "suite": suite,
                "enabled": not file_disabled and not commented,
                "kind": _classify_entry(match.group("uri"), suite, current_codename),
            }
        )
    return out


def _parse_sources(path: str, current_codename: str) -> list[dict[str, object]]:
    file_disabled = path.endswith(".disabled")
    out: list[dict[str, object]] = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for block in re.split(r"\n\s*\n", text):
        fields = _deb822_fields(block)
        if "uris" not in fields or "suites" not in fields:
            continue
        block_enabled = fields.get("enabled", "yes").lower() not in ("no", "false")
        for uri in fields["uris"].split():
            for suite in fields["suites"].split():
                out.append(
                    {
                        "file": path,
                        "format": "sources",
                        "type": fields.get("types", "deb"),
                        "uri": uri,
                        "suite": suite,
                        "enabled": not file_disabled and block_enabled,
                        "kind": _classify_entry(uri, suite, current_codename),
                    }
                )
    return out


def _deb822_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line and not line[0].isspace():
            key, _, value = line.partition(":")
            fields[key.strip().lower()] = value.strip()
    return fields


def _probe(uri: str, codename: str, timeout: int = 10) -> bool | None:
    """Return True/False if the target Release file exists, None on network error."""
    url = f"{uri.rstrip('/')}/dists/{codename}/Release"
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "ubuntu-release-upgrade-skill"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status == 200
    except urllib.error.HTTPError:
        return False  # non-2xx (e.g. 404) = suite not published for this codename
    except (urllib.error.URLError, OSError, TimeoutError):
        return None
