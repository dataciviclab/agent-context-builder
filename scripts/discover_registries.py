#!/usr/bin/env python3
"""Discover repos with registry.json in the GitHub org.

Scans all public repos in the configured org for registry/registry.json.
Compares with the current repos list in dataciviclab.config.yml.
Outputs the list of repos to add, or exits 0 if no changes.

No external dependencies — uses only stdlib (urllib, json).

Usage::

    python scripts/discover_registries.py \\
        --org dataciviclab --config dataciviclab.config.yml
    python scripts/discover_registries.py \\
        --org dataciviclab --config dataciviclab.config.yml --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _github_get(url: str, token: str | None = None) -> dict | list | None:
    """GET a GitHub API endpoint, return parsed JSON or None on 404."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def list_org_repos_with_registry(org: str, token: str | None = None) -> list[str]:
    """List all repos in the org that have registry/registry.json."""
    # Step 1: list all public repos
    repos: list[str] = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?type=public&per_page=100&page={page}"
        batch = _github_get(url, token)
        if not batch:
            break
        repos.extend(r["name"] for r in batch)
        page += 1
        if len(batch) < 100:
            break

    # Step 2: check which repos have registry/registry.json
    with_registry: list[str] = []
    for repo in repos:
        url = f"https://api.github.com/repos/{org}/{repo}/contents/registry/registry.json"
        if _github_get(url, token) is not None:
            with_registry.append(repo)
        time.sleep(0.1)

    return sorted(with_registry)


def load_config_repos(config_path: Path) -> list[str]:
    """Load repos list from dataciviclab.config.yml (simple YAML parser)."""
    repos: list[str] = []
    in_repos = False
    with open(config_path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("repos:"):
                in_repos = True
                continue
            if in_repos:
                if line.startswith("  - "):
                    repos.append(line.strip().removeprefix("- ").strip())
                elif line.strip() and not line.startswith(" "):
                    break  # reached next top-level key
    return repos


def save_config_repos(config_path: Path, repos: list[str]) -> None:
    """Update repos list in dataciviclab.config.yml, preserving YAML structure."""
    with open(config_path, encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    new_lines: list[str] = []
    in_repos = False

    for line in lines:
        if line.startswith("repos:"):
            in_repos = True
            new_lines.append("repos:")
            for repo in repos:
                new_lines.append(f"  - {repo}")
            continue
        if in_repos:
            if line.startswith("  - ") or line.strip() == "":
                continue
            else:
                in_repos = False
        new_lines.append(line)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover repos with registry.json")
    parser.add_argument("--org", default="dataciviclab", help="GitHub org name")
    parser.add_argument(
        "--config",
        default="dataciviclab.config.yml",
        help="Path to ACB config file",
    )
    parser.add_argument("--token", default=None, help="GitHub token (or GITHUB_TOKEN env)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to config file (default: dry-run)",
    )
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 1

    current_repos = load_config_repos(config_path)
    print(f"Current repos in config: {len(current_repos)}")

    discovered = list_org_repos_with_registry(args.org, token)
    print(f"Repos with registry.json: {len(discovered)}")

    current_set = set(current_repos)
    discovered_set = set(discovered)

    to_add = sorted(discovered_set - current_set)

    if not to_add:
        print("No new repos to add.")
        return 0

    print(f"\nTo add ({len(to_add)}):")
    for r in to_add:
        print(f"  + {r}")

    if args.apply:
        updated = sorted(current_set | discovered_set)
        save_config_repos(config_path, updated)
        print(f"\nConfig updated: {len(updated)} repos")
    else:
        print("\nDry run. Use --apply to update config.")

    return 1 if to_add else 0


if __name__ == "__main__":
    sys.exit(main())
