# ovos-tts-plugin-omnivoice

TTS plugin for [OpenVoiceOS](https://openvoiceos.org) wrapping
[**OmniVoice**](https://github.com/k2-fsa/OmniVoice) — a massively-multilingual
(**600+ language**) zero-shot text-to-speech model from the k2-fsa / sherpa /
icefall team, built on a diffusion language-model architecture.

OmniVoice has no fixed speaker catalogue. It produces a voice in one of three
modes, all wired through this plugin:

| Mode | How | Plugin config |
|------|-----|---------------|
| **Auto** | model picks a speaker | `voice: "auto"` (default) |
| **Voice design** | describe the voice in free text | `voice: "female"`/`"male"`, or `instruct: "..."` |
| **Voice cloning** | clone a short reference clip | `ref_audio` (+ optional `ref_text`) |

## Languages

OmniVoice supports **600+ languages**. This plugin ships explicit BCP-47 → model
`language_id` mappings for the languages below; any other tag falls back to its
primary sub-tag being passed straight to the model, so unmapped languages still
work if the model knows them.

| `lang` | `language_id` | Language |
|--------|---------------|----------|
| `en`, `en-US`, `en-GB` | `en` | English |
| `es` | `es` | Spanish |
| `fr` | `fr` | French |
| `de` | `de` | German |
| `it` | `it` | Italian |
| `pt` | `pt` | Portuguese |
| `ru` | `ru` | Russian |
| `zh`, `zh-CN` | `zh` | Chinese |
| `ja` | `ja` | Japanese |
| `ko` | `ko` | Korean |
| `hi` | `hi` | Hindi |
| `tr` | `tr` | Turkish |
| `fa` | `fa` | Persian |
| `ur` | `ur` | Urdu |

Set the OVOS `lang` (or per-request `lang`) to any of these tags. To reach one of
the 600+ languages that isn't mapped here, pass its ISO code as the `lang` — the
model accepts a language name (`"English"`) or code (`"en"`) directly.

### Arabic varieties

OmniVoice was trained on many Arabic varieties, so regional Arabic tags route to a
distinct trained variety instead of collapsing to Modern Standard Arabic:

| `lang` | `language_id` | Variety |
|--------|---------------|---------|
| `ar` | `arb` | Modern Standard Arabic |
| `ar-SA` | `ars` | Najdi (Saudi) |
| `ar-AE`, `ar-KW`, `ar-QA`, `ar-BH` | `afb` | Gulf |
| `ar-MA` | `ary` | Moroccan / Darija |
| `ar-EG` | `arz` | Egyptian |
| `ar-TN` | `aeb` | Tunisian |
| `ar-LY` | `ayl` | Libyan |
| `ar-DZ` | `arq` | Algerian |
| `ar-SD` | `apd` | Sudanese |
| `ar-LB`, `ar-SY`, `ar-JO`, `ar-PS` | `apc` | Levantine |
| `ar-IQ` | `acm` | Mesopotamian |
| `ar-OM` | `acx` | Omani |
| `ar-TD` | `shu` | Chadian |

> **Voice design across languages:** OmniVoice's voice-design (`instruct`) mode is
> trained mainly on English and Chinese. It generalizes to other languages but is
> less stable than the **auto** voice or a **cloned** reference clip. For the most
> robust output in other languages, prefer `voice: "auto"` or supply `ref_audio`.

## Install

The OmniVoice runtime (PyTorch + the multi-GB `omnivoice` package) is a core
dependency, so a plain install is enough to synthesize:

```bash
pip install ovos-tts-plugin-omnivoice
```

It runs on **CPU or GPU** — a GPU is optional (faster), **not required**. The
default install pulls PyPI's default torch build (CPU-capable). To target a
specific accelerator, reinstall torch from the matching index:

```bash
# NVIDIA CUDA:
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 \
    --extra-index-url https://download.pytorch.org/whl/cu128
# ...or AMD ROCm:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
# ...or a slim CPU-only build:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

The plugin auto-detects the device (CUDA/ROCm if available, else CPU). Weights
download automatically from `k2-fsa/OmniVoice` on the first synthesis.

## Configuration

`mycroft.conf`:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "en",
      "voice": "auto",
      "num_step": 32
    }
  }
}
```

Config keys:

| Key | Default | Meaning |
|-----|---------|---------|
| `lang` | session lang | BCP-47 tag; mapped to an OmniVoice `language_id` (tables above) |
| `voice` | `auto` | `auto`, `female`, `male`, or a preset name |
| `instruct` | — | free-text voice-design string (overrides `voice`) |
| `ref_audio` | — | path to a 3–10 s reference clip → voice cloning mode |
| `ref_text` | — | transcript of `ref_audio` (auto-transcribed if omitted) |
| `clone_dir` | — | directory of `<voice_id>.wav` (+ optional `<voice_id>.txt`) pairs; each becomes a selectable cloned voice |
| `clone_voices` | — | explicit map `{voice_id: {ref_audio, ref_text}}`; overrides `clone_dir` entries |
| `device` | auto | `cuda:0`, `cpu`, `mps`, or `xpu`; auto-detected (CUDA if available, else CPU) |
| `dtype` | auto | torch dtype; `float16` on CUDA, `float32` on CPU |
| `num_step` | `32` | diffusion steps (16 = faster, 32 = higher quality) |
| `speed` | — | speaking-rate factor (>1 faster, <1 slower) |

Example: clone a reference voice:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "en",
      "ref_audio": "/home/ovos/voices/ref.wav",
      "ref_text": "Welcome to the voice assistant."
    }
  }
}
```

### Named cloned voices (a speaker roster)

`ref_audio` clones one global voice. To expose a whole roster of cloned speakers,
point `clone_dir` at a directory of reference pairs:

```
/home/ovos/voices/
├── speaker6_male.wav      # 3–10 s reference clip
├── speaker6_male.txt      # its transcript (optional, recommended)
├── speaker3_female.wav
└── speaker3_female.txt
```

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "ar",
      "clone_dir": "/home/ovos/voices"
    }
  }
}
```

