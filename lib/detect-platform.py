#!/usr/bin/env python3
"""Detect git platform and resolve working access commands.

Output: JSON with platform info and ready-to-use command templates.
  {
    "platform": "gitlab"|"github",
    "host": "gitlab.example.com",
    "project": "group/subgroup/repo",
    "project_id": 145,
    "commands": {
      "mr_get": "glab api projects/145/merge_requests/{iid}",
      "mr_list": "glab api projects/145/merge_requests",
      "mr_create": "glab mr create -R group/subgroup/repo"
    }
  }

Placeholders in commands: {iid}, {nr} (MR/PR number).
Agent substitutes and runs. No fallback logic needed in skills.

Exit 1 if platform detection fails entirely.

Canonical location: haz-skills/lib/detect-platform.py
Consumers: pr-create, merge-message, change-summary (via symlinks)
"""
import json
import re
import shutil
import subprocess
import sys
from urllib.parse import quote_plus, urlparse


def run(args: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, ""


def get_remote_url() -> str:
    rc, url = run(["git", "remote", "get-url", "origin"])
    if rc != 0 or not url:
        rc, remotes = run(["git", "remote"])
        if rc == 0 and remotes:
            first = remotes.splitlines()[0]
            rc, url = run(["git", "remote", "get-url", first])
    if rc != 0 or not url:
        print("No git remote found", file=sys.stderr)
        sys.exit(1)
    return url


def parse_remote(url: str) -> tuple[str, str]:
    """Extract (host, project_path) from a git remote URL.

    Handles:
      git@host:group/repo.git              (SSH shorthand)
      ssh://git@host/group/repo.git         (SSH with scheme)
      ssh://git@host:2244/group/repo.git    (SSH with port)
      https://host/group/repo.git           (HTTPS)
    """
    if "@" in url and "://" not in url:
        after_at = url.split("@", 1)[1]
        host, path = after_at.split(":", 1)
        return host, _clean_path(path)

    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or ""
    return host, _clean_path(path)


def _clean_path(path: str) -> str:
    path = path.lstrip("/")
    return re.sub(r"\.git/?$", "", path)


# -- GitHub owner/repo from project path --

def _gh_owner_repo(project: str) -> str:
    parts = project.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return project


# -- GitLab project ID resolution --

def _resolve_gitlab_id(project: str) -> int | None:
    if not project or not shutil.which("glab"):
        return None

    encoded = quote_plus(project)
    rc, out = run(["glab", "api", f"projects/{encoded}"])
    if rc == 0 and out:
        try:
            return json.loads(out).get("id")
        except (json.JSONDecodeError, TypeError):
            pass

    repo_name = project.rsplit("/", 1)[-1]
    rc, out = run(["glab", "api", f"projects?search={repo_name}&per_page=20"])
    if rc == 0 and out:
        try:
            for p in json.loads(out):
                if p.get("path_with_namespace") == project:
                    return p.get("id")
        except (json.JSONDecodeError, TypeError):
            pass

    return None


# -- Access probing --

def _probe_gitlab(project: str) -> tuple[str, int | None]:
    """Probe GitLab access. Returns (access_method, project_id).

    access_method: "cli" | "cli_flag" | "api" | ""
    """
    # 1. CLI auto-detect (glab resolves project from git remote)
    rc, _ = run(["glab", "repo", "view", "--output", "json"])
    if rc == 0:
        return "cli", None

    # 2. CLI with explicit -R flag
    rc, _ = run(["glab", "repo", "view", "-R", project, "--output", "json"])
    if rc == 0:
        return "cli_flag", None

    # 3. API with numeric project ID
    project_id = _resolve_gitlab_id(project)
    if project_id:
        return "api", project_id

    return "", None


def _build_gitlab_commands(method: str, project: str, project_id: int | None) -> dict[str, str]:
    if method == "cli":
        return {
            "mr_get": "glab mr view {iid} --output json",
            "mr_list": "glab mr list --output json",
            "mr_create": "glab mr create",
        }
    if method == "cli_flag":
        return {
            "mr_get": f"glab mr view {{iid}} -R {project} --output json",
            "mr_list": f"glab mr list -R {project} --output json",
            "mr_create": f"glab mr create -R {project}",
        }
    if method == "api" and project_id:
        base = f"glab api projects/{project_id}"
        return {
            "mr_get": f"{base}/merge_requests/{{iid}}",
            "mr_list": f"{base}/merge_requests",
            # -R may still work for mr create even when repo view -R failed
            "mr_create": f"glab mr create -R {project}",
        }
    return {}


def _build_github_commands(project: str) -> dict[str, str]:
    owner_repo = _gh_owner_repo(project)
    # gh works with local repo context, but add -R for safety
    return {
        "mr_get": f"gh pr view {{nr}} -R {owner_repo} --json number,title,body,baseRefName,headRefName",
        "mr_list": f"gh pr list -R {owner_repo} --json number,title,headRefName,baseRefName",
        "mr_create": f"gh pr create -R {owner_repo}",
    }


# -- Platform detection --

def detect_platform(host: str) -> str | None:
    """Detect platform from hostname. Returns 'gitlab', 'github', or None."""
    if "github" in host:
        return "github"
    if "gitlab" in host:
        return "gitlab"

    if shutil.which("gh"):
        rc, _ = run(["gh", "auth", "status", "--hostname", host])
        if rc == 0:
            return "github"

    if shutil.which("glab"):
        rc, out = run(["glab", "auth", "status"])
        if host.lower() in out.lower():
            return "gitlab"

    if shutil.which("curl"):
        rc, _ = run(["curl", "-sf", "--max-time", "5", f"https://{host}/api/v4/version"])
        if rc == 0:
            return "gitlab"
        rc, _ = run(["curl", "-sf", "--max-time", "5", f"https://{host}/api/v3/meta"])
        if rc == 0:
            return "github"

    return None


def main():
    url = get_remote_url()
    host, project = parse_remote(url)
    if not host:
        print(f"Cannot parse host from remote URL: {url}", file=sys.stderr)
        sys.exit(1)

    platform = detect_platform(host)
    if not platform:
        print(f"Cannot detect platform for '{host}'. Is gh or glab authenticated?", file=sys.stderr)
        sys.exit(1)

    result: dict[str, str | int | dict[str, str]] = {
        "platform": platform,
        "host": host,
        "project": project,
    }

    if platform == "gitlab" and shutil.which("glab"):
        method, project_id = _probe_gitlab(project)
        if project_id:
            result["project_id"] = project_id
        commands = _build_gitlab_commands(method, project, project_id)
        if commands:
            result["commands"] = commands
        else:
            result["note"] = "glab cannot access this project. Check permissions or glab auth."

    elif platform == "github" and shutil.which("gh"):
        result["commands"] = _build_github_commands(project)

    elif platform == "gitlab":
        result["note"] = "glab not installed"

    elif platform == "github":
        result["note"] = "gh not installed"

    print(json.dumps(result))


if __name__ == "__main__":
    main()
