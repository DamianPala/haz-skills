"""File filtering: skip lock files and generated code. Flag binaries for LLM."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_LOCK_FILE_PATTERNS = re.compile(
    r"(lock\b|\.lock$|^package-lock\.json$|^yarn\.lock$|^Cargo\.lock$"
    r"|^poetry\.lock$|^go\.sum$|^pnpm-lock\.yaml$)",
    re.IGNORECASE,
)

_GENERATED_PATTERNS = re.compile(
    r"(\.min\.js$|\.min\.css$|\.generated\.|\.pb\.go$|_generated\.go$)",
    re.IGNORECASE,
)

# Extensions that are text-encoded binary data. These files can be huge
# (thousands of lines of hex) but their diffs have zero analytical value.
# Treated as binary: shown as a marker, not as full diff content.
_BINARY_LIKE_EXTENSIONS = frozenset(
    {
        ".hex",
        ".ihex",
        ".srec",
        ".s19",
        ".s28",
        ".s37",
        ".bin",
        ".elf",
        ".axf",
    }
)


def classify_skippable_by_path(path: str) -> str | None:
    """Return skip reason based on path alone, or None to keep it."""
    name = PurePosixPath(path).name

    if _LOCK_FILE_PATTERNS.search(name):
        return "lock file"

    if _GENERATED_PATTERNS.search(path):
        return "generated"

    return None


def is_binary_path(path: str, file_diffs: dict[str, str]) -> bool:
    """Detect if a file is binary based on path and diff content."""
    ext = PurePosixPath(path).suffix.lower()
    if ext in _BINARY_LIKE_EXTENSIONS:
        return True

    # If path is in file_diffs, it has text content (not binary)
    return False
