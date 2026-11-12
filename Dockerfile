# Akasavani - local text-to-speech web UI (container image, CPU by default)
FROM python:3.11-slim

# espeak-ng is required by several Coqui models (e.g. tts_models/en/vctk/vits).
# libgomp1 is needed by onnxruntime (the Piper Telugu engine).
# build-essential is needed if a dependency has to compile from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
        espeak-ng \
        libgomp1 \
        build-essential \
        git \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# App files + the speed-slider patch
COPY start_webui.py speak.py ./
COPY patches ./patches
COPY docker-entrypoint.sh ./

ENV COQUI_TOS_AGREED=1 \
    MODEL_NAME=tts_models/en/vctk/vits \
    PORT=5002

EXPOSE 5002

ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]
