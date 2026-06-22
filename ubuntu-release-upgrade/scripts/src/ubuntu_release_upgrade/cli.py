"""Command-line entry point: read-only inspection subcommands.

Each subcommand prints JSON findings to stdout. `generate-runbook` writes the
runbook file and prints a small status JSON. Typed helper errors map to non-zero
exit codes (network=2, permission=3, not-applicable=1).
"""

from __future__ import annotations

import argparse
import json
import sys

from ubuntu_release_upgrade import conffile, release, repos, runbook, system


def _print(payload: object) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _cmd_check_path(args: argparse.Namespace) -> int:
    return _print(release.check_path(args.target))


def _cmd_inventory_repos(args: argparse.Namespace) -> int:
    return _print(repos.inventory(args.target_codename, probe=not args.no_probe))


def _cmd_classify_conffile(args: argparse.Namespace) -> int:
    return _print(conffile.classify(args.path))


def _cmd_generate_runbook(args: argparse.Namespace) -> int:
    return _print(
        runbook.generate(
            target=args.target,
            out=args.out,
            force=args.force,
            probe=not args.no_probe,
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ubuntu-release-upgrade", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_path = sub.add_parser("check-path", help="Check if the upgrade path is open")
    p_path.add_argument("--target", help="Target codename or version (default: next release)")
    p_path.set_defaults(func=_cmd_check_path)

    p_repos = sub.add_parser("inventory-repos", help="Inventory APT sources")
    p_repos.add_argument("--target-codename", help="Probe target suite availability")
    p_repos.add_argument("--no-probe", action="store_true", help="Skip network availability probe")
    p_repos.set_defaults(func=_cmd_inventory_repos)

    p_conf = sub.add_parser("classify-conffile", help="Classify a pending conffile prompt")
    p_conf.add_argument("path", help="Absolute path of the conffile (e.g. /etc/foo.conf)")
    p_conf.set_defaults(func=_cmd_classify_conffile)

    p_run = sub.add_parser("generate-runbook", help="Collect findings and write the runbook")
    p_run.add_argument("--target", help="Target codename or version (default: next release)")
    p_run.add_argument("--out", help="Output path (default: state dir)")
    p_run.add_argument("--force", action="store_true", help="Regenerate even if a runbook exists")
    p_run.add_argument("--no-probe", action="store_true", help="Skip repo availability probe")
    p_run.set_defaults(func=_cmd_generate_runbook)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except system.HelperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
