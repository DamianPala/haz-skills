"""Classify a pending dpkg conffile prompt: maintainer-only vs. user-modified.

dpkg prompts when a config file changed on disk AND the package ships a new
version. The safe decision hinges on whether YOU edited the file. dpkg records
the md5 of the file as shipped by the installed version in /var/lib/dpkg/status;
if the on-disk md5 still matches, you never edited it, so taking the maintainer's
version (Y) is safe. If it differs, you have local edits worth keeping (N) or
merging (D). Overwriting is destructive, so the default leans to keeping.
"""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

from ubuntu_release_upgrade import system

_NEW_SUFFIXES = (".dpkg-new", ".dpkg-dist", ".ucf-dist")
_PREVIEW_LINES = 60


def classify(path: str) -> dict[str, object]:
    """Classify the pending conffile change for `path`."""
    new_file = _find_incoming(path)
    if new_file is None:
        raise system.NotApplicableError(f"No pending conffile change found for {path}")

    current = system.read_text_or_denied(path)
    incoming = system.read_text_or_denied(new_file)
    stored_md5 = _stored_md5(path)
    # dpkg records the md5 of the raw bytes, so hash bytes (not re-encoded text).
    current_md5 = hashlib.md5(Path(path).read_bytes()).hexdigest()  # noqa: S324
    user_modified = (stored_md5 != current_md5) if stored_md5 else None

    diff = list(
        difflib.unified_diff(
            current.splitlines(),
            incoming.splitlines(),
            fromfile="current",
            tofile="incoming",
            lineterm="",
        )
    )
    comments_only = _changes_comments_only(diff)

    return {
        "path": path,
        "incoming_file": new_file,
        "stored_md5_known": bool(stored_md5),
        "user_modified": user_modified,
        "changes_comments_only": comments_only,
        "diff_line_count": sum(
            1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---"))
        ),
        "recommendation": _recommend(user_modified, comments_only),
        "diff_preview": diff[:_PREVIEW_LINES],
    }


def _find_incoming(path: str) -> str | None:
    for suffix in _NEW_SUFFIXES:
        candidate = path + suffix
        if Path(candidate).is_file():
            return candidate
    return None


def _stored_md5(path: str, status: str = "/var/lib/dpkg/status") -> str | None:
    """Return the md5 dpkg recorded for this conffile in the installed package."""
    try:
        lines = Path(status).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    in_conffiles = False
    for line in lines:
        if line.startswith("Conffiles:"):
            in_conffiles = True
            continue
        if in_conffiles:
            if not line.startswith(" "):
                in_conffiles = False
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] == path:
                return parts[1]
    return None


def _changes_comments_only(diff: list[str]) -> bool:
    changed = [
        line for line in diff if line and line[0] in "+-" and not line.startswith(("+++", "---"))
    ]
    if not changed:
        return True
    for line in changed:
        body = line[1:].strip()
        if body and not body.startswith("#"):
            return False
    return True


def _recommend(user_modified: bool | None, comments_only: bool) -> str:
    if user_modified is None:
        return (
            "Could not read dpkg's record of this file; default to KEEPING your version (N) "
            "and review the diff (D)."
        )
    if user_modified is False:
        return "Install the maintainer's version (Y): you never edited this file."
    if comments_only:
        return "Probably safe to take the new version (Y); changes look like comments. Review (D) first."
    return "KEEP your version (N), or view the diff (D) and merge: you have local edits."
