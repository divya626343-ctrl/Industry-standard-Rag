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

echo "=== Downloading spaCy model ==="
python -m spacy download en_core_web_lg

echo "=== Starting Redis and Qdrant containers ==="
docker run -d --name redis -p 6379:6379 redis:latest
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

echo "=== Waiting for services to be healthy ==="
sleep 5
curl -sf http://localhost:6333/collections && echo " -> Qdrant OK"
redis-cli -h localhost ping && echo " -> Redis OK"

echo "=== Setup complete ==="