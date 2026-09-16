"""GitHub repository inspection, raw file reading, and Git operations tools."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

try:
    from ..types import MCPTool
except (ImportError, ModuleNotFoundError):
    from src.core.mcp.types import MCPTool  # type: ignore[no-redef]


def _normalize_github_repo_name(repo: str) -> str:
    r = repo.strip()
    if "github.com/" in r:
        r = r.split("github.com/")[-1]
    r = r.rstrip("/").rstrip(".git").strip("/")
    return r


def _builtin_github_search_repos(query: str, count: int = 5, sort: str = "stars") -> str:
    """Search GitHub public repositories via GitHub REST API."""
    q = query.strip()
    if not q:
        return "Error: Query cannot be empty"

    n = max(1, min(count, 15))
    s = sort.strip() if sort.strip() in {"stars", "forks", "updated"} else "stars"
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort={s}&order=desc&per_page={n}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        items = data.get("items", [])
        if not items:
            return f"🔍 ไม่พบ Repository บน GitHub ที่ตรงกับคำค้นหา: '{q}'"

        res = [f"🐙 ผลการค้นหา GitHub Repositories สำหรับ '{q}' (แสดง {len(items)} รายการ):\n"]
        for idx, item in enumerate(items, 1):
            full_name = item.get("full_name", "")
            desc = item.get("description") or "ไม่มีคำอธิบาย"
            stars = item.get("stargazers_count", 0)
            forks = item.get("forks_count", 0)
            lang = item.get("language") or "ไม่ระบุ"
            html_url = item.get("html_url", "")
            updated = item.get("updated_at", "")[:10]

            res.append(
                f"{idx}. 📦 **{full_name}** ★ {stars:,} | 🍴 {forks:,} | 🏷️ {lang} (อัปเดตล่าสุด: {updated})\n"
                f"   คำอธิบาย: {desc}\n"
                f"   🔗 {html_url}"
            )

        return "\n\n".join(res)
    except Exception as ex:
        return f"Error searching GitHub repositories: {ex}"


def _builtin_github_get_repo(repo: str) -> str:
    """Fetch repository metadata and latest release from GitHub API."""
    repo_name = _normalize_github_repo_name(repo)
    if not repo_name or "/" not in repo_name:
        return "Error: กรุณาระบุชื่อ repo ในรูปแบบ 'owner/repo' (เช่น 'Karanztez/MAX')"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        url = f"https://api.github.com/repos/{repo_name}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        full_name = data.get("full_name", repo_name)
        desc = data.get("description") or "ไม่มีคำอธิบาย"
        stars = data.get("stargazers_count", 0)
        forks = data.get("forks_count", 0)
        watchers = data.get("subscribers_count", 0)
        open_issues = data.get("open_issues_count", 0)
        lang = data.get("language") or "ไม่ระบุ"
        license_name = data.get("license", {}).get("name") if data.get("license") else "ไม่มี License"
        default_branch = data.get("default_branch", "main")
        html_url = data.get("html_url", "")
        created = data.get("created_at", "")[:10]
        updated = data.get("updated_at", "")[:10]

        rel_text = "ยังไม่มี Release"
        try:
            rel_url = f"https://api.github.com/repos/{repo_name}/releases/latest"
            rel_req = urllib.request.Request(rel_url, headers=headers, method="GET")
            with urllib.request.urlopen(rel_req, timeout=10) as rel_resp:
                rel_data = json.loads(rel_resp.read().decode("utf-8", errors="replace"))
                tag = rel_data.get("tag_name", "")
                rel_name = rel_data.get("name", "")
                rel_published = rel_data.get("published_at", "")[:10]
                rel_text = f"{tag} ({rel_name}) เมื่อ {rel_published}"
        except Exception:
            pass

        return (
            f"🐙 Repository: {full_name}\n"
            f"{'─'*50}\n"
            f"• คำอธิบาย: {desc}\n"
            f"• สถิติ: ★ {stars:,} Stars | 🍴 {forks:,} Forks | 👁️ {watchers:,} Watchers | 📌 {open_issues:,} Open Issues\n"
            f"• ภาษาหลัก: {lang} | License: {license_name} | Default Branch: `{default_branch}`\n"
            f"• สร้างเมื่อ: {created} | อัปเดตล่าสุด: {updated}\n"
            f"• Release ล่าสุด: {rel_text}\n"
            f"• ลิงก์: {html_url}"
        )
    except Exception as ex:
        return f"Error fetching GitHub repository details for '{repo_name}': {ex}"


def _builtin_github_read_file(repo: str, file_path: str, branch: str = "") -> str:
    """Read source code or file directly from a GitHub repository without cloning."""
    repo_name = _normalize_github_repo_name(repo)
    clean_path = file_path.strip().lstrip("/")
    if not repo_name or not clean_path:
        return "Error: กรุณาระบุชื่อ repo (เช่น 'owner/repo') และ path ของไฟล์ (เช่น 'README.md' หรือ 'src/main.py')"

    branches_to_try = [branch.strip()] if branch.strip() else ["HEAD", "main", "master"]
    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "text/plain,application/vnd.github.v3.raw",
    }

    for b in branches_to_try:
        raw_url = f"https://raw.githubusercontent.com/{repo_name}/{b}/{clean_path}"
        try:
            req = urllib.request.Request(raw_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                lines = content.splitlines()
                return (
                    f"📄 File: {repo_name}/{clean_path} (Branch: {b}, {len(lines)} บรรทัด, {len(content)} ตัวอักษร)\n"
                    f"{'─'*60}\n"
                    f"{content}"
                )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            return f"HTTP Error {e.code} reading '{clean_path}' from '{repo_name}': {e.reason}"
        except Exception as ex:
            return f"Error reading '{clean_path}' from '{repo_name}': {ex}"

    return f"Error: ไม่พบไฟล์ '{clean_path}' ใน repository '{repo_name}' (ค้นหาใน branches: {', '.join(branches_to_try)})"


def _builtin_github_list_issues(repo: str, state: str = "open", count: int = 5) -> str:
    """List issues and pull requests for a repository."""
    repo_name = _normalize_github_repo_name(repo)
    if not repo_name or "/" not in repo_name:
        return "Error: กรุณาระบุชื่อ repo ในรูปแบบ 'owner/repo'"

    n = max(1, min(count, 20))
    st = state.strip().lower() if state.strip().lower() in {"open", "closed", "all"} else "open"
    url = f"https://api.github.com/repos/{repo_name}/issues?state={st}&per_page={n}"

    headers = {
        "User-Agent": "MAX-AI-Agent/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        if not data:
            return f"ไม่พบรายการ Issues / PRs สถานะ '{st}' ใน '{repo_name}'"

        res = [f"📋 รายการ Issues/PRs ({st}) ใน {repo_name} (แสดง {len(data)} รายการล่าสุด):\n"]
        for idx, item in enumerate(data, 1):
            num = item.get("number", "?")
            title = item.get("title", "")
            user = item.get("user", {}).get("login", "unknown")
            is_pr = "pull_request" in item
            kind = "🔀 PR" if is_pr else "📌 Issue"
            comments = item.get("comments", 0)
            created = item.get("created_at", "")[:10]
            item_url = item.get("html_url", "")
            labels = [lbl.get("name", "") for lbl in item.get("labels", []) if isinstance(lbl, dict)]
            lbl_str = f" [{', '.join(labels)}]" if labels else ""
            res.append(f"{idx}. {kind} #{num}: {title}{lbl_str}\n   โดย: @{user} ({created}) | ความเห็น: {comments}\n   🔗 {item_url}")

        return "\n\n".join(res)
    except Exception as ex:
        return f"Error listing issues for '{repo_name}': {ex}"


def _builtin_github_clone_repo(repo_url: str, target_dir: str = "") -> str:
    """Clone a GitHub repository safely into local workspace."""
    try:
        from .system_tools import _builtin_run_command
    except (ImportError, ModuleNotFoundError):
        from src.core.mcp.builtins.system_tools import _builtin_run_command  # type: ignore[no-redef]

    r = repo_url.strip()
    if not r:
        return "Error: Repository URL or name cannot be empty"

    if not r.startswith("http://") and not r.startswith("https://") and not r.startswith("git@"):
        r = f"https://github.com/{r.rstrip('.git')}.git"

    cmd = f"git clone {r}"
    if target_dir.strip():
        cmd += f" \"{target_dir.strip()}\""

    res = _builtin_run_command(cmd, timeout_seconds=120)
    return f"📥 สั่งโคลน Repository: {r}\n\n{res}"


def get_git_tools() -> dict[str, tuple[MCPTool, Any]]:
    """Return dictionary of GitHub tools."""
    return {
        "github_search_repos": (
            MCPTool(
                name="github_search_repos",
                description="ค้นหาและสำรวจ Repositories บน GitHub ตามคำค้นหา ภาษา หรือจำนวนดาว (Stars)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "คำค้นหา เช่น fastmcp, android termux, machine learning"},
                        "count": {"type": "integer", "description": "จำนวนผลลัพธ์ที่ต้องการ (ค่าเริ่มต้น 5, สูงสุด 15)", "default": 5},
                        "sort": {"type": "string", "description": "การเรียงลำดับ: stars, forks, updated (ค่าเริ่มต้น stars)", "default": "stars"},
                    },
                    "required": ["query"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_search_repos(
                query=str(args.get("query", "")),
                count=int(args.get("count", 5)),
                sort=str(args.get("sort", "stars")),
            ),
        ),
        "github_get_repo": (
            MCPTool(
                name="github_get_repo",
                description="ดึงข้อมูลสรุปของ GitHub Repository (จำนวนดาว, ภาษาหลัก, License, สถิติ, และ Release ล่าสุด)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository ในรูปแบบ 'owner/repo' หรือ URL เต็ม เช่น 'Karanztez/MAX'"},
                    },
                    "required": ["repo"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_get_repo(str(args.get("repo", ""))),
        ),
        "github_read_file": (
            MCPTool(
                name="github_read_file",
                description="อ่านเนื้อหาไฟล์โค้ดหรือข้อความจาก GitHub Repository โดยตรง โดยไม่ต้องดาวน์โหลดหรือโคลนทั้งโปรเจกต์",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository เช่น 'Karanztez/MAX'"},
                        "file_path": {"type": "string", "description": "พาธของไฟล์ใน repo เช่น 'README.md' หรือ 'src/cli.py'"},
                        "branch": {"type": "string", "description": "ชื่อ branch (ค่าเริ่มต้นดึงจาก default branch / HEAD)", "default": ""},
                    },
                    "required": ["repo", "file_path"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_read_file(
                repo=str(args.get("repo", "")),
                file_path=str(args.get("file_path", "")),
                branch=str(args.get("branch", "")),
            ),
        ),
        "github_list_issues": (
            MCPTool(
                name="github_list_issues",
                description="ดึงรายการ Issues และ Pull Requests ล่าสุดของ GitHub Repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "ชื่อ repository ในรูปแบบ 'owner/repo'"},
                        "state": {"type": "string", "description": "สถานะ: open, closed, all (ค่าเริ่มต้น open)", "default": "open"},
                        "count": {"type": "integer", "description": "จำนวนรายการที่ต้องการดึง (ค่าเริ่มต้น 5)", "default": 5},
                    },
                    "required": ["repo"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_list_issues(
                repo=str(args.get("repo", "")),
                state=str(args.get("state", "open")),
                count=int(args.get("count", 5)),
            ),
        ),
        "github_clone_repo": (
            MCPTool(
                name="github_clone_repo",
                description="โคลน GitHub Repository ลงมายังเครื่องในโฟลเดอร์ที่กำหนด",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo_url": {"type": "string", "description": "URL ของ GitHub repo หรือ 'owner/repo' เช่น 'https://github.com/Karanztez/MAX'"},
                        "target_dir": {"type": "string", "description": "โฟลเดอร์ปลายทางที่ต้องการโคลนไปเก็บ (หากไม่ระบุจะใช้ชื่อ repo เดิม)", "default": ""},
                    },
                    "required": ["repo_url"],
                },
                server_name="builtin",
            ),
            lambda args: _builtin_github_clone_repo(
                repo_url=str(args.get("repo_url", "")),
                target_dir=str(args.get("target_dir", "")),
            ),
        ),
    }
