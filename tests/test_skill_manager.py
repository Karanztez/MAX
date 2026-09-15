import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.skill_manager import SkillManager


def main() -> None:
    with TemporaryDirectory() as folder:
        root = Path(folder)
        target = root / "demo"
        target.mkdir()
        (target / "SKILL.md").write_text(
            "---\nname: Demo Skill\ndescription: Test\ndefault: true\n---\n"
            "Always answer concisely.",
            encoding="utf-8",
        )
        manager = SkillManager(root)
        assert set(manager.skills) == {"demo"}
        assert manager.default_ids() == {"demo"}
        prompt = manager.compose_system_prompt("Base prompt", {"demo"})
        assert "Base prompt" in prompt
        assert "Active skill: Demo Skill" in prompt
        assert "Always answer concisely." in prompt
        assert manager.errors == []
    print("skill manager test passed")


if __name__ == "__main__":
    main()
