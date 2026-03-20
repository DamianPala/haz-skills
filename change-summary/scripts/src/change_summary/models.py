"""Shared data structures used across the change-summary pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChangeSummaryConfig:
    """Per-repo submodule handling config from AGENTS.md."""

    ignore: list[str] = field(default_factory=list)
    summarize: list[str] = field(default_factory=list)


@dataclass
class FileChange:
    path: str
    status: str  # added, modified, deleted, renamed
    category: str  # source, test, docs, config, ci, deps, assets, other
    lines_added: int = 0
    lines_removed: int = 0
    likely_type: str = ""  # unused in v2, kept for dataclass compat


@dataclass
class ProjectContext:
    name: str | None = None
    description: str | None = None
    readme_excerpt: str | None = None
    previous_changelog_entry: str | None = None
    top_dirs: list[str] = field(default_factory=list)
    agents_excerpt: str | None = None


@dataclass
class SkippedFile:
    path: str
    category: str
    reason: str  # "lock file", "binary", "generated"
