#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing system dependencies (LibreOffice, pandoc, TeX, fonts) ==="
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-impress \
    pandoc \
    texlive-xetex \
    texlive-fonts-recommended \
    fonts-dejavu-core

echo "=== Verifying tools are on PATH ==="
soffice --version
pandoc --version
xelatex --version

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt --break-system-packages

echo "=== Downloading spaCy small model (NOT en_core_web_lg -- 400MB, too slow/fragile to download) ==="
python -m spacy download en_core_web_sm

echo "=== Starting Redis and Qdrant via docker compose (uses compose.yaml -- redis-stack, correct container names) ==="
docker compose up -d redis qdrant

echo "=== Waiting for services to be healthy ==="
sleep 5
curl -sf http://localhost:6333/collections && echo " -> Qdrant OK"
docker exec rag_redis redis-cli ping && echo " -> Redis OK"
docker exec rag_redis redis-cli MODULE LIST | grep -q search && echo " -> RediSearch module loaded OK"

echo "=== Setup complete ==="