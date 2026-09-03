#!/usr/bin/env python3
"""Check document invariants of the CLI Design Standard.

Checks, per file:

- every fenced ``json`` block parses;
- requirement IDs (``**D1:`` and the like) are unique;
- every reference to a requirement ID resolves to a defined one;
- no em dash (U+2014), no trailing whitespace;
- no table row at column zero (tables live inside list items).

Usage: ``uv run --no-project python cli-design/scripts/check-standard.py [FILE ...]``
from the repository root. Without arguments it checks the standard itself.
Exit status is 1 when any check fails.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_FILE = Path("cli-design/references/cli-design-standard.md")
ID_DEFINITION = re.compile(r"\*\*([A-Z][0-9]+):")
ID_TOKEN = re.compile(r"(?<![A-Za-z0-9+])([A-Z][0-9]+)(?![A-Za-z0-9])")
FENCE = re.compile(r"^```(\w*)\s*$")


def split_fences(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (line_number, kind, text) segments; kind is "prose" or the fence language."""
    segments: list[tuple[int, str, str]] = []
    kind = "prose"
    start = 1
    buffer: list[str] = []
    for number, line in enumerate(lines, start=1):
        match = FENCE.match(line)
        if match is None:
            buffer.append(line)
            continue
        segments.append((start, kind, "\n".join(buffer)))
        buffer = []
        if kind == "prose":
            kind = match.group(1) or "code"
            start = number + 1
        else:
            kind = "prose"
            start = number + 1
    segments.append((start, kind, "\n".join(buffer)))
    return segments


def check_json_blocks(path: Path, segments: list[tuple[int, str, str]]) -> list[str]:
    problems = []
    for start, kind, text in segments:
        if kind != "json":
            continue
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            line = start + error.lineno - 1
            problems.append(f"{path}:{line}: invalid JSON block: {error.msg}")
    return problems


def check_ids(
    path: Path, lines: list[str], segments: list[tuple[int, str, str]]
) -> list[str]:
    problems = []
    defined: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        for identifier in ID_DEFINITION.findall(line):
            if identifier in defined:
                problems.append(
                    f"{path}:{number}: duplicate requirement ID {identifier}"
                    f" (first defined at line {defined[identifier]})"
                )
            else:
                defined[identifier] = number
    letters = {identifier[0] for identifier in defined}
    for start, kind, text in segments:
        if kind != "prose":
            continue
        for offset, line in enumerate(text.split("\n")):
            for token in ID_TOKEN.findall(line):
                if token[0] in letters and token not in defined:
                    problems.append(
                        f"{path}:{start + offset}: unresolved requirement ID {token}"
                    )
    return problems


def check_lines(path: Path, lines: list[str]) -> list[str]:
    problems = []
    for number, line in enumerate(lines, start=1):
        if "—" in line:
            problems.append(f"{path}:{number}: em dash")
        if line != line.rstrip(" \t"):
            problems.append(f"{path}:{number}: trailing whitespace")
        if line.startswith("|"):
            problems.append(f"{path}:{number}: table row at column zero")
    return problems


def check_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    segments = split_fences(lines)
    return (
        check_json_blocks(path, segments)
        + check_ids(path, lines, segments)
        + check_lines(path, lines)
    )


def main(argv: list[str]) -> int:
    paths = [Path(argument) for argument in argv] or [DEFAULT_FILE]
    problems: list[str] = []
    for path in paths:
        if not path.is_file():
            problems.append(f"{path}: not a file")
            continue
        problems.extend(check_file(path))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s) in {len(paths)} file(s)", file=sys.stderr)
        return 1
    print(f"ok: {len(paths)} file(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
