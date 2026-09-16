"""
test_web_security.py — Unit tests for Web Access Security and Domain Permission Guard.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.settings_store import SettingsStore
    from core.mcp_manager import (
        check_web_permission,
        set_web_permission_handler,
        _builtin_fetch_web,
        _builtin_http_request,
    )
except ImportError:
    from src.core.settings_store import SettingsStore  # type: ignore[no-redef]
    from src.core.mcp_manager import (  # type: ignore[no-redef]
        check_web_permission,
        set_web_permission_handler,
        _builtin_fetch_web,
        _builtin_http_request,
    )


class TestWebSecurity(unittest.TestCase):

    def setUp(self):
        self.tmpdir = TemporaryDirectory()
        self.settings_path = Path(self.tmpdir.name) / "settings.json"
        self.store = SettingsStore(path=self.settings_path)

    def tearDown(self):
        set_web_permission_handler(None)
        self.tmpdir.cleanup()

    def test_default_security_settings(self):
        """Verify default web security settings."""
        sec = self.store.load_web_security_settings()
        self.assertEqual(sec["policy"], "ask")
        self.assertIn("github.com", sec["allowed_domains"])
        self.assertIn("duckduckgo.com", sec["allowed_domains"])
        self.assertEqual(sec["denied_domains"], [])

    def test_add_allowed_and_denied_domains(self):
        """Verify adding allowed and denied domains."""
        self.store.add_allowed_domain("example.com")
        sec = self.store.load_web_security_settings()
        self.assertIn("example.com", sec["allowed_domains"])

        self.store.add_denied_domain("badsite.org")
        sec2 = self.store.load_web_security_settings()
        self.assertIn("badsite.org", sec2["denied_domains"])

    def test_check_web_permission_trusted_domains(self):
        """Verify built-in trusted domains are allowed by default."""
        allowed, _ = check_web_permission("https://api.github.com/repos")
        self.assertTrue(allowed)

        allowed2, _ = check_web_permission("https://duckduckgo.com/html/")
        self.assertTrue(allowed2)

    def test_check_web_permission_interactive_prompt_allow(self):
        """Verify interactive handler returning True allows access."""
        calls = []

        def mock_handler(domain: str, url: str, action: str) -> bool:
            calls.append((domain, url, action))
            return True

        set_web_permission_handler(mock_handler)
        allowed, msg = check_web_permission("https://new-unknown-site.xyz/page", action="Test")
        self.assertTrue(allowed)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "new-unknown-site.xyz")

    def test_check_web_permission_interactive_prompt_deny(self):
        """Verify interactive handler returning False blocks access."""
        def mock_handler(domain: str, url: str, action: str) -> bool:
            return False

        set_web_permission_handler(mock_handler)
        allowed, msg = check_web_permission("https://forbidden-site.xyz/api", action="Test")
        self.assertFalse(allowed)
        self.assertIn("ผู้ใช้ไม่อนุญาต", msg)

    def test_builtin_fetch_web_blocked_by_guard(self):
        """Verify _builtin_fetch_web returns error message when access denied."""
        def mock_deny(domain: str, url: str, action: str) -> bool:
            return False

        set_web_permission_handler(mock_deny)
        res = _builtin_fetch_web("https://unapproved-domain.com/index.html")
        self.assertIn("ผู้ใช้ไม่อนุญาต", res)

    def test_builtin_http_request_blocked_by_guard(self):
        """Verify _builtin_http_request returns error message when access denied."""
        def mock_deny(domain: str, url: str, action: str) -> bool:
            return False

        set_web_permission_handler(mock_deny)
        res = _builtin_http_request("https://unapproved-domain.com/api", method="POST")
        self.assertIn("ผู้ใช้ไม่อนุญาต", res)


if __name__ == "__main__":
    unittest.main()
