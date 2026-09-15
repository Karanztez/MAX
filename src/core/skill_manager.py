"""Safe, instruction-only SKILL.md loader for MaxPlus AI."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


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
