"""Project context collection: README, manifests, changelog, directory listing."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from change_summary.models import ChangeSummaryConfig, ProjectContext


def collect_project_context(repo_root: Path) -> ProjectContext:
    """Gather lightweight project context (~600 tokens)."""
    ctx = ProjectContext()
    ctx.name, ctx.description = _read_manifest(repo_root)
    ctx.readme_excerpt = _read_first_lines(repo_root / "README.md", 50)
    ctx.agents_excerpt = _read_first_lines(repo_root / "AGENTS.md", 50) or _read_first_lines(
        repo_root / "CLAUDE.md", 50
    )
    ctx.previous_changelog_entry = _read_last_changelog_entries(repo_root, count=3)
    ctx.top_dirs = _list_top_dirs(repo_root)
    return ctx


def _read_first_lines(path: Path, n: int) -> str | None:
    """Read the first n lines of a file, or None if missing."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.splitlines()[:n]
    result = "\n".join(lines).strip()
    return result or None


def _read_manifest(repo_root: Path) -> tuple[str | None, str | None]:
    """Extract project name and description from manifest files."""
    # package.json
    pj = repo_root / "package.json"
    if pj.is_file():
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            return data.get("name"), data.get("description")
        except (json.JSONDecodeError, OSError):
            pass

    # pyproject.toml (minimal parser, no toml dependency)
    pp = repo_root / "pyproject.toml"
    if pp.is_file():
        name, desc = _parse_pyproject_toml(pp)
        if name:
            return name, desc

    # Cargo.toml (same minimal parsing)
    cargo = repo_root / "Cargo.toml"
    if cargo.is_file():
        name, desc = _parse_cargo_toml(cargo)
        if name:
            return name, desc

    # CMakeLists.txt project()
    cmake = repo_root / "CMakeLists.txt"
    if cmake.is_file():
        name = _parse_cmake_project(cmake)
        if name:
            return name, None

    # Fallback: repo directory name
    return repo_root.resolve().name, None


def _parse_pyproject_toml(path: Path) -> tuple[str | None, str | None]:
    """Minimal TOML parser for name/description from pyproject.toml."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, None
    name = _toml_value(text, "name")
    desc = _toml_value(text, "description")
    return name, desc


def _parse_cargo_toml(path: Path) -> tuple[str | None, str | None]:
    """Minimal TOML parser for name/description from Cargo.toml."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, None
    name = _toml_value(text, "name")
    desc = _toml_value(text, "description")
    return name, desc


def _toml_value(text: str, key: str) -> str | None:
    """Extract a string value for a key from TOML text (simple cases)."""
    pattern = rf'^\s*{re.escape(key)}\s*=\s*"([^"]*)"'
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def _parse_cmake_project(path: Path) -> str | None:
    """Extract project name from CMakeLists.txt project() call."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"project\s*\(\s*(\w+)", text, re.IGNORECASE)
    return match.group(1) if match else None


def _read_last_changelog_entries(repo_root: Path, count: int = 3) -> str | None:
    """Parse the last N ## [X.Y.Z] sections from CHANGELOG.md.

    Multiple entries give the LLM a better sense of voice, style, and detail level.
    """
    changelog = repo_root / "CHANGELOG.md"
    if not changelog.is_file():
        return None
    try:
        text = changelog.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Find all ## [version] headings (skip ## [Unreleased])
    heading_pattern = re.compile(r"^## \[\d.+?\]", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))
    if not matches:
        return None

    # Take up to `count` sections
    take = min(count, len(matches))
    start = matches[0].start()
    end = matches[take].start() if take < len(matches) else len(text)
    section = text[start:end].strip()
    # Cap at ~60 lines to keep token budget
    lines = section.splitlines()[:60]
    return "\n".join(lines)


def _list_top_dirs(repo_root: Path) -> list[str]:
    """List top-level directories (excluding hidden)."""
    try:
        dirs = sorted(
            d.name + "/" for d in repo_root.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
    except OSError:
        return []
    return dirs


def parse_change_summary_config(repo_root: Path) -> ChangeSummaryConfig:
    """Parse submodule handling config from AGENTS.md ## change-summary section.

    Looks for a fenced YAML block under ## change-summary with:
        submodules:
          ignore:
            - path/to/submodule
          summarize:
            - another/submodule
    """
    config = ChangeSummaryConfig()
    agents_md = repo_root / "AGENTS.md"
    if not agents_md.is_file():
        return config

    try:
        text = agents_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return config

    section = _extract_md_section(text, "change-summary")
    if not section:
        return config

    yaml_text = _extract_yaml_block(section)
    if not yaml_text:
        return config

    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return config

    if not isinstance(data, dict):
        return config

    submods = data.get("submodules", {})
    if not isinstance(submods, dict):
        return config

    for key, target in [("ignore", "ignore"), ("summarize", "summarize")]:
        val = submods.get(key, [])
        if isinstance(val, list):
            setattr(config, target, [str(v) for v in val])

    return config


def _extract_md_section(text: str, heading: str) -> str | None:
    """Extract content under a ## heading until the next ## heading."""
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    if next_heading:
        return text[start : start + next_heading.start()]
    return text[start:]


def _extract_yaml_block(section: str) -> str | None:
    """Extract the first fenced YAML code block from a markdown section."""
    match = re.search(r"```ya?ml\s*\n(.*?)```", section, re.DOTALL)
    return match.group(1) if match else None
