# Dockerfile
FROM python:3.10-slim-bookworm

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-core \
    libreoffice-writer \
    libreoffice-impress \
    pandoc \
    texlive-xetex \
    texlive-latex-recommended \
    lmodern \
    texlive-fonts-recommended \
    fonts-dejavu-core \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 \
    -r requirements.txt
RUN python -m spacy download en_core_web_sm


COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "FastAPI.main:app", "--host", "0.0.0.0", "--port", "8000"]