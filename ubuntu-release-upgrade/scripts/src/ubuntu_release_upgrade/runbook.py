"""Generate (or locate) the stateful upgrade runbook.

Collects every read-only finding, renders the runbook template, and writes it to
the state path. The runbook is the source of truth across the mid-upgrade reboot:
it carries the reference info, the hazard plan, phase progress checkboxes, and the
decision log. An existing runbook is never clobbered (it holds progress); use
--force only to regenerate from scratch.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ubuntu_release_upgrade import release, repos, system

_TEMPLATE_DIR = Path(__file__).parents[3] / "references" / "templates"
_TEMPLATE_NAME = "runbook.md.j2"


def _state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "ubuntu-release-upgrade"


def _default_out(from_codename: str, to_codename: str) -> Path:
    name = f"runbook-{from_codename or 'current'}-to-{to_codename or 'next'}.md"
    return _state_dir() / name


def generate(
    target: str | None = None,
    out: str | None = None,
    force: bool = False,
    probe: bool = True,
) -> dict[str, object]:
    """Collect deterministic findings and render the runbook. Returns status + path."""
    path_info = release.check_path(target)
    from_cn = str(path_info["from"]["codename"])  # type: ignore[index]
    to_cn = str(path_info["to"]["codename"])  # type: ignore[index]
    out_path = Path(out) if out else _default_out(from_cn, to_cn)

    if out_path.exists() and not force:
        return {"status": "exists", "path": str(out_path), "hint": "use --force to regenerate"}

    context = {
        "generated": datetime.date.today().isoformat(),
        "flavor": path_info.get("flavor", ""),
        "desktop": system.detect_desktop(),
        "path": path_info,
        "repos": repos.inventory(to_cn or None, probe=probe),
    }
    rendered = _render(context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    return {"status": "created", "path": str(out_path)}


def _render(context: dict[str, object]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=(), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env.get_template(_TEMPLATE_NAME).render(**context)
