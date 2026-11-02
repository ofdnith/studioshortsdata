#!/usr/bin/env bash
# Baixa os modelos do Kokoro (voz) para models/. Uso: ./scripts/baixar_modelos.sh
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
mkdir -p models
for arquivo in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ -s "models/$arquivo" ]; then
    echo "ok: models/$arquivo já existe"
  else
    echo "baixando $arquivo..."
    curl -fL --progress-bar -o "models/$arquivo.part" "$BASE/$arquivo"
    mv "models/$arquivo.part" "models/$arquivo"
  fi
done
ls -lh models/
