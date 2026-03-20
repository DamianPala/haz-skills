# Pyproject snippets

Use these snippets only when the user asks for them or when they are clearly relevant to the request. Copy the exact blocks as needed and adjust as needed.

## Build system (uv_build)

Always scaffold with `uv init --package` to get the correct version pinning for the installed uv. The generated `[build-system]` block looks like this (example, do not hardcode):

```toml
[build-system]
requires = ["uv_build>=0.10.0,<0.11.0"]
build-backend = "uv_build"
```

If you must create `pyproject.toml` manually (no `uv init`), run `uv init --package _tmp` in `/tmp`, copy the `[build-system]` block, then delete the temp project.

## Dependency groups (PEP 735)

Unified variant (small projects):

```toml
[dependency-groups]
dev = [
  "ruff",
  "mypy",
  "pytest>=8.0",
  "pytest-cov",
]
```

Split variant (when test/lint groups are reused separately):

```toml
[dependency-groups]
dev = [
  {include-group = "lint"},
  {include-group = "test"},
]
lint = [
  "ruff",
  "mypy",
]
test = [
  "pytest>=8.0",
  "pytest-cov",
]
```

Add via CLI: `uv add --group dev ruff mypy` or `uv add --group test pytest pytest-cov`.

Sync a specific group: `uv sync --group test`. Sync all groups: `uv sync --all-groups`.

## Click completion

Copy `references/_completion.py` into the package and wire it:

```python
from myapp._completion import add_completion_command
add_completion_command(cli, "myapp")
```

Usage: `myapp generate-completion --install` (auto-installs) or `myapp generate-completion [bash|zsh|fish]` (stdout).

## bump-my-version (mini-package / package)

Add to `pyproject.toml`. Note: the `search`/`replace` pattern includes surrounding context to avoid matching `current_version` in the bumpversion config itself.

```toml
[tool.bumpversion]
current_version = "0.1.0"
commit = true
tag = true
tag_name = "v{new_version}"

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'name = "<app>"\nversion = "{current_version}"'
replace = 'name = "<app>"\nversion = "{new_version}"'
```

Replace `<app>` with the actual package name from `[project]`.

Usage: `uvx bump-my-version bump patch` (or `minor`/`major`).

## Ruff defaults

```toml
[tool.ruff]
line-length = 120
```

## pytest defaults

```toml
[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]

addopts = [
  "-ra",
  "--strict-markers",
  "--strict-config",
  "--tb=short",
  "--capture=fd",
  "--maxfail=5",
]

log_cli = true
log_cli_level = "INFO"
log_format = "[%(asctime)s.%(msecs)03d] - %(name)s:%(lineno)d [%(levelname)s]: %(message)s"
log_date_format = "%Y-%m-%d %H:%M:%S"

norecursedirs = [
  ".git",
  ".venv",
  "__pycache__",
  "build",
  "dist",
  ".eggs",
  "*.egg",
]
```
