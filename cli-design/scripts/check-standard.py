"""Check document invariants of the CLI Design Standard.

Checks, per file:

- every fenced ``json`` block parses;
- requirement IDs (``### D1:`` headings) are unique and in stage order;
- clause markers (``**D1a:**`` at the start of a paragraph) belong to the
  enclosing requirement and run a, b, c without gaps or duplicates;
- every reference to a requirement or clause ID resolves to one defined in
  any of the checked files, so the maintenance guide's references are
  resolved against the standard when both are given;
- every ``"standard"`` value in a JSON example equals the header version;
- no em dash (U+2014), no trailing whitespace;
- no indented table row (tables live at column zero).

On success it also prints the normative keyword counts of each file
(MUST, SHOULD, MAY; ``MUST NOT`` and ``SHOULD NOT`` count under their base
keyword) so an edit can be compared with the text before it.

Usage: ``uv run --no-project python cli-design/scripts/check-standard.py [FILE ...]``
from the repository root. Without arguments it checks the standard itself.
Exit status is 1 when any check fails.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

DEFAULT_FILE = Path("cli-design/references/cli-design-standard.md")
STAGES = "DIROFHBCMV"
ID_DEFINITION = re.compile(r"^### ([A-Z][0-9]+):")
ID_TOKEN = re.compile(r"(?<![A-Za-z0-9+])([A-Z][0-9]+)(?![A-Za-z0-9])")
CLAUSE_MARKER = re.compile(r"^\*\*([A-Z][0-9]+)([a-z]):\*\* ")
CLAUSE_TOKEN = re.compile(
    rf"(?<![A-Za-z0-9+])([{STAGES}][1-9][0-9]*[a-z])(?![A-Za-z0-9])"
)
VERSION_LINE = re.compile(r"^\*\*Version:\*\* (\S+)$")
STANDARD_VALUE = re.compile(r'"standard": "([^"]*)"')
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(\w*)\s*$")
KEYWORDS = ("MUST", "SHOULD", "MAY")

Segment = tuple[int, str, str]


@dataclass
class Document:
    path: Path
    lines: list[str]
    segments: list[Segment]
    defined: dict[str, int] = field(default_factory=dict)
    markers: set[str] = field(default_factory=set)


def split_fences(lines: list[str]) -> list[Segment]:
    """Return (line_number, kind, text) segments; kind is "prose" or the fence language."""
    segments: list[Segment] = []
    kind = "prose"
    start = 1
    buffer: list[str] = []
    fence_length = 0
    fence_character = ""
    for number, line in enumerate(lines, start=1):
        match = FENCE.match(line)
        if match is None:
            buffer.append(line)
            continue
        ticks, language = match.groups()
        if kind != "prose" and (
            language or len(ticks) < fence_length or ticks[0] != fence_character
        ):
            buffer.append(line)
            continue
        segments.append((start, kind, "\n".join(buffer)))
        buffer = []
        if kind == "prose":
            kind, fence_length = language or "code", len(ticks)
            fence_character = ticks[0]
        else:
            kind, fence_length = "prose", 0
        start = number + 1
    segments.append((start, kind, "\n".join(buffer)))
    if kind != "prose":
        segments.append((start - 1, "unclosed_fence", ""))
    return segments


def prose_lines(segments: list[Segment]):
    """Yield (line_number, line) for every line outside fences."""
    for start, kind, text in segments:
        if kind != "prose":
            continue
        for offset, line in enumerate(text.split("\n")):
            yield start + offset, line


def load(path: Path) -> Document:
    lines = path.read_text(encoding="utf-8").split("\n")
    return Document(path, lines, split_fences(lines))


def check_json_blocks(doc: Document) -> list[str]:
    problems = []
    for start, kind, text in doc.segments:
        if kind == "unclosed_fence":
            problems.append(f"{doc.path}:{start}: unclosed code fence")
            continue
        if kind != "json":
            continue
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            line = start + error.lineno - 1
            problems.append(f"{doc.path}:{line}: invalid JSON block: {error.msg}")
    return problems


def stage_key(identifier: str) -> tuple[int, int]:
    return STAGES.find(identifier[0]), int(identifier[1:])


def collect_ids(doc: Document) -> list[str]:
    """Record heading IDs on the document; check uniqueness and stage order."""
    problems = []
    for number, line in prose_lines(doc.segments):
        for identifier in ID_DEFINITION.findall(line):
            if identifier in doc.defined:
                problems.append(
                    f"{doc.path}:{number}: duplicate requirement ID {identifier}"
                    f" (first defined at line {doc.defined[identifier]})"
                )
            else:
                doc.defined[identifier] = number
    order = list(doc.defined)
    for previous, current in pairwise(order):
        if stage_key(current) <= stage_key(previous):
            problems.append(
                f"{doc.path}:{doc.defined[current]}: requirement {current}"
                f" out of order after {previous}"
            )
    return problems


def collect_clauses(doc: Document) -> list[str]:
    """Record clause markers on the document; check they sit under their requirement."""
    problems = []
    current: str | None = None
    expected = "a"
    for number, line in prose_lines(doc.segments):
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
                f"{doc.path}:{number}: clause {rule}{letter} outside requirement {rule}"
            )
            continue
        if letter != expected:
            problems.append(
                f"{doc.path}:{number}: clause {rule}{letter}, expected {rule}{expected}"
            )
        expected = chr(ord(letter) + 1)
        doc.markers.add(rule + letter)
    return problems


def check_references(doc: Document, ids: set[str], markers: set[str]) -> list[str]:
    """Every requirement or clause reference resolves to a definition in some checked file."""
    problems = []
    letters = {identifier[0] for identifier in ids}
    for number, line in prose_lines(doc.segments):
        for token in ID_TOKEN.findall(line):
            if token[0] in letters and token not in ids:
                problems.append(
                    f"{doc.path}:{number}: unresolved requirement ID {token}"
                )
        for token in CLAUSE_TOKEN.findall(line):
            if token[0] in letters and token not in markers:
                problems.append(f"{doc.path}:{number}: unresolved clause ID {token}")
    return problems


def check_version(doc: Document) -> list[str]:
    version = next(
        (m.group(1) for line in doc.lines if (m := VERSION_LINE.match(line))), None
    )
    if version is None:
        return []
    problems = []
    for start, kind, text in doc.segments:
        if kind != "json":
            continue
        for offset, line in enumerate(text.split("\n")):
            for value in STANDARD_VALUE.findall(line):
                if value != version:
                    problems.append(
                        f"{doc.path}:{start + offset}: example claims standard {value},"
                        f" header says {version}"
                    )
    return problems


def check_lines(doc: Document) -> list[str]:
    problems = []
    for number, line in enumerate(doc.lines, start=1):
        if "—" in line:
            problems.append(f"{doc.path}:{number}: em dash")
        if line != line.rstrip(" \t"):
            problems.append(f"{doc.path}:{number}: trailing whitespace")
        if line.lstrip(" ").startswith("|") and line.startswith(" "):
            problems.append(f"{doc.path}:{number}: indented table row")
    return problems


def keyword_counts(doc: Document) -> str:
    text = "\n".join(doc.lines)
    counts = (len(re.findall(rf"\b{word}\b", text)) for word in KEYWORDS)
    return " ".join(f"{word} {count}" for word, count in zip(KEYWORDS, counts))


def main(argv: list[str]) -> int:
    paths = [Path(argument) for argument in argv] or [DEFAULT_FILE]
    problems: list[str] = []
    docs: list[Document] = []
    for path in paths:
        if not path.is_file():
            problems.append(f"{path}: not a file")
            continue
        doc = load(path)
        problems.extend(collect_ids(doc))
        problems.extend(collect_clauses(doc))
        docs.append(doc)
    ids = {identifier for doc in docs for identifier in doc.defined}
    markers = {marker for doc in docs for marker in doc.markers}
    for doc in docs:
        problems.extend(check_json_blocks(doc))
        problems.extend(check_references(doc, ids, markers))
        problems.extend(check_version(doc))
        problems.extend(check_lines(doc))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s) in {len(paths)} file(s)", file=sys.stderr)
        return 1
    print(f"ok: {len(paths)} file(s) checked")
    for doc in docs:
        print(f"{doc.path.name}: {keyword_counts(doc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
