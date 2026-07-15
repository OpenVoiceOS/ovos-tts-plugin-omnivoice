"""Language mapping for the OmniVoice OVOS TTS plugin.

OmniVoice is a massively-multilingual (600+ language) zero-shot TTS model. Its
:meth:`OmniVoice.generate` accepts a ``language`` argument that is either a
language *name* (e.g. ``"Standard Arabic"``) or an ISO-639-3 style *code* (the
model's own ``language_id``, e.g. ``"arb"``). OVOS speaks BCP-47 language tags
(e.g. ``"ar"``, ``"ar-SA"``, ``"en-US"``), so this module bridges the two.

The model does **not** ship a fixed catalogue of speakers. A "voice" is produced
either by *voice design* (a free-text ``instruct`` describing gender/age/pitch/
accent) or by *voice cloning* (a reference audio clip). The presets exposed to
OVOS therefore map to voice-design instructions, plus an ``auto`` voice that lets
the model pick a speaker itself.
"""

# BCP-47 (lower-cased) -> OmniVoice language_id (ISO-639-3 code the model knows).
# Arabic is the headline: OmniVoice was trained on 22 Arabic varieties, so every
# regional tag routes to the closest trained variety rather than collapsing to
# Modern Standard Arabic.
OMNIVOICE_LANG_MAP = {
    # --- Arabic varieties -------------------------------------------------
    "ar": "arb",        # Modern Standard Arabic (1483 h of training data)
    "ar-sa": "ars",     # Najdi Arabic (Saudi Arabia, 203 h)
    "ar-eg": "arz",     # Egyptian Arabic
    "ar-ma": "ary",     # Moroccan Arabic (Darija)
    "ar-dz": "arq",     # Algerian Arabic
    "ar-tn": "aeb",     # Tunisian Arabic
    "ar-ly": "ayl",     # Libyan Arabic
    "ar-sd": "apd",     # Sudanese Arabic
    "ar-lb": "apc",     # Levantine Arabic (Lebanon/Syria/Jordan/Palestine)
    "ar-sy": "apc",
    "ar-jo": "apc",
    "ar-ps": "apc",
    "ar-iq": "acm",     # Mesopotamian Arabic (Iraq)
    "ar-om": "acx",     # Omani Arabic
    "ar-ae": "afb",     # Gulf Arabic (UAE/Kuwait/Qatar/Bahrain, 98 h)
    "ar-kw": "afb",
    "ar-qa": "afb",
    "ar-bh": "afb",
    "ar-td": "shu",     # Chadian Arabic
    # --- a few common non-Arabic languages (600+ supported by the model) ---
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "ru": "ru",
    "zh": "zh",
    "zh-cn": "zh",
    "ja": "ja",
    "ko": "ko",
    "hi": "hi",
    "tr": "tr",
    "fa": "fa",
    "ur": "ur",
}


def resolve_language(lang: str) -> str:
    """Map an OVOS/BCP-47 tag to an OmniVoice ``language_id``.

    Falls back to the bare primary sub-tag (``"ar-xx"`` -> ``"ar"`` -> ``"arb"``),
    then to the raw code, and finally to ``None`` (language-agnostic mode) so an
    unknown tag never crashes synthesis.
    """
    if not lang:
        return None
    key = lang.lower().replace("_", "-")
    if key in OMNIVOICE_LANG_MAP:
        return OMNIVOICE_LANG_MAP[key]
    primary = key.split("-")[0]
    if primary in OMNIVOICE_LANG_MAP:
        return OMNIVOICE_LANG_MAP[primary]
    # Unknown: hand the primary sub-tag straight to the model, it may know it.
    return primary or None
