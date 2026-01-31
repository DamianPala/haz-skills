#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""Sample CLI app with three commands."""

import argparse
import logging
import sys
from dataclasses import dataclass

try:
    import argcomplete
except ImportError:
    argcomplete = None


@dataclass(frozen=True)
class GreetResult:
    message: str


@dataclass(frozen=True)
class AddResult:
    total: int


@dataclass(frozen=True)
class RepeatResult:
    output: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sampleapp4",
        description="Sample CLI app with three commands.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (use -vv for debug).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    greet_parser = subparsers.add_parser("greet", help="Greet someone.")
    greet_parser.add_argument("name", help="Name to greet.")
    greet_parser.add_argument(
        "--upper",
        action="store_true",
        help="Uppercase the greeting.",
    )

    add_parser = subparsers.add_parser("add", help="Add two integers.")
    add_parser.add_argument("a", type=int, help="First integer.")
    add_parser.add_argument("b", type=int, help="Second integer.")

    repeat_parser = subparsers.add_parser("repeat", help="Repeat text.")
    repeat_parser.add_argument("text", help="Text to repeat.")
    repeat_parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=2,
        help="How many times to repeat (default: 2).",
    )
    repeat_parser.add_argument(
        "--sep",
        default=" ",
        help="Separator between repeats (default: space).",
    )

    return parser


def setup_logging(verbosity: int) -> None:
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def cmd_greet(name: str, *, upper: bool) -> GreetResult:
    message = f"Hello, {name}!"
    if upper:
        message = message.upper()
    logging.info("Generated greeting for %s", name)
    return GreetResult(message=message)


def cmd_add(a: int, b: int) -> AddResult:
    total = a + b
    logging.info("Computed sum %s", total)
    return AddResult(total=total)


def cmd_repeat(text: str, count: int, *, sep: str) -> RepeatResult:
    if count < 1:
        raise ValueError("count must be >= 1")
    output = sep.join([text] * count)
    logging.info("Repeated text %d times", count)
    return RepeatResult(output=output)


def run(args: argparse.Namespace) -> int:
    match args.command:
        case "greet":
            result = cmd_greet(args.name, upper=args.upper)
            print(result.message)
        case "add":
            result = cmd_add(args.a, args.b)
            print(result.total)
        case "repeat":
            result = cmd_repeat(args.text, args.count, sep=args.sep)
            print(result.output)
        case _:
            raise AssertionError(f"Unhandled command: {args.command}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()

    if argcomplete is not None:
        argcomplete.autocomplete(parser)

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    try:
        return run(args)
    except ValueError as exc:
        logging.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
