"""
tests/test_media_providers.py — Unit tests for GPT Image, NAI Image, Grok Image, and media generation.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from core.provider_profiles import (
        default_profiles,
        GPT_IMAGE_MODELS,
        NAI_IMAGE_MODELS,
        GROK_IMAGE_MODELS,
    )
    import core.mcp.builtins.media_tools as media_tools_mod
    from core.mcp.builtins.media_tools import (
        _get_image_provider_credentials,
        _generate_image_via_maxplus,
        _builtin_generate_image,
        get_media_tools,
    )
except (ImportError, ModuleNotFoundError):
    from src.core.provider_profiles import (  # type: ignore[no-redef]
        default_profiles,
        GPT_IMAGE_MODELS,
        NAI_IMAGE_MODELS,
        GROK_IMAGE_MODELS,
    )
    import src.core.mcp.builtins.media_tools as media_tools_mod  # type: ignore[no-redef]
    from src.core.mcp.builtins.media_tools import (  # type: ignore[no-redef]
        _get_image_provider_credentials,
        _generate_image_via_maxplus,
        _builtin_generate_image,
        get_media_tools,
    )


class TestMediaProviders(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_default_profiles_include_image_providers(self):
        profiles = default_profiles()
        ids = [p["id"] for p in profiles]
        self.assertIn("maxplus-gpt-image", ids)
        self.assertIn("maxplus-nai-image", ids)
        self.assertIn("maxplus-grok-image", ids)
        self.assertIn("maxplus-native", ids)

        gpt_prof = next(p for p in profiles if p["id"] == "maxplus-gpt-image")
        self.assertEqual(gpt_prof["base_url"], "https://api.maxplus-ai.cc/gpt-image/v1")
        self.assertEqual(gpt_prof["models"], list(GPT_IMAGE_MODELS))

        nai_prof = next(p for p in profiles if p["id"] == "maxplus-nai-image")
        self.assertEqual(nai_prof["base_url"], "https://api.maxplus-ai.cc/nai-image/v1")
        self.assertEqual(nai_prof["models"], list(NAI_IMAGE_MODELS))
        self.assertEqual(nai_prof["model"], "nai-diffusion-4-5-full")

        grok_prof = next(p for p in profiles if p["id"] == "maxplus-grok-image")
        self.assertEqual(grok_prof["base_url"], "https://api.maxplus-ai.cc/grok-image/v1")
        self.assertEqual(grok_prof["models"], list(GROK_IMAGE_MODELS))
        self.assertEqual(grok_prof["model"], "grok-imagine-image-2.0")

        native_prof = next(p for p in profiles if p["id"] == "maxplus-native")
        self.assertEqual(native_prof["base_url"], "https://api.maxplus-ai.cc/v1")
        self.assertIn("sonnet-4-5", native_prof["models"])
        self.assertIn("haiku", native_prof["models"])

    def test_get_image_provider_credentials_urls(self):
        gpt_url, _ = _get_image_provider_credentials("gpt-image")
        self.assertEqual(gpt_url, "https://api.maxplus-ai.cc/gpt-image/v1")

        nai_url, _ = _get_image_provider_credentials("nai-image")
        self.assertEqual(nai_url, "https://api.maxplus-ai.cc/nai-image/v1")

        grok_url, _ = _get_image_provider_credentials("grok-image")
        self.assertEqual(grok_url, "https://api.maxplus-ai.cc/grok-image/v1")

    @patch("urllib.request.urlopen")
    def test_generate_image_via_maxplus_b64(self, mock_urlopen):
        with patch.object(media_tools_mod, "_get_image_provider_credentials", return_value=("https://api.maxplus-ai.cc/gpt-image/v1", "test-key-123")):
            import base64

            fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
            fake_b64 = base64.b64encode(fake_png).decode("ascii")

            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "data": [{"b64_json": fake_b64}]
            }).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            out_path = Path(self.temp_dir.name) / "test_out.png"
            ok, msg = _generate_image_via_maxplus(
                provider="gpt-image",
                prompt="A futuristic flying car",
                out_file=out_path,
                width=1024,
                height=1024,
                model="dall-e-3",
            )

            self.assertTrue(ok)
            self.assertIn("สร้างรูปภาพระดับพรีเมียมสำเร็จด้วย GPT-IMAGE", msg)
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.read_bytes(), fake_png)

    def test_builtin_generate_image_auto_provider_dispatch(self):
        with patch.object(media_tools_mod, "_generate_image_via_maxplus", return_value=(True, "Mocked GPT-IMAGE Success")) as mock_gen:
            out_path = os.path.join(self.temp_dir.name, "gpt.png")

            res = _builtin_generate_image(
                prompt="A lovely cute kitten",
                output_path=out_path,
                model="dall-e-3",
                provider="auto",
            )
            self.assertIn("Mocked GPT-IMAGE Success", res)
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            self.assertEqual(kwargs.get("provider"), "gpt-image")

    def test_builtin_generate_image_nai_dispatch(self):
        with patch.object(media_tools_mod, "_generate_image_via_maxplus", return_value=(True, "Mocked NAI Success")) as mock_gen:
            out_path = os.path.join(self.temp_dir.name, "anime.png")

            res = _builtin_generate_image(
                prompt="Anime magical girl, sparkling eyes",
                output_path=out_path,
                model="nai-diffusion-3",
                provider="auto",
            )
            self.assertIn("Mocked NAI Success", res)
            args, kwargs = mock_gen.call_args
            self.assertEqual(kwargs.get("provider"), "nai-image")

    def test_media_tools_registered_with_new_options(self):
        tools = get_media_tools()
        self.assertIn("generate_image", tools)
        tool, _ = tools["generate_image"]
        schema = tool.input_schema
        props = schema["properties"]
        self.assertIn("provider", props)
        self.assertIn("quality", props)
        self.assertIn("style", props)


if __name__ == "__main__":
    unittest.main()
