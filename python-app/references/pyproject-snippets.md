# Pyproject snippets

Use these snippets only when the user asks for them or when they are clearly relevant to the request. Copy the exact blocks as needed and adjust other block if needed.

## Hatch default env (uv + common dev tools)

```toml
[tool.hatch.envs.default]
type = "virtual"
path = ".venv"
installer = "uv"
skip-install = false
features = ["test"]
dependencies = [
  "ruff",
  "mypy",
  "pytest",
  "pytest-cov",
]
```

## Optional test feature (required when using `features = ["test"]`)

```toml
[project.optional-dependencies]
test = [
  "pytest>=8.0",
]
```

## Click completion (Hatch post-install, bash)

```toml
[tool.hatch.envs.default]
post-install-commands = [
  "bash -lc 'dest=\"$XDG_DATA_HOME\"; if [ -z \"$dest\" ]; then dest=\"$HOME/.local/share\"; fi; dest=\"$dest/bash-completion/completions/<app-name>\"; mkdir -p \"$(dirname \"$dest\")\"; _<APP_NAME_UPPER>_COMPLETE=bash_source <app-name> > \"$dest\"'",
]
```

Notes:
- Replace `<app-name>` with the CLI command name (e.g., `sampleapp`).
- Replace `<APP_NAME_UPPER>` with the uppercased CLI name and non-alphanumerics as `_` (e.g., `SAMPLEAPP`).
- This generates a completion script file; the shell still needs to load user completions (see skill instructions).

## Disable SPDX headers in Hatch templates

```toml
[template.licenses]
headers = false
```

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
