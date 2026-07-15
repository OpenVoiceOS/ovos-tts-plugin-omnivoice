# ovos-tts-plugin-omnivoice

TTS plugin for [OpenVoiceOS](https://openvoiceos.org) wrapping
[**OmniVoice**](https://github.com/k2-fsa/OmniVoice) — a massively-multilingual
(600+ language) zero-shot text-to-speech model from the k2-fsa / sherpa / icefall
team, built on a diffusion language-model architecture.

OmniVoice has no fixed speaker catalogue. It produces a voice in one of three
modes, all wired through this plugin:

| Mode | How | Plugin config |
|------|-----|---------------|
| **Auto** | model picks a speaker | `voice: "auto"` (default) |
| **Voice design** | describe the voice in free text | `voice: "female"`/`"male"`, or `instruct: "..."` |
| **Voice cloning** | clone a short reference clip | `ref_audio` (+ optional `ref_text`) |

The headline for this plugin is **Arabic**: OmniVoice was trained on **22 Arabic
varieties**, so every regional language tag routes to a distinct trained variety
instead of collapsing to Modern Standard Arabic.

## Arabic voices / language tags

Set the OVOS `lang` to one of these BCP-47 tags to reach the matching OmniVoice
variety (training hours in parentheses):

| `lang` | OmniVoice `language_id` | Variety |
|--------|------------------------|---------|
| **`ar`** | **`arb`** | **Modern Standard Arabic (1483 h)** |
| **`ar-SA`** | **`ars`** | **Najdi Arabic — Saudi (204 h)** |
| **`ar-AE`/`ar-KW`/`ar-QA`/`ar-BH`** | **`afb`** | **Gulf Arabic (99 h)** |
| **`ar-MA`** | **`ary`** | **Moroccan Arabic / Darija (105 h)** |
| **`ar-EG`** | **`arz`** | **Egyptian Arabic (23 h)** |
| **`ar-TN`** | **`aeb`** | **Tunisian Arabic (22 h)** |
| **`ar-LY`** | **`ayl`** | **Libyan Arabic (20 h)** |
| **`ar-DZ`** | **`arq`** | **Algerian Arabic (10 h)** |
| **`ar-SD`** | **`apd`** | **Sudanese Arabic (10 h)** |
| **`ar-LB`/`ar-SY`/`ar-JO`/`ar-PS`** | **`apc`** | **Levantine Arabic (16 h)** |
| **`ar-IQ`** | **`acm`** | **Mesopotamian Arabic (4 h)** |
| **`ar-OM`** | **`acx`** | **Omani Arabic (22 h)** |
| **`ar-TD`** | **`shu`** | **Chadian Arabic (2 h)** |

A selection of other languages is also mapped (`en`, `es`, `fr`, `de`, `it`,
`pt`, `ru`, `zh`, `ja`, `ko`, `hi`, `tr`, `fa`, `ur`); the underlying model
supports 600+, and any unmapped tag falls back to its primary sub-tag being
passed straight to the model.

> **Note on voice design for Arabic:** OmniVoice's voice-design (`instruct`) mode
> is trained mainly on English and Chinese. It generalizes to Arabic but is less
> stable than the **auto** voice or a **cloned** reference clip. For production
> Arabic, prefer `voice: "auto"` or supply `ref_audio`.

## Install

The plugin itself is lightweight. The OmniVoice runtime (PyTorch + the
`omnivoice` package, multi-GB) is an optional extra, so config/validation works
without it.

```bash
# 1. install a torch build for your hardware (see the OmniVoice README), e.g. CUDA:
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 \
    --extra-index-url https://download.pytorch.org/whl/cu128

# 2. install the plugin with the runtime extra
pip install ovos-tts-plugin-omnivoice[gpu]
```

Weights download automatically from `k2-fsa/OmniVoice` on the first synthesis.

## Configuration

`mycroft.conf`:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "ar-SA",
      "voice": "auto",
      "device": "cuda:0",
      "dtype": "float16",
      "num_step": 32
    }
  }
}
```

Config keys:

| Key | Default | Meaning |
|-----|---------|---------|
| `lang` | session lang | BCP-47 tag; mapped to an OmniVoice variety (table above) |
| `voice` | `auto` | `auto`, `female`, `male`, or a preset name |
| `instruct` | — | free-text voice-design string (overrides `voice`) |
| `ref_audio` | — | path to a 3–10 s reference clip → voice cloning mode |
| `ref_text` | — | transcript of `ref_audio` (auto-transcribed if omitted) |
| `device` | `cuda:0` | `cuda:0`, `cpu`, `mps`, or `xpu` |
| `dtype` | `float16` | torch dtype for the model |
| `num_step` | `32` | diffusion steps (16 = faster, 32 = higher quality) |
| `speed` | — | speaking-rate factor (>1 faster, <1 slower) |

Example: clone a Gulf-Arabic reference voice:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "ar-AE",
      "ref_audio": "/home/ovos/voices/gulf_ref.wav",
      "ref_text": "مرحبا بك في المساعد الصوتي"
    }
  }
}
```

## Serve it via ovos-tts-server

Install the server alongside this plugin, then point it at the module:

```bash
pip install ovos-tts-server ovos-tts-plugin-omnivoice[gpu]

ovos-tts-server \
    --engine ovos-tts-plugin-omnivoice \
    --port 9666 \
    --cache
```

Then request audio (the `lang` selects the Arabic variety):

```bash
# Modern Standard Arabic
curl -G "http://localhost:9666/synthesize/مرحبا" --data-urlencode "lang=ar" -o msa.wav

# Najdi (Saudi) Arabic
curl -G "http://localhost:9666/synthesize/مرحبا" --data-urlencode "lang=ar-SA" -o najdi.wav
```

## License

Apache-2.0. OmniVoice itself is distributed by the k2-fsa team under its own
license — see the [upstream repository](https://github.com/k2-fsa/OmniVoice).
