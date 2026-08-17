# Industry-Standard RAG Platform

A production-style Retrieval-Augmented Generation backend — FastAPI + LangGraph guardrail pipeline + Celery background ingestion + Qdrant hybrid search + Redis session/state management.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Desktop, or Engine + Compose plugin on Linux)
- Python 3.10
- A Groq API key (LLM calls)
- A Backblaze B2 (or S3-compatible) bucket + credentials (document storage)

---

## 1. Clone the repo

```bash
git clone <your-repo-url>
cd <repo-folder>
```

## 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your actual values (Groq API key, object storage credentials, etc.). See `.env.example` for the full list of required variables.

## 3. Start Redis and Qdrant

```bash
docker compose up -d
```

This starts:
- **Redis** (`redis/redis-stack` — required for RediSearch/RedisJSON, used by session state and LangGraph checkpointing) on `localhost:6379`
- **Qdrant** (vector store) on `localhost:6333`

Verify both are healthy:

```bash
docker exec -it rag_redis redis-cli ping        # expect: PONG
curl http://localhost:6333/collections           # expect: {"result":{"collections":[]}...}
```

> **Using Qdrant Cloud instead?** Skip the `qdrant` service in `docker-compose.yml` and set `QDRANT_ENDPOINT` + `QDRANT_API_KEY` in `.env` to your cloud cluster's values instead.

## 4. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**System dependencies** (for document conversion — DOCX/PPTX → PDF):

```bash
sudo apt-get install -y libreoffice-writer libreoffice-impress fonts-crosextra-carlito fonts-crosextra-caladea
```

(macOS: `brew install --cask libreoffice`; Windows: install LibreOffice directly and ensure `soffice` is on your PATH)

## 5. Run FastAPI

```bash
uvicorn FastAPI.main:app --reload --host 0.0.0.0 --port 8000
```

## 6. Run the Celery worker (separate terminal)

Background document ingestion (parsing, chunking, embedding) runs through Celery, not inline in the request:

```bash
celery -A Rag_backend.workers.celery_app worker --loglevel=info
```

*(On Windows, add `--pool=solo` — Celery's default prefork pool isn't reliable on Windows.)*

## 7. (Optional) Run Celery Beat

Only needed if you want the periodic inactive-session cleanup to run:

```bash
celery -A Rag_backend.workers.celery_app beat --loglevel=info
```

---

## Explore the API

Once FastAPI is running, open the interactive docs in your browser:

```
http://localhost:8000/docs
```

This gives you a full list of every endpoint, request/response schemas, and a "Try it out" button to call them directly — no separate client needed to explore what the API can do.

A quick health check:

```bash
curl http://localhost:8000/health
```

---

## Typical flow to try it out

1. `POST /session/init` → get a `session_id`
2. `POST /upload` (multipart file + `session_id`) → get a `task_id`
3. `GET /task-status/{task_id}` → poll until `SUCCESS`
4. `POST /query` (`{"query": "...", "session_id": "..."}`) → streams back status updates and the final answer (SSE)

---

## Project structure

```
Rag_backend/       core pipeline: ingestion, chunking, embedding, LangGraph guardrail nodes, data store clients
FastAPI/            API routes
workers/            Celery app + tasks (ingestion, session sweep)
docker-compose.yml  Redis + Qdrant
requirements.txt    Python dependencies
.env.example        required environment variables
```

---

## Notes

- Sessions are anonymous and ephemeral — no login, no persisted chat history across a browser refresh, by design.
- Supported upload formats: `pdf`, `docx`, `pptx`.
- Document conversion uses LibreOffice under the hood — make sure it's installed and `soffice` is reachable on your PATH before uploading `.docx`/`.pptx` files.
