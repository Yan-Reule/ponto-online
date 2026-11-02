#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if docker compose version >/dev/null 2>&1; then
  docker compose up --build
else
  docker build -t pontoface:local .
  mkdir -p data
  echo 'Abra http://localhost:8000. Pressione Ctrl+C para parar.'
  docker run --rm --name pontoface -p 127.0.0.1:8000:8000 \
    -v "$PWD/data:/app/data" -v pontoface-models:/models pontoface:local
fi
