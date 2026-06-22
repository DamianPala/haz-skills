"""Shared low-level system helpers: detection and file reads.

All read-only. No sudo, no mutation. Typed errors map to CLI exit codes.
"""

from __future__ import annotations

import os
from pathlib import Path


class HelperError(Exception):
    """Base for helper errors that map to a non-zero CLI exit code."""

    exit_code = 1


class NetworkError(HelperError):
    """A required network fetch failed (meta-release, repo probe)."""

    exit_code = 2


class PermissionDeniedError(HelperError):
    """A file could not be read; the user must re-run with sudo."""

    exit_code = 3


class NotApplicableError(HelperError):
    """The requested inspection does not apply (e.g. no pending conffile)."""

    exit_code = 1


def read_os_release(path: str = "/etc/os-release") -> dict[str, str]:
    """Parse an os-release file into a dict (values unquoted)."""
    data: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return data
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def detect_flavor(osr: dict[str, str] | None = None) -> str:
    """Best-effort Ubuntu flavor name (e.g. 'kubuntu', 'ubuntu')."""
    osr = osr if osr is not None else read_os_release()
    variant = (osr.get("VARIANT_ID") or "").lower()
    if variant:
        return variant
    # Fall back to installed desktop sessions.
    if _has_session("plasma"):
        return "kubuntu"
    return (osr.get("ID") or "ubuntu").lower()


def _has_session(marker: str) -> bool:
    sessions = Path("/usr/share/xsessions")
    wayland = Path("/usr/share/wayland-sessions")
    for folder in (sessions, wayland):
        if folder.is_dir() and any(
            marker.split("-")[0] in p.name.lower() for p in folder.iterdir()
        ):
            return True
    return False


def detect_desktop() -> str:
    """Detect the desktop environment family: 'kde', 'gnome', or 'other'."""
    hints = " ".join(
        os.environ.get(var, "")
        for var in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_DESKTOP")
    ).lower()
    if "kde" in hints or "plasma" in hints:
        return "kde"
    if "gnome" in hints:
        return "gnome"
    # Environment may be empty (non-graphical agent session): probe installed sessions.
    if _has_session("plasma"):
        return "kde"
    if _has_session("gnome"):
        return "gnome"
    return "other"


def read_text_or_denied(path: str | Path) -> str:
    """Read a text file, raising PermissionDeniedError on permission failure."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except PermissionError as exc:
        raise PermissionDeniedError(f"Permission denied reading {path}; re-run with sudo") from exc
