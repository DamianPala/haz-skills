#!/usr/bin/env python3
"""Detect git platform (GitHub/GitLab) and CLI from remote URL.

Output: JSON {"cli": "gh"|"glab", "host": "...", "method": "..."}
Exit 1 with error message if detection fails.

Cross-platform: works on Linux, macOS, Windows (Git Bash/WSL).
"""
import json
import shutil
import subprocess
import sys
from urllib.parse import urlparse


def run(args: list[str]) -> tuple[int, str]:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return 1, ""


def get_remote_host() -> str:
    rc, url = run(["git", "remote", "get-url", "origin"])
    if rc != 0 or not url:
        # Try first available remote
        rc, remotes = run(["git", "remote"])
        if rc == 0 and remotes:
            first = remotes.splitlines()[0]
            rc, url = run(["git", "remote", "get-url", first])
    if rc != 0 or not url:
        print("No git remote found", file=sys.stderr)
        sys.exit(1)

    # ssh: git@host:user/repo.git
    if "@" in url and "://" not in url:
        return url.split("@")[1].split(":")[0]
    # https://host/user/repo.git
    return urlparse(url).hostname or ""


def detect(host: str) -> dict:
    # 1. Known hosts
    if "github" in host:
        return {"cli": "gh", "host": host, "method": "known"}
    if "gitlab" in host:
        return {"cli": "glab", "host": host, "method": "known"}

    # 2. Auth status
    if shutil.which("gh"):
        rc, _ = run(["gh", "auth", "status", "--hostname", host])
        if rc == 0:
            return {"cli": "gh", "host": host, "method": "auth"}

    if shutil.which("glab"):
        rc, out = run(["glab", "auth", "status"])
        if host.lower() in out.lower():
            return {"cli": "glab", "host": host, "method": "auth"}

    # 3. API probe (only if curl available)
    if shutil.which("curl"):
        rc, _ = run(["curl", "-sf", "--max-time", "5", f"https://{host}/api/v4/version"])
        if rc == 0:
            return {"cli": "glab", "host": host, "method": "api"}

        rc, _ = run(["curl", "-sf", "--max-time", "5", f"https://{host}/api/v3/meta"])
        if rc == 0:
            return {"cli": "gh", "host": host, "method": "api"}

    return {}


def main():
    host = get_remote_host()
    result = detect(host)
    if not result:
        print(f"Cannot detect platform for '{host}'. Is gh or glab authenticated?", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
