---
name: python-app
description: General-purpose Python apps (CLI tools, services, libraries, scripts, automation) for Ubuntu >= 24.04 and Python >= 3.12. Use for templates, project structure, implementation, refactors, or best-practice setup.
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
- Run `hatch new <name>` without `--cli` and wire the CLI manually in `src/<app>/cli.py` plus `[project.scripts]` when needed.
- After `hatch new`, update `pyproject.toml` with required tool sections (Hatch envs, pytest, lint/type configs) from `references/pyproject-snippets.md` when relevant to the request.
- Define interfaces: CLI args, public API functions, config, env vars.
- Implement core logic with logging and validation; add tests if requested.
- Provide run/usage instructions (use Hatch for package and mini-package apps).

## System requirements check (before building)

- Confirm Ubuntu and Python >= 3.12 are available.
- For package apps, ensure `uv` and `hatch` is installed and on PATH.
- Confirm Hatch config disables SPDX headers when using `hatch new` (set `[template.licenses] headers = false` in `~/.config/hatch/config.toml`).
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
- Create the project with Hatchling first, then build the app inside that structure. Add necessary modules if needed.
- For mini-package and package apps, use Hatch to run the app and tests (e.g., `hatch run ...` or `hatch shell`).
- For Click CLIs, enable completions by default (do not skip unless the user opts out): add the Hatch `post-install-commands` hook that writes a bash completion file under `"$XDG_DATA_HOME"/bash-completion/completions/<app-name>` (falls back to `~/.local/share`) using `_APP_NAME_COMPLETE=bash_source` (see `references/pyproject-snippets.md`), and include shell setup instructions in deliverables.
- For script layout CLIs using `argparse`, enable argcomplete by default (unless user opts out): add `# PYTHON_ARGCOMPLETE_OK` before imports, add a safe `argcomplete` import after imports, and call `argcomplete.autocomplete(parser)` after building the parser.
- If using Hatch env `features` (e.g., `features = ["test"]`), ensure matching entries exist under `[project.optional-dependencies]`.

## Project layouts

script:

- Single file only (e.g., `app.py`).
- Include a shebang on the first line (use `#!/usr/bin/env python`).
- Stdlib-only; no external dependencies.
- If using `argparse`, wire argcomplete completions; it is optional and only activates if `argcomplete` is installed.

mini-package:

- Generate with Hatchling using a `src/` layout.
- `pyproject.toml`
- `src/app/__init__.py`
- `src/app/cli.py`
- Use `click` for CLI entrypoints.
- Configure `pyproject.toml` according to `references/pyproject-snippets.md` and apply only the relevant blocks.
- Run the app and tests via Hatch.

package:

- Generate with Hatchling using a `src/` layout.
- `pyproject.toml`
- `src/app/__init__.py`
- `src/app/cli.py` (only if the app exposes a CLI)
- `src/app/core.py` (core logic; can be renamed if a domain-specific module fits better)
- Optional modules as needed (e.g., `config.py`, `service.py`).
- `tests/` (only if requested)
- `README.md` (only if requested)
- Configure `pyproject.toml` according to `references/pyproject-snippets.md` and apply only the relevant blocks.
- Run the app and tests via Hatch.

## Config pattern

- CLI flags override config file values.
- Config file optional; support JSON/YAML/TOML if requested.
- Environment variables optional and documented when used.

## Logging and errors

- INFO for high-level progress, DEBUG for details.
- Log to stdout by default; allow file logging if requested.
- Catch exceptions at top-level; surface helpful messages.
- Use f-strings for all logging messages (no %-style formatting).

## Deliverables checklist

- Python code with a clear entrypoint
- Example command(s) or usage snippet
- Sample input/output (if applicable)
- Tests or docs only if requested
- Copy `assets/gitignore/.gitignore` as the project `.gitignore` for all layout types.
- After creating the project, include run instructions. For Hatch-based mini-package/package apps: tell the user to run `hatch shell`, then invoke the CLI by its command name (e.g., `sampleapp ...`). Include at least one concrete example command.
- Use `python` (not `python3`) in all deliverable commands because the default is uv.
- For Click CLIs, confirm the completion hook exists in `pyproject.toml`, and explain that the post-install hook generates a completion file and the shell must load user completions, with a minimal one-line `~/.bashrc` example when needed.
- For script CLIs using `argparse` + argcomplete, include user-facing instructions for installing and enabling system-wide completion (e.g., `python -m pip install argcomplete --break-system-packages` and `sudo activate-global-python-argcomplete`).

## Pre-finish checklist (when building a project)

- Layout matches requested type (script/mini-package/package)
- `requires-python` matches the target
- Dependencies listed in `[project.dependencies]`
- CLI entrypoint set in `[project.scripts]` if a CLI is provided
- Avoid deprecated features or compatibility shims (e.g., skip `from __future__ import annotations`)
- If tests are added/requested: pytest snippet in `pyproject.toml` and pytest installed via Hatch env + optional dependencies (from `references/pyproject-snippets.md`)
- If using Hatch env features: ensure matching `[project.optional-dependencies]` entries exist
- README updated with run instructions and at least one example command

## Troubleshooting

## uv cache

If Hatch/uv fails due to cache permission errors, rerun with a writable cache directory:
`UV_CACHE_DIR=<writable-path> hatch run pytest` (or `hatch shell` / `hatch run ...`).

## Example: simple script CLI (argparse + argcomplete)

See `examples/simple-script-app.py` for a minimal script-style CLI example.
