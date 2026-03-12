#!/usr/bin/env python3
"""Detect git platform (GitHub/GitLab) and CLI from remote URL.

Output: JSON {"cli": "gh"|"glab", "host": "...", "method": "..."}
Exit 1 with error message if detection fails.
"""
import json
import subprocess
import sys
from urllib.parse import urlparse


def run(cmd: str) -> tuple[int, str]:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    return r.returncode, r.stdout.strip()


def get_remote_host() -> str:
    rc, url = run("git remote get-url origin 2>/dev/null || git remote get-url $(git remote | head -1)")
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
    rc, _ = run(f"gh auth status --hostname {host}")
    if rc == 0:
        return {"cli": "gh", "host": host, "method": "auth"}

    rc, out = run("glab auth status 2>&1")
    if host.lower() in out.lower():
        return {"cli": "glab", "host": host, "method": "auth"}

    # 3. API probe
    rc, _ = run(f"curl -sf --max-time 5 https://{host}/api/v4/version")
    if rc == 0:
        return {"cli": "glab", "host": host, "method": "api"}

    rc, _ = run(f"curl -sf --max-time 5 https://{host}/api/v3/meta")
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
