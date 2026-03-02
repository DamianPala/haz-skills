---
name: python-app-uv
description: General-purpose Python apps (CLI tools, services, libraries, scripts, automation) for Ubuntu >= 22.04 and Python >= 3.12. Uses uv for scaffolding, project management, builds, and dependency resolution. Use for templates, project structure, implementation, refactors, or best-practice setup.
---

# Model-agnostic guidance

- Keep instructions clear across models.
- Avoid model-specific jargon unless required.

## OpenAI-specific check

- Verify web search access before claiming up-to-date info.

# Generic Python App Creation

Use this skill to design and implement Python apps with a clean, editable structure.

Scope and targets:
- OS: Ubuntu >= 22.04
- Python: >= 3.12
- App types: CLI, library, service, automation
- Toolchain: uv (scaffolding, dependency management, builds, running)
- Priorities: clarity, maintainability, minimal dependencies

## Compatibility and features

- Target Python 3.12 compatibility.
- Use the newest language features and stdlib capabilities available in Python 3.12.
- Avoid features introduced after 3.12 unless the user explicitly opts in to a higher minimum.
- Avoid deprecated features and backward-compatibility shims for unsupported Python versions (e.g., unnecessary `__future__` imports) unless the user explicitly requests them.

## Quick workflow

- Clarify app type and goal.
- Define scope: MVP features, out-of-scope items, expected users.
- Choose structure: single-file, small package, or service layout.
- For mini-package/package: run `uv init --package <name>` to scaffold, then wire the CLI manually in `src/<app>/cli.py` plus `[project.scripts]`.
- After scaffolding, update `pyproject.toml` with dependency groups, tool configs from `references/pyproject-snippets.md` when relevant to the request.
- Define interfaces: CLI args, public API functions, config, env vars.
- Implement core logic with logging and validation; add tests if requested.
- Provide run/usage instructions using `uv run`.

## System requirements check (before building)

- Confirm Ubuntu and Python >= 3.12 are available.
- Ensure `uv` is installed and on PATH (`uv --version`, expect >= 0.10).
- If any requirement is missing, stop and ask the user how to proceed.

## Pre-build questions (ask only if not already answered)

Ask the minimum set of questions needed to start. Skip anything already specified by the user.

- Propose 3-5 app names based on the goal, then ask which name to use.
- App purpose and main tasks?
- App type: CLI, library, service, automation?
- Inputs: sources, formats, examples?
- Outputs: destinations, formats, examples?
- Dependencies: stdlib-only or allowed third-party libs?
- Execution model: one-shot, scheduled, long-running?
- Need a draft/prototype before full build?
- Non-functional needs: performance, security, logging verbosity?
- Deliverables: files, tests, docs, run instructions?

## Implementation defaults

- Prefer minimal dependencies.
- Use `argparse` for CLI, `logging` for logs, `pathlib` for paths.
- Keep modules small and focused.
- Add `--help` and clear error messages.
- Return non-zero exit codes on failure for CLI apps.
- For mini-package/package: scaffold with `uv init --package`, then build inside that structure. Add necessary modules as needed.
- Run the app with `uv run <app>`, run tests with `uv run pytest`.
- For distribution: `uv build` to create sdist/wheel, `uv publish` to upload to PyPI.
- For global CLI install (like pipx): `uv tool install .` from the project directory, or `uv tool install <package>` from PyPI.
- Use `[dependency-groups]` (PEP 735) for dev/test tools instead of `[project.optional-dependencies]` or tool-specific env configs. See `references/pyproject-snippets.md`.
- For Click CLIs, copy `references/_completion.py` into the package and call `add_completion_command(cli, '<app-name>')`. This adds a `generate-completion` subcommand that outputs completion scripts to stdout, with `--install` to auto-install to the correct OS path.
- For script layout CLIs using `argparse`, enable argcomplete by default (unless user opts out): add `# PYTHON_ARGCOMPLETE_OK` before imports, add a safe `argcomplete` import after imports, and call `argcomplete.autocomplete(parser)` after building the parser.

## Project layouts

script:

- Single file only (e.g., `app.py`).
- Include a shebang on the first line (use `#!/usr/bin/env python`).
- Stdlib-only; no external dependencies.
- If using `argparse`, wire argcomplete completions; it is optional and only activates if `argcomplete` is installed.

mini-package:

