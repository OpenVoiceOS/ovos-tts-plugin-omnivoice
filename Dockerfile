# OmniVoice as an OVOS TTS server.
#
# Runs the plugin behind ovos-tts-server on a CPU-only base. The OmniVoice model
# is multi-GB and downloads on first use into the mounted cache volume, so it is
# not baked into the image.
FROM python:3.11-slim

# System deps: libsndfile1 (soundfile), git/build tooling for any source wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        git \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# plugin + OmniVoice runtime + the OVOS TTS server.
# - CPU-only torch first so the multi-GB CUDA wheels never land in this CPU image.
# - setuptools<81 keeps ovos-plugin-manager's pkg_resources usage working.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir "setuptools<81" ".[gpu]" ovos-tts-server

RUN useradd -m -u 1000 ovos
USER ovos

EXPOSE 9666

# --cache persists synthesized audio across restarts. The selected language/voice
# is configured via mycroft.conf — see docs/docker.md.
ENTRYPOINT ["ovos-tts-server", "--engine", "ovos-tts-plugin-omnivoice", "--cache"]
