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
| Python | `ovos-tts-plugin-omnivoice` (OmniVoice + CPU torch/torchaudio built in) + `ovos-tts-server` |
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

## GPU (AMD ROCm)

A second image variant runs synthesis on an **AMD Radeon GPU**. It is identical
to the CPU image except torch/torchaudio come from PyTorch's ROCm index. Because
torch-ROCm reports itself through the CUDA API, the plugin's device
auto-detection picks the GPU (float16) with no extra config — `get_tts` runs on
`cuda:0`.

The workflow publishes it alongside the CPU image with a **`-rocm` suffix**:
`…:dev-rocm`, `…:latest-rocm`, and `…:<version>-rocm`.

The GPU must be passed into the container, and (for cards not on torch-ROCm's
official gfx list) masqueraded via `HSA_OVERRIDE_GFX_VERSION`. The bundled
`docker-compose.gpu.yml` override does all of this:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Equivalent `docker run`:

```bash
docker run -p 9666:9666 \
  --device /dev/kfd --device /dev/dri \
  --group-add "$(getent group render | cut -d: -f3)" \
  --group-add "$(getent group video  | cut -d: -f3)" \
  --security-opt seccomp=unconfined --ipc host \
  -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  -v omnivoice-cache:/home/ovos/.cache \
  ghcr.io/openvoiceos/ovos-tts-plugin-omnivoice:dev-rocm
```

| | |
|---|---|
| Base | `python:3.11-slim` + torch/torchaudio from `…/whl/rocm6.2` |
| Devices | `/dev/kfd`, `/dev/dri` (host `render`/`video` groups) |
| Env | `HSA_OVERRIDE_GFX_VERSION` for unlisted gfx targets |
| Tags | `dev-rocm`, `latest-rocm`, `<version>-rocm` |

### `HSA_OVERRIDE_GFX_VERSION`

torch-ROCm ships kernels only for a fixed set of gfx targets. A card outside
that set (e.g. the RX 7600 / Navi 33 / **gfx1102**) must masquerade as a
supported one — `11.0.0` makes it present as gfx1100 (Navi 31), which is
shipped. Set it to match your card, or drop it entirely for a natively-supported
GPU. Verify the GPU was actually selected:

```bash
docker exec <container> python -c \
  "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# True Radeon RX 7600
```

To build the ROCm image locally instead of pulling it, uncomment the `build:`
block in `docker-compose.gpu.yml`, or:

```bash
docker build -f Dockerfile.rocm -t ovos-tts-plugin-omnivoice:rocm .
```

Adjust the ROCm wheel index with `--build-arg ROCM_INDEX=rocm6.3` if a different
ROCm build matches your host driver better.