Every `<voice_id>.wav` becomes a selectable voice: a request with
`voice="speaker6_male"` synthesizes with that reference clip. Adding a speaker is
dropping in another wav+txt pair — no config change. Voice ids that match no pair
fall back to the voice-design presets as before.

For custom naming or refs outside a single directory, `clone_voices` maps ids
explicitly and wins over scanned entries:

```json
{
  "tts": {
    "module": "ovos-tts-plugin-omnivoice",
    "ovos-tts-plugin-omnivoice": {
      "lang": "ar",
      "clone_dir": "/home/ovos/voices",
      "clone_voices": {
        "sarah": {"ref_audio": "/mnt/refs/agent.wav", "ref_text": "مرحبا بك"}
      }
    }
  }
}
```

Through `ovos-tts-server`'s ElevenLabs-compatible API the voice id travels in the
URL path, so each cloned speaker is reachable as
`/elevenlabs/v1/text-to-speech/<voice_id>`.

## Serve it via ovos-tts-server

Install the server alongside this plugin, then point it at the module:

```bash
pip install ovos-tts-server ovos-tts-plugin-omnivoice

ovos-tts-server \
    --engine ovos-tts-plugin-omnivoice \
    --port 9666 \
    --cache
```

Then request audio (the `lang` selects the language / variety):

```bash
# English
curl -G "http://localhost:9666/synthesize/hello there" --data-urlencode "lang=en" -o en.wav

# Modern Standard Arabic
curl -G "http://localhost:9666/synthesize/مرحبا" --data-urlencode "lang=ar" -o msa.wav

# Najdi (Saudi) Arabic
curl -G "http://localhost:9666/synthesize/مرحبا" --data-urlencode "lang=ar-SA" -o najdi.wav
```

### Docker

A batteries-included image runs the plugin as an `ovos-tts-server`:

```bash
docker run -p 9666:9666 -v omnivoice-cache:/home/ovos/.cache \
  ghcr.io/openvoiceos/ovos-tts-plugin-omnivoice:latest
```

The image is built and pushed to GHCR on every push to `dev`/`master`. See
[docs/docker.md](docs/docker.md) for configuration and the bundled
`docker-compose.yml`.

## License

Apache-2.0. OmniVoice itself is distributed by the k2-fsa team under its own
license — see the [upstream repository](https://github.com/k2-fsa/OmniVoice).
</content>
