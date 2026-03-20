"""Generate deterministic Agent prompts for interpret and verify steps.

Always generates per-chunk worker prompts + orchestration dispatch prompt,
even for single chunk (orchestrator never interprets/verifies inline).
"""

from __future__ import annotations

from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parents[3] / "references" / "prompts"


def _load_template(name: str) -> str:
    return (_TEMPLATES_DIR / name).read_text(encoding="utf-8")


def _list_output_files(workdir: Path) -> list[str]:
    chunks = sorted(workdir.glob("diff-*.txt"))
    return [str(c) for c in chunks]


def _format_file_list(files: list[str]) -> str:
    return "\n".join(f"- `{f}`" for f in files)


def _project_label(name: str | None, description: str | None) -> str:
    if name and description:
        return f"{name} -- {description}"
    if name:
        return name
    return "(unknown project)"


# --- Interpret prompts ---


def _build_interpret_rules(output_path: str, range_str: str, project: str) -> str:
    return _load_template("interpret-rules.md").format(
        output_path=output_path,
        range=range_str,
        project=project,
    )


def _write_multi_interpret(
    workdir: Path,
    files: list[str],
    range_str: str,
    project: str,
    agent: str,
) -> None:
    chunk_prompt_paths: list[str] = []

    for i, chunk_file in enumerate(files, 1):
        rules = _build_interpret_rules(f"{workdir}/changes-chunk-{i}.yaml", range_str, project)
        header = (
            "You are interpreting one chunk of a change-summary diff.\n\n"
            f"## Input\nRead this file: `{chunk_file}`\n\n"
            "Do NOT read other chunk files. Do NOT write to `changes.yaml`.\n"
        )
        prompt = header + "\n" + rules
        path = workdir / f"interpret-chunk-{i}-prompt.md"
        path.write_text(prompt, encoding="utf-8")
        chunk_prompt_paths.append(str(path))

    orchestration = _load_template("interpret-orchestration.md").format(
        chunk_count=len(files),
        chunk_prompt_list=_format_file_list(chunk_prompt_paths),
        workdir=workdir,
        agent=agent,
    )
    (workdir / "interpret-prompt.md").write_text(orchestration, encoding="utf-8")


# --- Verify prompts ---


def _build_verify_rules(output_path: str) -> str:
    return _load_template("verify-rules.md").format(
        output_path=output_path,
    )


def _write_multi_verify(workdir: Path, files: list[str], agent: str) -> None:
    chunk_prompt_paths: list[str] = []

    for i, chunk_file in enumerate(files, 1):
        rules = _build_verify_rules(f"{workdir}/verify-chunk-{i}-result.txt")
        header = (
            "You are verifying one chunk of a change-summary.\n\n"
            "## Input\n"
            f"- Raw diff: `{chunk_file}`\n"
            f"- Interpreted changes: `{workdir}/changes-chunk-{i}.yaml`\n\n"
            "Read the raw diff file. Read the interpreted changes YAML. "
            "Verify each YAML item against the diffs in your chunk.\n\n"
            "Do NOT read other chunk files. Do NOT write to `verify-result.txt`.\n"
        )
        prompt = header + "\n" + rules
        path = workdir / f"verify-chunk-{i}-prompt.md"
        path.write_text(prompt, encoding="utf-8")
        chunk_prompt_paths.append(str(path))

    orchestration = _load_template("verify-orchestration.md").format(
        chunk_prompt_list=_format_file_list(chunk_prompt_paths),
        workdir=workdir,
        agent=agent,
    )
    (workdir / "verify-prompt.md").write_text(orchestration, encoding="utf-8")


# --- Orphan fill prompts ---


def _build_orphan_fill_rules(output_path: str) -> str:
    return _load_template("orphan-fill-rules.md").format(
        output_path=output_path,
    )


def write_orphan_prompts(
    workdir: Path,
    orphans: dict[int, list[str]],
    agent: str = "claude",
) -> None:
    """Write orphan fill prompts for chunks with orphan files."""
    chunk_prompt_paths: list[str] = []

    for chunk_num in sorted(orphans):
        orphan_diff_path = workdir / f"orphan-diff-{chunk_num}.txt"
        if not orphan_diff_path.is_file():
            continue

        output_path = f"{workdir}/orphan-changes-chunk-{chunk_num}.yaml"
        rules = _build_orphan_fill_rules(output_path)
        header = (
            "You are interpreting ORPHAN files that were missed in the initial "
            "change-summary interpretation pass.\n\n"
            f"## Input\nRead this file: `{orphan_diff_path}`\n\n"
            "These files were present in the diff but not covered by any YAML entry. "
            "Describe the changes in them.\n"
        )
        prompt = header + "\n" + rules
        path = workdir / f"orphan-fill-chunk-{chunk_num}-prompt.md"
        path.write_text(prompt, encoding="utf-8")
        chunk_prompt_paths.append(str(path))

    if not chunk_prompt_paths:
        return

    # Write orchestration prompt
    dispatch_lines = []
    for prompt_path in chunk_prompt_paths:
        dispatch_lines.append(
            f"acpc prompt {agent} --input-file {prompt_path} "
            f"--model standard --permissions write --quiet"
        )

    orchestration = (
        f"## Orphan fill: {len(chunk_prompt_paths)} chunk(s) with orphan files\n\n"
        "Run each orphan fill prompt:\n\n"
        "```bash\n" + "\n".join(f"{line} &" for line in dispatch_lines) + "\n```\n\n"
        "Launch all in parallel, then `wait` for completion.\n\n"
        "After completion, verify outputs:\n\n"
        "```bash\n"
        f"ls -lh {workdir}/orphan-changes-chunk-*.yaml\n"
        "```\n\n"
        'Report: "Orphan fill done: N/M chunks filled" with file sizes.\n\n'
        "### Retry on failure\n\n"
        "If any orphan output is missing:\n"
        "1. Re-run the failed chunk's acpc command (same args, not in background)\n"
        "2. If it fails again, report which chunk(s) failed and stop.\n"
    )
    (workdir / "orphan-fill-prompt.md").write_text(orchestration, encoding="utf-8")


# --- Dedup prompt ---


def _write_dedup_prompt(workdir: Path) -> None:
    """Write dedup prompt for post-merge deduplication."""
    changes_path = f"{workdir}/changes.yaml"
    output_path = f"{workdir}/changes.yaml"
    rules = _load_template("dedup-rules.md").format(
        changes_path=changes_path,
        output_path=output_path,
    )
    header = (
        "You are deduplicating a merged change summary. This is a post-merge step "
        "to remove near-duplicate entries created by independent chunk interpreters.\n\n"
    )
    prompt = header + rules
    (workdir / "dedup-prompt.md").write_text(prompt, encoding="utf-8")


# --- Entry point ---


def write_prompts(
    workdir: str | Path,
    range_str: str,
    project_name: str | None = None,
    project_description: str | None = None,
    agent: str = "claude",
) -> None:
    """Write all agent prompts to workdir."""
    out = Path(workdir)
    out.mkdir(parents=True, exist_ok=True)

    files = _list_output_files(out)
    project = _project_label(project_name, project_description)

    # Always generate dispatch prompts (even for single chunk).
    # Orchestrator dispatches to acpc, never interprets/verifies inline.
    _write_multi_interpret(out, files, range_str, project, agent)
    _write_multi_verify(out, files, agent)

    # Dedup prompt (only useful with multi-chunk, but always generated
    # so the orchestrator can decide whether to use it)
    if len(files) > 1:
        _write_dedup_prompt(out)
