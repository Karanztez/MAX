import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.skill_manager import SkillManager
except ImportError:
    from src.core.skill_manager import SkillManager  # type: ignore[no-redef]


import unittest


class TestSkillManager(unittest.TestCase):
    def test_skill_manager_basics(self) -> None:
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
            self.assertEqual(set(manager.skills), {"demo"})
            self.assertEqual(manager.default_ids(), {"demo"})
            prompt = manager.compose_system_prompt("Base prompt", {"demo"})
            self.assertIn("Base prompt", prompt)
            self.assertIn("Active skill: Demo Skill", prompt)
            self.assertIn("Always answer concisely.", prompt)
            self.assertEqual(manager.errors, [])


if __name__ == "__main__":
    unittest.main()

