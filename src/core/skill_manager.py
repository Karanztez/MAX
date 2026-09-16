"""Safe, instruction-only SKILL.md loader for MaxPlus AI."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    description: str
    instructions: str
    enabled_by_default: bool = False


class SkillManager:
    """Discover SKILL.md files without importing or executing skill code."""

    MAX_SKILL_BYTES = 64 * 1024

    def __init__(self, root: Optional[Path] = None) -> None:
        if root:
            self.root = root
        else:
            cwd_skills = Path.cwd() / "skills"
            project_skills = Path(__file__).resolve().parent.parent.parent / "skills"
            module_skills = Path(__file__).resolve().parent / "skills"
            if cwd_skills.exists():
                self.root = cwd_skills
            elif project_skills.exists():
                self.root = project_skills
            else:
                self.root = module_skills
        self.skills: dict[str, Skill] = {}
        self.errors: list[str] = []
        self.refresh()

    @staticmethod
    def _frontmatter(text: str) -> tuple[dict[str, str], str]:
        if not text.startswith("---"):
            return {}, text.strip()
        lines = text.splitlines()
        try:
            end = lines.index("---", 1)
        except ValueError:
            return {}, text.strip()
        meta: dict[str, str] = {}
        for line in lines[1:end]:
            if ":" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip().strip('"\'')
        return meta, "\n".join(lines[end + 1:]).strip()

    def refresh(self) -> None:
        self.skills.clear()
        self.errors.clear()
        if not self.root.exists():
            return
        for path in sorted(self.root.rglob("SKILL.md")):
            try:
                if path.stat().st_size > self.MAX_SKILL_BYTES:
                    raise ValueError("ไฟล์มีขนาดเกิน 64 KB")
                meta, instructions = self._frontmatter(path.read_text(encoding="utf-8"))
                if not instructions:
                    raise ValueError("ไม่มีคำสั่ง Skill")
                skill_id = path.parent.relative_to(self.root).as_posix()
                if skill_id == ".":
                    skill_id = path.parent.name
                name = meta.get("name") or path.parent.name.replace("-", " ").title()
                self.skills[skill_id] = Skill(
                    skill_id=skill_id,
                    name=name,
                    description=meta.get("description", ""),
                    instructions=instructions,
                    enabled_by_default=meta.get("default", "false").lower() in ("1", "true", "yes", "on"),
                )
            except Exception as ex:
                self.errors.append(f"{path}: {ex}")

    def default_ids(self) -> set[str]:
        return {item.skill_id for item in self.skills.values() if item.enabled_by_default}

    def compose_system_prompt(self, base_prompt: str, enabled_ids: Iterable[str]) -> str:
        selected = [self.skills[item] for item in enabled_ids if item in self.skills]
        selected.sort(key=lambda item: item.name.casefold())
        parts = [base_prompt.strip()] if base_prompt.strip() else []
        for skill in selected:
            parts.append(
                f"## Active skill: {skill.name}\n"
                f"{skill.instructions}\n"
                "Follow this skill only when it is relevant to the user's request."
            )
        return "\n\n".join(parts)

    def install_skill(self, skill_id: str, content: str, overwrite: bool = True) -> tuple[bool, str]:
        """Install or update a skill by writing SKILL.md into skills directory."""
        sid = skill_id.strip().lower().replace(" ", "-")
        if not sid:
            return False, "Error: Skill ID cannot be empty"

        raw_text = content.strip()
        if not raw_text:
            return False, "Error: Skill content cannot be empty"

        # Auto-wrap with frontmatter if missing
        if not raw_text.startswith("---"):
            name = sid.replace("-", " ").title()
            raw_text = f"---\nname: {name}\ndescription: Custom Skill for {name}\ndefault: false\n---\n\n{raw_text}"

        target_dir = self.root / sid
        skill_file = target_dir / "SKILL.md"

        if skill_file.exists() and not overwrite:
            return False, f"Error: Skill '{sid}' already exists and overwrite is False"

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(raw_text, encoding="utf-8")
            self.refresh()
            if sid in self.skills:
                return True, f"✅ ติดตั้งสกิล '{self.skills[sid].name}' ({sid}) สำเร็จเรียบร้อยแล้ว!"
            return True, f"✅ บันทึกไฟล์ '{skill_file}' สำเร็จเรียบร้อยแล้ว"
        except Exception as ex:
            return False, f"Error installing skill '{sid}': {ex}"

    def install_from_github(self, repo_or_url: str, skill_id: str = "") -> tuple[bool, str]:
        """Fetch and install SKILL.md from a GitHub repository or URL."""
        import urllib.request
        import urllib.error

        src = repo_or_url.strip()
        if not src:
            return False, "Error: GitHub repo or URL cannot be empty"

        # Case 1: Direct raw URL
        if "raw.githubusercontent.com" in src or src.endswith("SKILL.md") or src.endswith(".md"):
            raw_url = src
            sid = skill_id.strip() or src.split("/")[-2] if "SKILL.md" in src else src.split("/")[-1].replace(".md", "")
        # Case 2: Tree/Blob GitHub URL
        elif "github.com" in src and ("/tree/" in src or "/blob/" in src):
            # https://github.com/owner/repo/tree/main/skills/my-skill
            clean = src.split("github.com/")[-1]
            parts = clean.split("/")
            owner = parts[0]
            repo = parts[1]
            branch = parts[3] if len(parts) > 3 else "main"
            subpath = "/".join(parts[4:]) if len(parts) > 4 else ""
            if subpath and not subpath.endswith("SKILL.md"):
                subpath = f"{subpath}/SKILL.md"
            elif not subpath:
                subpath = "SKILL.md"
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{subpath}"
            sid = skill_id.strip() or (parts[-1] if parts[-1] != "SKILL.md" else parts[-2])
        # Case 3: owner/repo:skill_name or owner/repo
        else:
            clean_repo = src.split("github.com/")[-1].rstrip(".git").strip("/")
            sub_skill = ""
            if ":" in clean_repo:
                clean_repo, sub_skill = clean_repo.split(":", 1)
            parts = clean_repo.split("/")
            if len(parts) < 2:
                return False, f"Error: รูปแบบชื่อ Repository ไม่ถูกต้อง (ต้องเป็น 'owner/repo' หรือ URL เต็ม)"
            owner, repo = parts[0], parts[1]
            sid = skill_id.strip() or (sub_skill.strip() if sub_skill.strip() else repo)

            # Try candidate paths
            candidates = []
            if sub_skill:
                candidates.append(f"skills/{sub_skill}/SKILL.md")
                candidates.append(f"{sub_skill}/SKILL.md")
                candidates.append(f"{sub_skill}.md")
            candidates.extend(["SKILL.md", f"skills/{sid}/SKILL.md", f"{sid}/SKILL.md", "skills/SKILL.md"])

            headers = {"User-Agent": "MAX-AI-Agent/1.0", "Accept": "text/plain,application/vnd.github.v3.raw"}
            for b in ("main", "master", "HEAD"):
                for c_path in candidates:
                    test_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{c_path}"
                    try:
                        req = urllib.request.Request(test_url, headers=headers, method="GET")
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            text = resp.read().decode("utf-8", errors="replace")
                            if text.strip():
                                return self.install_skill(sid, text, overwrite=True)
                    except Exception:
                        continue
            return False, f"Error: ไม่พบไฟล์ SKILL.md ใน repository '{owner}/{repo}'"

        headers = {"User-Agent": "MAX-AI-Agent/1.0", "Accept": "text/plain,application/vnd.github.v3.raw"}
        try:
            req = urllib.request.Request(raw_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            if not text.strip():
                return False, f"Error: ไฟล์ที่ดาวน์โหลดจาก '{raw_url}' ไม่มีเนื้อหา"
            return self.install_skill(sid, text, overwrite=True)
        except Exception as ex:
            return False, f"Error downloading skill from '{raw_url}': {ex}"

    def delete_skill(self, skill_id: str) -> tuple[bool, str]:
        """Delete an installed skill directory."""
        import shutil
        sid = skill_id.strip().lower()
        if not sid:
            return False, "Error: Skill ID cannot be empty"

        target_dir = self.root / sid
        if not target_dir.exists():
            # Check if skill exists with partial match
            match = next((k for k in self.skills if k.casefold() == sid.casefold()), None)
            if match:
                target_dir = self.root / match
                sid = match
            else:
                return False, f"Error: ไม่พบสกิล '{sid}' ในระบบ"

        try:
            if target_dir.is_dir():
                shutil.rmtree(target_dir)
            elif target_dir.is_file():
                target_dir.unlink()
            self.refresh()
            return True, f"🗑️ ลบสกิล '{sid}' ออกจากระบบเรียบร้อยแล้ว"
        except Exception as ex:
            return False, f"Error deleting skill '{sid}': {ex}"

    def list_skills_info(self) -> list[dict[str, Any]]:
        """Return comprehensive list of all installed skills."""
        results = []
        for sid, skill in sorted(self.skills.items(), key=lambda item: item[1].name.casefold()):
            results.append({
                "id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "default": skill.enabled_by_default,
                "path": str(self.root / skill.skill_id / "SKILL.md"),
            })
        return results

