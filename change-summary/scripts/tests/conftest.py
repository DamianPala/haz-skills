"""Shared fixtures including synthetic git repo builder."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _run(args: list[str], cwd: Path) -> None:
    """Run a shell command, raise on failure."""
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{result.stderr}")


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command in the given directory."""
    _run(["git"] + args, cwd)


def _commit(cwd: Path, message: str, *, body: str = "") -> None:
    """Create a git commit with deterministic dates."""
    env_args = ["-c", "user.name=Test", "-c", "user.email=test@test.com"]
    full_msg = f"{message}\n\n{body}" if body else message
    _git(env_args + ["commit", "--allow-empty", "-m", full_msg], cwd)


def _write_and_add(cwd: Path, relpath: str, content: str) -> None:
    """Write a file and stage it."""
    filepath = cwd / relpath
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    _git(["add", relpath], cwd)


def _delete_and_add(cwd: Path, relpath: str) -> None:
    """Delete a file and stage the deletion."""
    _git(["rm", relpath], cwd)


@pytest.fixture(scope="session")
def synthetic_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a synthetic git repo with known commits and tags.

    Structure mirrors the reference synthetic-test-repo:
    - Initial commit + v1.0.0 tag
    - CC commits + v1.1.0 tag
    - Mixed commits (CC, WIP, custom prefix, merge, breaking) + v1.2.0 tag
    - A patch release + v1.2.1 tag
    """
    repo = tmp_path_factory.mktemp("synthetic-repo")
    env = ["-c", "user.name=Test", "-c", "user.email=test@test.com"]

    _git(["init", "--initial-branch=master"], repo)
    _git(["config", "user.name", "Test"], repo)
    _git(["config", "user.email", "test@test.com"], repo)
    # Disable hooks (global commitlint etc.) so test commits aren't rejected
    _git(["config", "core.hooksPath", "/dev/null"], repo)

    # ── v1.0.0: Initial project structure ──

    _write_and_add(
        repo,
        "pyproject.toml",
        (
            '[project]\nname = "test-project"\n'
            'description = "A synthetic test project"\nversion = "1.0.0"\n'
        ),
    )
    _write_and_add(repo, "README.md", "# Test Project\n\nA test project for change-summary.\n")
    _write_and_add(
        repo,
        "CHANGELOG.md",
        (
            "# Changelog\n\n## [1.0.0] - 2026-01-01\n\n"
            "### Added\n- Initial project structure\n- Basic API endpoints\n"
        ),
    )
    _write_and_add(repo, "src/__init__.py", "")
    _write_and_add(repo, "src/main.py", 'def main():\n    print("hello")\n')
    _write_and_add(
        repo,
        "src/api.py",
        (
            "def get_tasks():\n    return []\n\n\n"
            "def create_task(name):\n    return {'name': name}\n"
        ),
    )
    _write_and_add(repo, "src/utils.py", "def sanitize(s):\n    return s.strip()\n")
    _write_and_add(repo, "tests/test_main.py", "def test_main():\n    assert True\n")
    _write_and_add(
        repo,
        ".github/workflows/ci.yml",
        "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n",
    )
    _write_and_add(repo, "requirements.txt", "requests>=2.0\n")

    _git(env + ["commit", "-m", "feat: initial project structure"], repo)
    _git(["tag", "v1.0.0"], repo)

    # ── v1.1.0: CC commits ──

    _write_and_add(
        repo,
        "src/auth.py",
        (
            "def login(user, password):\n    return {'token': 'abc'}\n\n\n"
            "def oauth2_flow(provider):\n    return {'access_token': 'xyz'}\n"
        ),
    )
    _git(env + ["commit", "-m", "feat(auth): add OAuth2 support"], repo)

    # Modify api.py (small fix)
    _write_and_add(
        repo,
        "src/api.py",
        (
            "import time\n\n\ndef get_tasks():\n    return []\n\n\n"
            "def create_task(name):\n    return {'name': name}\n\n\n"
            "def handle_timeout(e):\n    time.sleep(1)\n    raise e\n"
        ),
    )
    _git(env + ["commit", "-m", "fix(api): handle timeout errors gracefully"], repo)

    _write_and_add(repo, "docs/usage.md", "# Usage\n\nRun `python -m test_project`\n")
    _git(env + ["commit", "-m", "docs: update usage guide"], repo)

    _write_and_add(
        repo,
        "tests/test_auth.py",
        ("def test_login():\n    assert True\n\ndef test_oauth2():\n    assert True\n"),
    )
    _git(env + ["commit", "-m", "test: add auth tests"], repo)

    _write_and_add(repo, "requirements.txt", "requests>=2.0\nflask>=3.0\n")
    _git(env + ["commit", "-m", "chore: update dependencies"], repo)

    _git(["tag", "v1.1.0"], repo)

    # ── v1.2.0: Mixed commits (CC, WIP, bracket prefix, merge, breaking) ──

    _write_and_add(
        repo,
        "src/api.py",
        (
            "import time\n\n\ndef get_tasks():\n    return []\n\n\n"
            "def create_task(name):\n    return {'name': name}\n\n\n"
            "def handle_timeout(e):\n    time.sleep(1)\n    raise e\n\n\n"
            "def batch_create(tasks):\n    return [create_task(t) for t in tasks]\n"
        ),
    )
    _git(env + ["commit", "-m", "feat(api): add batch task creation endpoint"], repo)

    # WIP/generic commits
    _write_and_add(
        repo,
        "src/utils.py",
        ("def sanitize(s):\n    return s.strip()\n\n\ndef normalize(s):\n    return s.lower()\n"),
    )
    _git(env + ["commit", "-m", "wip"], repo)

    _write_and_add(
        repo,
        "src/utils.py",
        (
            "def sanitize(s):\n    return s.strip()\n\n\n"
            "def normalize(s):\n    return s.lower().strip()\n"
        ),
    )
    _git(env + ["commit", "-m", "fix"], repo)

    _write_and_add(repo, "src/main.py", ('def main():\n    print("hello world")\n'))
    _git(env + ["commit", "-m", "update"], repo)

    _write_and_add(repo, "src/main.py", ('def main():\n    print("hello world!")\n'))
    _git(env + ["commit", "-m", "."], repo)

    # Bracket prefix commits
    _write_and_add(
        repo,
        "src/export.py",
        ("def export_csv(data):\n    return ','.join(str(d) for d in data)\n"),
    )
    _git(env + ["commit", "-m", "[FEAT] Add export feature"], repo)

    _write_and_add(
        repo,
        "src/utils.py",
        (
            "import datetime\n\n\n"
            "def sanitize(s):\n    return s.strip()\n\n\n"
            "def normalize(s):\n    return s.lower().strip()\n\n\n"
            "def fix_timezone(dt):\n    return dt.replace(tzinfo=datetime.timezone.utc)\n"
        ),
    )
    _git(env + ["commit", "-m", "[FIX] Fix timezone handling"], repo)

    # Merge commit: create a branch, commit, merge with --no-ff
    _git(["checkout", "-b", "feat/notifications"], repo)
    _write_and_add(
        repo,
        "src/notifications.py",
        ("def send_notification(user, msg):\n    print(f'Notify {user}: {msg}')\n"),
    )
    _git(env + ["commit", "-m", "feat: add notification system"], repo)
    _git(["checkout", "master"], repo)
    _git(
        env + ["merge", "--no-ff", "feat/notifications", "-m", "Merge branch 'feat/notifications'"],
        repo,
    )

    # Breaking change
    _write_and_add(
        repo,
        "src/api.py",
        (
            "import time\n\n\n"
            "def get_tasks_v2():\n    return {'tasks': [], 'meta': {}}\n\n\n"
            "def create_task(name):\n    return {'name': name, 'id': 1}\n\n\n"
            "def handle_timeout(e):\n    time.sleep(1)\n    raise e\n\n\n"
            "def batch_create(tasks):\n    return [create_task(t) for t in tasks]\n"
        ),
    )
    _git(env + ["commit", "-m", "feat!: change API response format"], repo)

    # Refactor
    _write_and_add(
        repo,
        "src/http_client.py",
        (
            "import urllib.request\n\n\n"
            "def get(url):\n    return urllib.request.urlopen(url).read()\n"
        ),
    )
    _git(env + ["commit", "-m", "refactor: extract http client"], repo)

    # CI
    _write_and_add(
        repo,
        ".github/workflows/deploy.yml",
        (
            "name: Deploy\non: push\n  branches: [main]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n"
        ),
    )
    _git(env + ["commit", "-m", "ci: add deployment workflow"], repo)

    _git(["tag", "v1.2.0"], repo)

    # ── v1.2.1: Patch release ──

    _write_and_add(
        repo,
        "src/auth.py",
        (
            "import threading\n\n\n"
            "def login(user, password):\n    return {'token': 'abc'}\n\n\n"
            "def oauth2_flow(provider):\n    return {'access_token': 'xyz'}\n\n\n"
            "_lock = threading.Lock()\n\n\n"
            "def refresh_token(token):\n    with _lock:\n        return {'token': 'new'}\n"
        ),
    )
    _git(env + ["commit", "-m", "fix(auth): prevent token refresh race condition"], repo)

    _write_and_add(
        repo,
        "tests/test_auth.py",
        (
            "def test_login():\n    assert True\n\n"
            "def test_oauth2():\n    assert True\n\n"
            "def test_token_refresh_race():\n    assert True\n"
        ),
    )
    _git(env + ["commit", "-m", "test: add regression test for token refresh"], repo)

    _git(["tag", "v1.2.1"], repo)

    # Extra commits after v1.2.1 (untagged, for testing auto-detect)
    _write_and_add(repo, "src/templates.py", "def render(name):\n    return f'Hello {name}'\n")
    _git(env + ["commit", "-m", "feat: add task templates"], repo)

    _write_and_add(
        repo,
        "src/templates.py",
        ("def render(name):\n    return f'Hello {name}'\n\n\n# TODO: more templates\n"),
    )
    _git(env + ["commit", "-m", "work in progress"], repo)

    return repo
