"""Integration test: verify prompt generation end-to-end."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def _make_test_repo(base: Path) -> Path:
    """Create a small git repo with 3 commits and a tag."""
    repo = base / "test-repo"
    repo.mkdir()

    _git(["init", "--initial-branch=main"], repo)
    _git(["config", "user.name", "Test"], repo)
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "core.hooksPath", "/dev/null"], repo)

    # Initial commit + tag
    (repo / "README.md").write_text("# My Project\n")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "my-project"\ndescription = "A test project"\nversion = "0.1.0"\n'
    )
    _git(["add", "."], repo)
    _git(["commit", "-m", "feat: initial commit"], repo)
    _git(["tag", "v0.1.0"], repo)

    # Second commit: source change
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def hello():\n    return 'hello'\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "feat: add hello function"], repo)

    # Third commit: fix
    (src / "main.py").write_text("def hello():\n    return 'hello world'\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "fix: correct greeting message"], repo)

    return repo


SCRIPTS_DIR = Path(__file__).resolve().parent.parent


class TestPromptGeneration:
    def test_full_cli_generates_prompts(self, tmp_path: Path) -> None:
        """Run full CLI and verify all output files are created."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Dispatch + worker prompts must exist
        assert (outdir / "diff-1.txt").is_file(), "diff-1.txt missing"
        assert (outdir / "interpret-prompt.md").is_file(), "interpret-prompt.md missing"
        assert (outdir / "interpret-chunk-1-prompt.md").is_file(), "interpret-chunk-1-prompt.md missing"
        assert (outdir / "verify-prompt.md").is_file(), "verify-prompt.md missing"
        assert (outdir / "verify-chunk-1-prompt.md").is_file(), "verify-chunk-1-prompt.md missing"

    def test_interpret_prompt_has_real_paths(self, tmp_path: Path) -> None:
        """interpret-prompt.md must contain actual file paths, not {workdir} placeholders."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )

        dispatch = (outdir / "interpret-prompt.md").read_text()
        worker = (outdir / "interpret-chunk-1-prompt.md").read_text()

        # Dispatch must reference the chunk worker prompt
        assert "interpret-chunk-1-prompt.md" in dispatch
        # Worker must contain actual paths and rules
        assert str(outdir) in worker, (
            f"interpret-chunk-1-prompt.md should reference {outdir}"
        )
        assert "diff-1.txt" in worker
        # Must NOT contain unfilled Python format placeholders
        assert "{workdir}" not in dispatch
        assert "{range}" not in worker
        assert "{project}" not in worker

    def test_verify_prompt_references_changes_yaml(self, tmp_path: Path) -> None:
        """verify-prompt.md must reference changes.yaml with actual path."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )

        dispatch = (outdir / "verify-prompt.md").read_text()
        worker = (outdir / "verify-chunk-1-prompt.md").read_text()

        # Dispatch must reference the chunk worker prompt
        assert "verify-chunk-1-prompt.md" in dispatch
        # Worker must reference changes YAML and diff
        assert f"{outdir}/changes-chunk-1.yaml" in worker
        assert "diff-1.txt" in worker
        # Must NOT contain unfilled placeholders
        assert "{workdir}" not in dispatch
        assert "{output_path}" not in worker
        assert "{cross_check_path}" not in worker

    def test_prompts_are_valid_markdown(self, tmp_path: Path) -> None:
        """Prompts should be valid markdown a sub-agent can follow."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )

        interpret_dispatch = (outdir / "interpret-prompt.md").read_text()
        interpret_worker = (outdir / "interpret-chunk-1-prompt.md").read_text()
        verify_dispatch = (outdir / "verify-prompt.md").read_text()
        verify_worker = (outdir / "verify-chunk-1-prompt.md").read_text()

        # Dispatch prompts have dispatch structure
        assert "## Dispatch" in interpret_dispatch
        assert "## Dispatch" in verify_dispatch

        # Worker prompts have full rules
        assert "## Interpretation flow" in interpret_worker
        assert "## Output" in interpret_worker
        assert "## Semantic checks" in verify_worker
        assert "## Output" in verify_worker

    def test_interpret_prompt_contains_project_info(self, tmp_path: Path) -> None:
        """Interpret prompt should include project name and range."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )

        # Project info is in worker prompt, not dispatch
        worker = (outdir / "interpret-chunk-1-prompt.md").read_text()

        assert "my-project" in worker
        assert "v0.1.0..HEAD" in worker

    def test_no_output_flag_skips_prompts(self, tmp_path: Path) -> None:
        """When --output is not set, prompts should not be written anywhere."""
        repo = _make_test_repo(tmp_path)

        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        assert result.returncode == 0

        # No prompt files should exist in cwd
        assert not (repo / "interpret-prompt.md").exists()
        assert not (repo / "verify-prompt.md").exists()

    def test_chunked_output_prompts_list_all_chunks(self, tmp_path: Path) -> None:
        """With small --max-tokens, prompts should list diff-N.txt chunk files."""
        repo = _make_test_repo(tmp_path)
        outdir = tmp_path / "output"

        subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(SCRIPTS_DIR),
                "change-summary",
                "v0.1.0",
                "HEAD",
                "--output",
                str(outdir),
                "--max-tokens",
                "200",
            ],
            capture_output=True,
            text=True,
            cwd=repo,
        )

        # With tiny token budget we should get chunks
        chunk_files = list(outdir.glob("chunk-*.txt"))
        if chunk_files:
            interpret = (outdir / "interpret-prompt.md").read_text()
            verify = (outdir / "verify-prompt.md").read_text()

            for i in range(1, len(chunk_files) + 1):
                # Interpret chunk prompts
                int_prompt = outdir / f"interpret-chunk-{i}-prompt.md"
                assert int_prompt.exists(), f"missing: {int_prompt.name}"
                assert int_prompt.name in interpret, (
                    f"{int_prompt.name} not referenced in interpret orchestration"
                )
                int_content = int_prompt.read_text()
                assert "## Interpretation flow" in int_content, (
                    f"{int_prompt.name} missing interpretation rules"
                )
                assert "{output_path}" not in int_content, (
                    f"{int_prompt.name} has unfilled placeholder"
                )

                # Verify chunk prompts
                ver_prompt = outdir / f"verify-chunk-{i}-prompt.md"
                assert ver_prompt.exists(), f"missing: {ver_prompt.name}"
                assert ver_prompt.name in verify, (
                    f"{ver_prompt.name} not referenced in verify orchestration"
                )
                ver_content = ver_prompt.read_text()
                assert "## Semantic checks" in ver_content, (
                    f"{ver_prompt.name} missing verification rules"
                )
                assert "{output_path}" not in ver_content, (
                    f"{ver_prompt.name} has unfilled placeholder"
                )
                assert "{cross_check_path}" not in ver_content, (
                    f"{ver_prompt.name} has unfilled cross_check_path placeholder"
                )
