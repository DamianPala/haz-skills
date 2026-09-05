#!/usr/bin/env python3
"""Check document invariants of the CLI Design Standard.

Checks, per file:

- every fenced ``json`` block parses;
- requirement IDs (``### D1:`` headings) are unique and in stage order;
- clause markers (``**D1a**`` at the start of a paragraph) belong to the
  enclosing requirement and run a, b, c without gaps or duplicates;
- every reference to a requirement or clause ID resolves to a defined one;
- every ``"standard"`` value in a JSON example equals the header version;
- no em dash (U+2014), no trailing whitespace;
- no indented table row (tables live at column zero).

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
STAGES = "DIROFMH"
ID_DEFINITION = re.compile(r"^### ([A-Z][0-9]+):")
ID_TOKEN = re.compile(r"(?<![A-Za-z0-9+])([A-Z][0-9]+)(?![A-Za-z0-9])")
CLAUSE_MARKER = re.compile(r"^\*\*([A-Z][0-9]+)([a-z])\*\* ")
CLAUSE_TOKEN = re.compile(
    rf"(?<![A-Za-z0-9+`])([{STAGES}][1-9][0-9]*[a-z])(?![A-Za-z0-9])"
)
VERSION_LINE = re.compile(r"^\*\*Version:\*\* (\S+)$")
STANDARD_VALUE = re.compile(r'"standard": "([^"]*)"')
FENCE = re.compile(r"^```(\w*)\s*$")

Segment = tuple[int, str, str]


def split_fences(lines: list[str]) -> list[Segment]:
    """Return (line_number, kind, text) segments; kind is "prose" or the fence language."""
    segments: list[Segment] = []
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
        kind = (match.group(1) or "code") if kind == "prose" else "prose"
        start = number + 1
    segments.append((start, kind, "\n".join(buffer)))
    return segments


def prose_lines(segments: list[Segment]):
    """Yield (line_number, line) for every line outside fences."""
    for start, kind, text in segments:
        if kind != "prose":
            continue
        for offset, line in enumerate(text.split("\n")):
            yield start + offset, line


def check_json_blocks(path: Path, segments: list[Segment]) -> list[str]:
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


def stage_key(identifier: str) -> tuple[int, int]:
    return STAGES.find(identifier[0]), int(identifier[1:])


def check_ids(path: Path, segments: list[Segment]) -> tuple[list[str], list[str]]:
    """Check heading IDs; return (problems, defined IDs in reading order)."""
    problems = []
    defined: dict[str, int] = {}
    for number, line in prose_lines(segments):
        for identifier in ID_DEFINITION.findall(line):
            if identifier in defined:
                problems.append(
                    f"{path}:{number}: duplicate requirement ID {identifier}"
                    f" (first defined at line {defined[identifier]})"
                )
            else:
                defined[identifier] = number
    order = list(defined)
    for previous, current in zip(order, order[1:]):
        if stage_key(current) <= stage_key(previous):
            problems.append(
                f"{path}:{defined[current]}: requirement {current} out of order after {previous}"
            )
    letters = {identifier[0] for identifier in defined}
    for number, line in prose_lines(segments):
        for token in ID_TOKEN.findall(line):
            if token[0] in letters and token not in defined:
                problems.append(f"{path}:{number}: unresolved requirement ID {token}")
    return problems, order


def check_clauses(path: Path, segments: list[Segment], defined: list[str]) -> list[str]:
    """Check clause markers against their requirement and clause citations against markers."""
    problems = []
    markers: set[str] = set()
    current: str | None = None
    expected = "a"
    for number, line in prose_lines(segments):
        heading = ID_DEFINITION.match(line)
        if heading:
            current, expected = heading.group(1), "a"
            continue
        if line.startswith("## "):
            current = None
            continue
        marker = CLAUSE_MARKER.match(line)
        if marker is None:
            continue
        rule, letter = marker.groups()
        if rule != current:
            problems.append(
                f"{path}:{number}: clause {rule}{letter} outside requirement {rule}"
            )
            continue
        if letter != expected:
            problems.append(
                f"{path}:{number}: clause {rule}{letter}, expected {rule}{expected}"
            )
        expected = chr(ord(letter) + 1)
        markers.add(rule + letter)
    letters = {identifier[0] for identifier in defined}
    for number, line in prose_lines(segments):
        for token in CLAUSE_TOKEN.findall(line):
            if token[0] in letters and token not in markers:
                problems.append(f"{path}:{number}: unresolved clause ID {token}")
    return problems


def check_version(path: Path, lines: list[str], segments: list[Segment]) -> list[str]:
    version = next(
        (m.group(1) for line in lines if (m := VERSION_LINE.match(line))), None
    )
    if version is None:
        return []
    problems = []
    for start, kind, text in segments:
        if kind != "json":
            continue
        for offset, line in enumerate(text.split("\n")):
            for value in STANDARD_VALUE.findall(line):
                if value != version:
                    problems.append(
                        f"{path}:{start + offset}: example claims standard {value},"
                        f" header says {version}"
                    )
    return problems


def check_lines(path: Path, lines: list[str]) -> list[str]:
    problems = []
    for number, line in enumerate(lines, start=1):
        if "—" in line:
            problems.append(f"{path}:{number}: em dash")
        if line != line.rstrip(" \t"):
            problems.append(f"{path}:{number}: trailing whitespace")
        if line.lstrip(" ").startswith("|") and line.startswith(" "):
            problems.append(f"{path}:{number}: indented table row")
    return problems


def check_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").split("\n")
    segments = split_fences(lines)
    id_problems, defined = check_ids(path, segments)
    return (
        check_json_blocks(path, segments)
        + id_problems
        + check_clauses(path, segments, defined)
        + check_version(path, lines, segments)
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
