"""File categorization by path and extension."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

# ---------------------------------------------------------------------------
# File categorization constants and patterns
# ---------------------------------------------------------------------------

SOURCE_EXTENSIONS = frozenset(
    {
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".cxx",
        ".py",
        ".pyx",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".scala",
        ".cs",
        ".swift",
        ".rb",
        ".php",
        ".lua",
        ".zig",
        ".asm",
        ".s",
    }
)

SOURCE_DIRS = frozenset({"src", "lib", "app", "pkg", "cmd", "internal", "source"})

_TEST_PATTERNS = re.compile(r"(^tests?/|_test\.|\.test\.|\.spec\.|_spec\.)", re.IGNORECASE)

DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt", ".adoc"})

CONFIG_EXTENSIONS = frozenset({".yml", ".yaml", ".json", ".toml", ".ini", ".cfg"})

_CI_PATTERNS = re.compile(
    r"(^\.github/|^\.gitlab-ci|^\.circleci/|^Makefile$|^makefile$"
    r"|^GNUmakefile$|^CMakeLists\.txt$|^Dockerfile|^Jenkinsfile"
    r"|^\.travis\.yml$|^Taskfile|^justfile$)",
    re.IGNORECASE,
)

_DEPS_PATTERNS = re.compile(
    r"(lock\b|\.lock$|^requirements.*\.txt$|^go\.sum$|^Cargo\.lock$"
    r"|^Gemfile\.lock$|^yarn\.lock$|^pnpm-lock|^package-lock)",
    re.IGNORECASE,
)

ASSET_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".bmp",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
    }
)

ASSET_DIRS = frozenset({"fonts", "images", "icons", "assets"})


def categorize_file(filepath: str) -> str:
    """Categorize a file by its path and extension.

    Returns one of: source, test, docs, config, ci, deps, assets, other.
    """
    p = PurePosixPath(filepath)
    ext = p.suffix.lower()
    parts = p.parts
    name = p.name

    # Test (check before source, test files may live in src/)
    if _TEST_PATTERNS.search(filepath):
        return "test"

    # CI/CD
    if _CI_PATTERNS.search(filepath):
        return "ci"

    # Dependencies (lock files, requirements)
    if _DEPS_PATTERNS.search(name):
        return "deps"

    # Assets (check before source: asset extensions win over source directories)
    if ext in ASSET_EXTENSIONS:
        return "assets"
    if any(p in ASSET_DIRS for p in parts):
        return "assets"

    # Source code
    if ext in SOURCE_EXTENSIONS:
        return "source"
    if parts and parts[0] in SOURCE_DIRS:
        return "source"

    # Docs
    if ext in DOC_EXTENSIONS:
        return "docs"
    if parts and parts[0] == "docs":
        return "docs"
    if name.upper().startswith("README"):
        return "docs"

    # Config (root-level only: depth 1)
    if ext in CONFIG_EXTENSIONS and len(parts) == 1:
        return "config"

    return "other"