- Scaffold with `uv init --package <name>`.
- `pyproject.toml` (uv_build backend, dependency groups)
- `src/<app>/__init__.py`
- `src/<app>/cli.py`
- `README.md`
- Use `click` for CLI entrypoints.
- Add Click as dependency: `uv add click`.
- Add dev tools via dependency groups: `uv add --group dev ruff mypy pytest pytest-cov`.
- Configure `pyproject.toml` according to `references/pyproject-snippets.md` and apply only the relevant blocks.
- Run the app and tests via `uv run`.

package:

- Scaffold with `uv init --package <name>`.
- `pyproject.toml` (uv_build backend, dependency groups)
- `src/<app>/__init__.py`
- `src/<app>/cli.py` (only if the app exposes a CLI)
- `src/<app>/core.py` (core logic; can be renamed if a domain-specific module fits better)
- Optional modules as needed (e.g., `config.py`, `service.py`).
- `tests/` (only if requested)
- `README.md`
- Configure `pyproject.toml` according to `references/pyproject-snippets.md` and apply only the relevant blocks.
- Run the app and tests via `uv run`.

## Config pattern

- CLI flags override config file values.
- Config file optional; support JSON/YAML/TOML if requested.
- Environment variables optional and documented when used.

## Logging and errors

- INFO for high-level progress, DEBUG for details.
- Log to stdout by default; allow file logging if requested.
- Catch exceptions at top-level; surface helpful messages.
- Use f-strings for all logging messages (no %-style formatting).

## README structure (mini-package and package layouts)

Generate a `README.md` with these sections. Skip sections that don't apply (e.g., no "Tests" if no tests, no "Shell completions" if no CLI). Keep it concise, no filler.

```
# <app-name>

<one-line description from pyproject.toml>

## Setup (local development)

uv sync

## Development

Run commands inside the venv (auto-syncs dependencies):

uv run <command>

Start an interactive shell with the venv active:

uv run bash

## Usage

uv run <app> <example commands with realistic args>

## Install globally

uv tool install .

After install, run directly:
<app> <example>

## Tests (if tests exist)

uv run pytest

## Shell completions (if Click CLI)

<app> generate-completion --install
```

Notes:
- "Setup" section uses `uv sync` (syncs local venv, not a global install).
- "Install globally" uses `uv tool install .` (makes the command available system-wide, like pipx).
- Usage examples should use `uv run <app>` (works without global install).
- After global install, examples use bare `<app>` (no `uv run`).

## Deliverables checklist

- Python code with a clear entrypoint
- Sample input/output (if applicable)
- Tests only if requested
- Copy `assets/gitignore/.gitignore` as the project `.gitignore` for all layout types.
- `README.md` following the README structure above (mini-package and package layouts).
- Use `python` (not `python3`) in all deliverable commands because the default is uv.
- For Click CLIs, confirm `_completion.py` is included and `add_completion_command()` is called.
- For script CLIs using `argparse` + argcomplete, include user-facing instructions for installing and enabling system-wide completion (e.g., `python -m pip install argcomplete --break-system-packages` and `sudo activate-global-python-argcomplete`).
- Commit `uv.lock` to version control for reproducible builds.

## Pre-finish checklist (when building a project)

- Layout matches requested type (script/mini-package/package)
- `requires-python` matches the target
- `[build-system]` uses `uv_build`
- Dependencies listed in `[project.dependencies]`
- Dev/test tools in `[dependency-groups]` (PEP 735), not in `[project.optional-dependencies]`
- CLI entrypoint set in `[project.scripts]` if a CLI is provided
- Avoid deprecated features or compatibility shims (e.g., skip `from __future__ import annotations`)
- If tests are added/requested: pytest snippet in `pyproject.toml` and pytest in a dependency group (from `references/pyproject-snippets.md`)
- `README.md` present with sections from README structure template
- `uv.lock` present and committed to version control

## Troubleshooting

### uv cache

If uv fails due to cache permission errors, set a writable cache directory:
`UV_CACHE_DIR=<writable-path> uv run pytest`

### Dependency sync

If dependencies seem stale after editing `pyproject.toml` manually, run `uv sync` to update the lockfile and venv.

### Python version mismatch

If `uv init` picks a higher Python than intended, override with `uv init --package <name> --python 3.12` or edit `requires-python` in `pyproject.toml` and run `uv sync`.

## Example: simple script CLI (argparse + argcomplete)

See `examples/simple-script-app.py` for a minimal script-style CLI example.
