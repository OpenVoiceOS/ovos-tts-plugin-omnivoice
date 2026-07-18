"""OmniVoice TTS plugin for OpenVoiceOS.

`OmniVoice <https://github.com/k2-fsa/OmniVoice>`_ is a massively-multilingual
(600+ language) zero-shot TTS model from the k2-fsa / sherpa / icefall team. It
generates speech in three modes:

* **Voice cloning** — clone a speaker from a short reference clip (``ref_audio``).
* **Voice design** — describe the voice with a free-text ``instruct`` string
  (gender, age, pitch, accent...).
* **Auto** — let the model pick a voice by itself.

This plugin wires those modes through the standard OVOS ``TTS`` contract. Because
OmniVoice has no fixed speaker catalogue, the exposed "voices" are voice-design
presets, and Arabic is first-class: the model was trained on 22 Arabic varieties,
each reachable through a regional ``lang`` tag (see :mod:`.languages`).
"""

import logging

import soundfile as sf
from ovos_plugin_manager.templates.tts import TTS, TTSValidator
from ovos_utils import classproperty

from ovos_tts_plugin_omnivoice.languages import (
    OMNIVOICE_LANG_MAP,
    resolve_language,
)

LOG = logging.getLogger(__name__)


class OmniVoiceTTS(TTS):
    """OmniVoice zero-shot TTS plugin for OpenVoiceOS."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            audio_ext="wav",
            validator=OmniVoiceTTSValidator(self),
        )
        self.model_id = self.config.get("model", "k2-fsa/OmniVoice")
        # None => auto-detect at load time (CUDA if available, else CPU). This
        # keeps the plugin working on CPU-only hosts without extra config.
        self.device = self.config.get("device")
        self.dtype = self.config.get("dtype")
        # Generation controls (see docs/generation-parameters.md upstream).
        self.num_step = self.config.get("num_step", 32)
        self.speed = self.config.get("speed")
        # Voice-cloning inputs (optional; take precedence over voice design).
        self.ref_audio = self.config.get("ref_audio")
        self.ref_text = self.config.get("ref_text")
        # Voice-design instruction (optional). Falls back to the per-voice preset.
        self.instruct = self.config.get("instruct")
        # Named cloned voices. Two sources, merged (explicit map wins):
        # - "clone_voices": {"<voice_id>": {"ref_audio": path, "ref_text": str}}
        # - "clone_dir": a directory scanned for <voice_id>.wav + <voice_id>.txt
        #   pairs (the transcript file is optional but strongly recommended).
        # A request whose ``voice`` matches an entry synthesizes with that
        # reference clip, so a whole speaker roster is exposed by dropping
        # wav+txt pairs in the directory — no per-voice configuration.
        self.clone_voices = dict(self._scan_clone_dir(self.config.get("clone_dir")))
        self.clone_voices.update(self.config.get("clone_voices") or {})

        self._model = None
        # Lazy load so config/validator tests do not need the multi-GB weights.
        if not self.config.get("lazy", True):
            self._load_model()

    @staticmethod
    def _scan_clone_dir(path):
        """Yield ``(voice_id, {"ref_audio", "ref_text"})`` for wav/txt pairs in *path*."""
        if not path:
            return
        import os

        if not os.path.isdir(path):
            LOG.warning(f"clone_dir does not exist: {path}")
            return
        for name in sorted(os.listdir(path)):
            if not name.endswith(".wav"):
                continue
            voice_id = name[:-4]
            entry = {"ref_audio": os.path.join(path, name)}
            txt = os.path.join(path, voice_id + ".txt")
            if os.path.isfile(txt):
                with open(txt, encoding="utf-8") as f:
                    entry["ref_text"] = f.read().strip()
            yield voice_id, entry

    def _load_model(self):
        if self._model is not None:
            return
        import torch
        from omnivoice import OmniVoice

        device = self.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        dtype = self.dtype or ("float16" if str(device).startswith("cuda") else "float32")
        if isinstance(dtype, str):
            dtype = getattr(torch, dtype)
        LOG.info(f"Loading OmniVoice model {self.model_id} on {device} ({dtype})")
        self._model = OmniVoice.from_pretrained(
            self.model_id, device_map=device, dtype=dtype
        )

    @property
    def model(self):
        self._load_model()
        return self._model

    def _resolve_voice_design(self, voice, lang):
        """Return the ``instruct`` string for the requested voice, if any."""
        if self.instruct:
            return self.instruct
        # Look the voice up in the per-language preset table.
        for entry in OmniVoiceTTSConfig.get(_canonical(lang or ""), []):
            if entry.get("voice") == voice:
                return entry.get("meta", {}).get("instruct")
        return None

    def get_tts(self, sentence, wav_file, lang=None, voice=None):
        """Synthesize ``sentence`` to ``wav_file`` (24 kHz mono WAV).

        Args:
            sentence: text to synthesize.
            wav_file: destination WAV path.
            lang: BCP-47 language tag (e.g. ``"ar"``, ``"ar-SA"``, ``"en-US"``).
            voice: voice-design preset name (see :data:`OmniVoiceTTSConfig`).

        Returns:
            ``(wav_file, None)`` — OmniVoice produces no phoneme timing.
        """
        lang = lang or self.lang
        voice = voice or self.voice
        language = resolve_language(lang)

        gen_kwargs = {"text": sentence, "language": language, "num_step": self.num_step}
        if self.speed is not None:
            gen_kwargs["speed"] = self.speed

        clone = self.clone_voices.get(voice)
        if clone:
            # Named cloned voice (clone_voices / clone_dir).
            gen_kwargs["ref_audio"] = clone["ref_audio"]
            if clone.get("ref_text"):
                gen_kwargs["ref_text"] = clone["ref_text"]
        elif self.ref_audio:
            # Voice cloning mode.
            gen_kwargs["ref_audio"] = self.ref_audio
            if self.ref_text:
                gen_kwargs["ref_text"] = self.ref_text
        else:
            instruct = self._resolve_voice_design(voice, lang)
            if instruct:
                # Voice design mode.
                gen_kwargs["instruct"] = instruct
            # else: auto mode — the model picks a voice itself.

        audios = self.model.generate(**gen_kwargs)
        # generate() returns a list of 1-D float32 np.ndarray at model.sampling_rate.
        sr = getattr(self.model, "sampling_rate", 24000)
        sf.write(wav_file, audios[0], sr)
        return wav_file, None

    @classproperty
    def available_languages(cls) -> set:
        """BCP-47 tags with an explicit OmniVoice mapping (a subset of 600+)."""
        return set(OMNIVOICE_LANG_MAP.keys())


class OmniVoiceTTSValidator(TTSValidator):
    """Validator for the OmniVoice plugin."""

    def validate_lang(self):
        # OmniVoice is language-agnostic-capable, so any tag is acceptable; the
        # primary sub-tag is always resolvable. Nothing to reject here.
        assert resolve_language(self.tts.lang) is not None

    def validate_connection(self):
        # No network service; weights load lazily on first synthesis.
        pass

    def validate_dependencies(self):
        try:
            import omnivoice  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "OmniVoice is not installed. Install it with "
                "`pip install ovos-tts-plugin-omnivoice[gpu]` (or install torch "
                "and `omnivoice` manually per the upstream instructions)."
            ) from exc

    def get_tts_class(self):
        return OmniVoiceTTS


def _design(gender, extra="", *, priority=50):
    """Build a voice-design instruct string + OVOS voice meta."""
    instruct = gender if not extra else f"{gender}, {extra}"
    return {
        "voice": gender if not extra else f"{gender}-{extra.replace(', ', '-').replace(' ', '_')}",
        "instruct": instruct,
        "gender": gender,
        "priority": priority,
    }


def _voices(lang, *designs):
    out = []
    for d in designs:
        out.append(
            {
                "voice": d["voice"],
                "lang": lang,
                "meta": {
                    "display_name": f"OmniVoice {lang} {d['voice']}",
                    "offline": True,
                    "gender": d["gender"],
                    "priority": d["priority"],
                    "instruct": d["instruct"],
                },
            }
        )
    # Every language also gets an "auto" voice (model picks the speaker).
    out.append(
        {
            "voice": "auto",
            "lang": lang,
            "meta": {
                "display_name": f"OmniVoice {lang} auto",
                "offline": True,
                "gender": "unknown",
                "priority": 60,
                "instruct": None,
            },
        }
    )
    return out


# Voice-design presets exposed to OVOS. Voice design is trained mainly on English
# and Chinese; for Arabic (and other languages) it generalizes but the most robust
# path is the "auto" voice or a cloned reference clip. Presets cover the common
# gender request; extend via the `instruct` config option for finer control.
_DESIGNS = (_design("female"), _design("male"))

# Arabic-first language table. Each Arabic tag routes to a distinct trained
# variety (see languages.OMNIVOICE_LANG_MAP).
def _canonical(tag):
    """Present language tags in canonical BCP-47 form (``ar-sa`` -> ``ar-SA``)."""
    parts = tag.split("-")
    if len(parts) == 2:
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return tag.lower()


OmniVoiceTTSConfig = {
    _canonical(lang): _voices(_canonical(lang), *_DESIGNS)
    for lang in OMNIVOICE_LANG_MAP.keys()
}


class OmniVoiceTTSPluginConfig(dict):
    """`opm.tts.config` entry point: advertises languages/voices to OVOS."""

    def __new__(cls):
        return OmniVoiceTTSConfig
