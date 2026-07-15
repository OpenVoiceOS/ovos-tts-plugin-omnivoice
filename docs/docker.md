# Docker / OVOS TTS Server

The plugin ships an image that runs it as an
[`ovos-tts-server`](https://github.com/OpenVoiceOS/ovos-tts-server), with the
OmniVoice runtime (CPU torch) and the server preinstalled. The multi-GB OmniVoice
model downloads on first use into the mounted cache volume, so the image stays
lean and the model is fetched only once.

## Quick start

```bash
docker run -p 9666:9666 -v omnivoice-cache:/home/ovos/.cache \
  ghcr.io/openvoiceos/ovos-tts-plugin-omnivoice:latest
```

or with the bundled compose file:

```bash
docker compose up -d
```

Then synthesize:

```bash
curl "http://localhost:9666/synthesize/%D9%85%D8%B1%D8%AD%D8%A8%D8%A7?lang=ar-SA" --output hello.wav
# status check
curl http://localhost:9666/status
```

## What's in the image

| | |
|---|---|
| Base | `python:3.11-slim` |
| System | `libsndfile1` |
| Python | `ovos-tts-plugin-omnivoice[gpu]` (OmniVoice + CPU torch/torchaudio) + `ovos-tts-server` |
| Model | downloaded on first use into `/home/ovos/.cache` (persist via a volume) |
| Port | `9666` |

## Configuration

The language/voice comes from `mycroft.conf`. Mount one into the container to pick
an Arabic variety (or any of OmniVoice's 600+ languages):

```json
{
  "tts": {
    "ovos-tts-plugin-omnivoice": {
      "lang": "ar-SA"
    }
  }
}
```

```bash
docker run -p 9666:9666 \
  -v omnivoice-cache:/home/ovos/.cache \
  -v ./mycroft.conf:/home/ovos/.config/mycroft/mycroft.conf:ro \
  ghcr.io/openvoiceos/ovos-tts-plugin-omnivoice:latest
```

The published image is built and pushed to GHCR by `.github/workflows/docker.yml`
on every push to `dev` (tag `dev`) and `master` (tag `latest`), plus per-tag
releases.
