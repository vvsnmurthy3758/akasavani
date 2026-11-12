#!/usr/bin/env bash
# Apply the speed-slider patch, then start the TTS web server.
set -euo pipefail

SITE="$(python -c 'import os, TTS.server; print(os.path.dirname(TTS.server.__file__))')"
cp /app/patches/server.py "${SITE}/server.py"
cp /app/patches/index.html "${SITE}/templates/index.html"

echo "Starting TTS server (model=${MODEL_NAME:-tts_models/en/vctk/vits}, port=${PORT:-5002})"
exec tts-server --model_name "${MODEL_NAME:-tts_models/en/vctk/vits}" --port "${PORT:-5002}"
