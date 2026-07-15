"""Unit tests for ovos-tts-plugin-omnivoice.

These run in CI without downloading any model weights: the OmniVoice runtime is
mocked, so only the plugin's config/lang/voice wiring is exercised.
"""

import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np


class TestLanguageMapping(unittest.TestCase):
    def test_arabic_varieties_map_to_distinct_ids(self):
        from ovos_tts_plugin_omnivoice.languages import resolve_language

        self.assertEqual(resolve_language("ar"), "arb")       # MSA
        self.assertEqual(resolve_language("ar-SA"), "ars")    # Najdi
        self.assertEqual(resolve_language("ar-EG"), "arz")    # Egyptian
        self.assertEqual(resolve_language("ar-MA"), "ary")    # Moroccan
        self.assertEqual(resolve_language("ar-AE"), "afb")    # Gulf
        self.assertEqual(resolve_language("ar-LB"), "apc")    # Levantine

    def test_underscore_and_case_normalised(self):
        from ovos_tts_plugin_omnivoice.languages import resolve_language

        self.assertEqual(resolve_language("AR_eg"), "arz")

    def test_unknown_region_falls_back_to_primary(self):
        from ovos_tts_plugin_omnivoice.languages import resolve_language

        self.assertEqual(resolve_language("ar-ZZ"), "arb")

    def test_unknown_language_returns_primary_subtag(self):
        from ovos_tts_plugin_omnivoice.languages import resolve_language

        self.assertEqual(resolve_language("xx-YY"), "xx")

    def test_empty_is_language_agnostic(self):
        from ovos_tts_plugin_omnivoice.languages import resolve_language

        self.assertIsNone(resolve_language(""))


class TestConfig(unittest.TestCase):
    def test_config_advertises_arabic(self):
        from ovos_tts_plugin_omnivoice import OmniVoiceTTSConfig

        self.assertIn("ar", OmniVoiceTTSConfig)
        self.assertIn("ar-SA", OmniVoiceTTSConfig)
        voices = [v["voice"] for v in OmniVoiceTTSConfig["ar"]]
        self.assertIn("auto", voices)
        self.assertIn("female", voices)
        self.assertIn("male", voices)

    def test_config_entrypoint_returns_dict(self):
        from ovos_tts_plugin_omnivoice import (
            OmniVoiceTTSConfig,
            OmniVoiceTTSPluginConfig,
        )

        self.assertIs(OmniVoiceTTSPluginConfig(), OmniVoiceTTSConfig)

    def test_every_language_has_an_auto_voice(self):
        from ovos_tts_plugin_omnivoice import OmniVoiceTTSConfig

        for lang, voices in OmniVoiceTTSConfig.items():
            self.assertIn("auto", [v["voice"] for v in voices], lang)


class TestPlugin(unittest.TestCase):
    """Exercise the plugin with a fully mocked OmniVoice runtime."""

    def _make_tts(self, config=None):
        from ovos_tts_plugin_omnivoice import OmniVoiceTTS

        tts = OmniVoiceTTS(config=config or {"lang": "ar"})
        mock_model = MagicMock()
        mock_model.sampling_rate = 24000
        mock_model.generate.return_value = [
            np.zeros(2400, dtype=np.float32)
        ]
        tts._model = mock_model  # inject to skip real load
        return tts, mock_model

    def test_get_tts_writes_wav_and_returns_none_phonemes(self):
        tts, model = self._make_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            path, phonemes = tts.get_tts("مرحبا", f.name, lang="ar")
            self.assertEqual(path, f.name)
            self.assertIsNone(phonemes)
            import soundfile as sf

            data, sr = sf.read(f.name)
            self.assertEqual(sr, 24000)
            self.assertGreater(len(data), 0)

    def test_arabic_lang_passed_as_omnivoice_id(self):
        tts, model = self._make_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            tts.get_tts("مرحبا", f.name, lang="ar-EG")
        kwargs = model.generate.call_args.kwargs
        self.assertEqual(kwargs["language"], "arz")

    def test_voice_design_preset_resolves_to_instruct(self):
        tts, model = self._make_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            tts.get_tts("مرحبا", f.name, lang="ar", voice="female")
        kwargs = model.generate.call_args.kwargs
        self.assertEqual(kwargs.get("instruct"), "female")

    def test_auto_voice_sends_no_instruct(self):
        tts, model = self._make_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            tts.get_tts("مرحبا", f.name, lang="ar", voice="auto")
        kwargs = model.generate.call_args.kwargs
        self.assertNotIn("instruct", kwargs)

    def test_ref_audio_config_selects_cloning_mode(self):
        tts, model = self._make_tts(
            config={"lang": "ar", "ref_audio": "/tmp/ref.wav", "ref_text": "hi"}
        )
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            tts.get_tts("مرحبا", f.name, lang="ar", voice="female")
        kwargs = model.generate.call_args.kwargs
        self.assertEqual(kwargs["ref_audio"], "/tmp/ref.wav")
        self.assertEqual(kwargs["ref_text"], "hi")
        self.assertNotIn("instruct", kwargs)

    def test_validator_accepts_any_lang(self):
        from ovos_tts_plugin_omnivoice import OmniVoiceTTSValidator

        tts, _ = self._make_tts(config={"lang": "ar-SA"})
        OmniVoiceTTSValidator(tts).validate_lang()


if __name__ == "__main__":
    unittest.main()
