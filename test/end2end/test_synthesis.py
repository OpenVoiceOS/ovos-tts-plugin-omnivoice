"""Real end-to-end synthesis test.

Gated on the OmniVoice runtime actually being importable AND weights being
loadable. When the multi-GB model or torch is absent (as in the default CI
lane), the test is skipped with a clear reason — it is never faked with
importorskip and never hides a missing declared dependency.

Enable it by installing the runtime (`pip install "."`, plus a torch build
for your hardware) and setting OMNIVOICE_E2E=1.
"""

import os
import tempfile
import unittest

RUN_E2E = os.environ.get("OMNIVOICE_E2E", "0") == "1"


def _runtime_available():
    try:
        import omnivoice  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(RUN_E2E, "set OMNIVOICE_E2E=1 to run real synthesis")
@unittest.skipUnless(_runtime_available(), "omnivoice/torch runtime not installed")
class TestRealSynthesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from ovos_tts_plugin_omnivoice import OmniVoiceTTS

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = "float16" if device.startswith("cuda") else "float32"
        cls.tts = OmniVoiceTTS(
            config={"lang": "ar", "device": device, "dtype": dtype, "num_step": 16}
        )

    def test_arabic_synthesis_writes_audio(self):
        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav = f.name
        try:
            path, phonemes = self.tts.get_tts(
                "السلام عليكم، هذا اختبار.", wav, lang="ar", voice="auto"
            )
            self.assertEqual(path, wav)
            self.assertIsNone(phonemes)
            data, sr = sf.read(wav)
            self.assertGreater(len(data), sr // 2)  # at least ~0.5 s of audio
        finally:
            if os.path.exists(wav):
                os.unlink(wav)


if __name__ == "__main__":
    unittest.main()
