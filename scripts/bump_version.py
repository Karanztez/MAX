#!/usr/bin/env python3
"""
scripts/bump_version.py — Automated Semantic Version Bumper and Changelog Extractor for MAX.
Used by GitHub Actions and local release workflows.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent


def get_current_version() -> str:
    init_py = ROOT_DIR / "src" / "__init__.py"
    if init_py.exists():
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_py.read_text(encoding="utf-8"))
        if match:
            return match.group(1).strip().lstrip("v")

    setup_py = ROOT_DIR / "setup.py"
    if setup_py.exists():
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', setup_py.read_text(encoding="utf-8"))
        if match:
            return match.group(1).strip().lstrip("v")

    return "1.0.0"


def bump_semver(version: str, bump_type: str = "patch") -> str:
    cleaned = version.strip().lstrip("v")
    parts = cleaned.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 1
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    bump_type = bump_type.lower().strip()
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # default patch
        return f"{major}.{minor}.{patch + 1}"


def apply_version(new_version: str) -> None:
    ver = new_version.strip().lstrip("v")

    # 1. src/__init__.py
    init_path = ROOT_DIR / "src" / "__init__.py"
    if init_path.exists():
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{ver}"',
            init_path.read_text(encoding="utf-8"),
        )
        init_path.write_text(content, encoding="utf-8")

    # 2. src/core/updater.py
    updater_path = ROOT_DIR / "src" / "core" / "updater.py"
    if updater_path.exists():
        content = re.sub(
            r'APP_VERSION\s*=\s*["\'][^"\']+["\']',
            f'APP_VERSION = "{ver}"',
            updater_path.read_text(encoding="utf-8"),
        )
        updater_path.write_text(content, encoding="utf-8")

    # 3. src/core/mcp_manager.py & connection.py
    mcp_path = ROOT_DIR / "src" / "core" / "mcp_manager.py"
    if mcp_path.exists():
        content = re.sub(
            r'("clientInfo":\s*\{"name":\s*"MaxPlusAI",\s*"version":\s*")[^"]+("\})',
            rf'\g<1>{ver}\g<2>',
            mcp_path.read_text(encoding="utf-8"),
        )
        mcp_path.write_text(content, encoding="utf-8")

    conn_path = ROOT_DIR / "src" / "core" / "mcp" / "connection.py"
    if conn_path.exists():
        content = re.sub(
            r'("clientInfo":\s*\{"name":\s*"MaxPlusAI",\s*"version":\s*")[^"]+("\})',
            rf'\g<1>{ver}\g<2>',
            conn_path.read_text(encoding="utf-8"),
        )
        conn_path.write_text(content, encoding="utf-8")

    # 4. setup.py
    setup_path = ROOT_DIR / "setup.py"
    if setup_path.exists():
        content = re.sub(
            r'version\s*=\s*["\'][^"\']+["\']',
            f'version="{ver}"',
            setup_path.read_text(encoding="utf-8"),
        )
        setup_path.write_text(content, encoding="utf-8")

    # 5. pyproject.toml
    pyproject_path = ROOT_DIR / "pyproject.toml"
    if pyproject_path.exists():
        content = re.sub(
            r'version\s*=\s*["\'][^"\']+["\']',
            f'version = "{ver}"',
            pyproject_path.read_text(encoding="utf-8"),
        )
        pyproject_path.write_text(content, encoding="utf-8")

    # 6. Public Python SDK package
    sdk_init_path = ROOT_DIR / "src" / "max_ai" / "__init__.py"
    if sdk_init_path.exists():
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{ver}"',
            sdk_init_path.read_text(encoding="utf-8"),
        )
        sdk_init_path.write_text(content, encoding="utf-8")

    # 7. JavaScript SDK runtime version
    js_index_path = ROOT_DIR / "js" / "src" / "index.ts"
    if js_index_path.exists():
        content = re.sub(
            r'export const VERSION\s*=\s*["\'][^"\']+["\']',
            f'export const VERSION = "{ver}"',
            js_index_path.read_text(encoding="utf-8"),
        )
        js_index_path.write_text(content, encoding="utf-8")

    # 8. npm manifests (the lockfile stores the root package version twice)
    for manifest_name in ("package.json", "package-lock.json"):
        manifest_path = ROOT_DIR / manifest_name
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = ver
        if manifest_name == "package-lock.json":
            root_package = manifest.get("packages", {}).get("")
            if isinstance(root_package, dict):
                root_package["version"] = ver
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def update_changelog(new_version: str) -> None:
    """Updates CHANGELOG.md to promote [Unreleased] or add entry for new_version."""
    changelog_path = ROOT_DIR / "CHANGELOG.md"
    if not changelog_path.exists():
        return

    ver = new_version.strip().lstrip("v")
    tag = f"v{ver}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content = changelog_path.read_text(encoding="utf-8")

    # If version already exists in CHANGELOG.md, do nothing
    if re.search(rf'##\s*\[?v?{re.escape(ver)}\]?', content):
        return

    unreleased_match = re.search(r'(##\s*\[?Unreleased\]?[^\n]*\n)(.*?)(?=\n##\s|\Z)', content, re.DOTALL | re.IGNORECASE)
    if unreleased_match:
        unreleased_header = unreleased_match.group(1)
        unreleased_body = unreleased_match.group(2).strip()

        if unreleased_body:
            # Promote unreleased notes to new version and create fresh [Unreleased]
            replacement = (
                f"## [Unreleased]\n\n"
                f"---\n\n"
                f"## [{tag}] - {today}\n\n"
                f"{unreleased_body}\n"
            )
            content = content.replace(unreleased_match.group(0), replacement)
        else:
            # Empty unreleased, add new section
            git_notes = get_git_commit_log()
            replacement = (
                f"## [Unreleased]\n\n"
                f"---\n\n"
                f"## [{tag}] - {today}\n\n"
                f"### Added\n"
                f"{git_notes}\n"
            )
            content = content.replace(unreleased_match.group(0), replacement)
    else:
        # Prepend after header
        git_notes = get_git_commit_log()
        new_entry = (
            f"## [Unreleased]\n\n"
            f"---\n\n"
            f"## [{tag}] - {today}\n\n"
            f"### Added\n"
            f"{git_notes}\n\n"
            f"---\n\n"
        )
        content = new_entry + content

    changelog_path.write_text(content, encoding="utf-8")


def get_git_commit_log() -> str:
    try:
        # Get last tag
        tag_proc = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        last_tag = tag_proc.stdout.strip()
        if last_tag:
            log_proc = subprocess.run(
                ["git", "log", f"{last_tag}..HEAD", "--pretty=format:* %s (%h)"],
                cwd=str(ROOT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            logs = log_proc.stdout.strip()
            if logs:
                return logs
    except Exception:
        pass

    # Fallback to last 5 commits
    try:
        log_proc = subprocess.run(
            ["git", "log", "-n", "5", "--pretty=format:* %s (%h)"],
            cwd=str(ROOT_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return log_proc.stdout.strip()
    except Exception:
        return "* Maintenance updates and performance improvements"


def extract_release_notes(version: str) -> str:
    ver = version.strip().lstrip("v")
    changelog_files = [
        ROOT_DIR / "CHANGELOG.md",
        ROOT_DIR / "RELEASE_NOTES.md",
    ]

    for fpath in changelog_files:
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")

        # Pattern 1: Match specific version section e.g. ## [v1.0.2] or ## [1.0.2] or ## 1.0.2
        pattern = rf'##\s*\[?v?{re.escape(ver)}\]?[^\n]*\n(.*?)(?=\n##\s|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match and match.group(1).strip():
            return match.group(1).strip()

        # Pattern 2: Match Unreleased section if present
        unreleased_pattern = r'##\s*\[?Unreleased\]?[^\n]*\n(.*?)(?=\n##\s|\Z)'
        unreleased_match = re.search(unreleased_pattern, content, re.DOTALL | re.IGNORECASE)
        if unreleased_match and unreleased_match.group(1).strip():
            return unreleased_match.group(1).strip()

    # If no custom changelog entry found, fallback to Git commits
    git_logs = get_git_commit_log()
    return f"### 🚀 What's Changed\n\n{git_logs}"


def main() -> None:
    parser = argparse.ArgumentParser(description="MAX Version Bumper and Changelog Helper")
    parser.add_argument("--get", action="store_true", help="Print current version")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="Bump version type")
    parser.add_argument("--set-version", help="Explicitly set a version")
    parser.add_argument("--notes", help="Extract and print release notes for the given version")
    parser.add_argument("--update-changelog", help="Update CHANGELOG.md with the given version")
    parser.add_argument("--output-file", help="Write output to a specific file")

    args = parser.parse_args()

    curr = get_current_version()

    if args.get:
        print(curr)
        return

    target_version = curr
    if args.bump:
        target_version = bump_semver(curr, args.bump)
        apply_version(target_version)
        print(f"v{target_version}")
        return

    if args.set_version:
        target_version = args.set_version.strip().lstrip("v")
        apply_version(target_version)
        print(f"v{target_version}")
        return

    if args.update_changelog:
        update_changelog(args.update_changelog)
        return

    if args.notes:
        notes = extract_release_notes(args.notes)
        if args.output_file:
            Path(args.output_file).write_text(notes, encoding="utf-8")
        else:
            print(notes)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
