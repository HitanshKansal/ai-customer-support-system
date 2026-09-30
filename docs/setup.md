# Setup Guide

## Prerequisites

- Python 3.12 or newer.
- PostgreSQL 16 with pgvector, or Docker Desktop.
- Git and PowerShell on Windows.

## Docker Setup

```powershell
docker compose up --build
```

The API waits for PostgreSQL health, runs migrations, and starts on port `8000`.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to the local PostgreSQL connection string. Then run:

```powershell
alembic upgrade head
python -m backend.scripts.seed_knowledge_base
uvicorn backend.app.main:app --reload
```

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_NAME` | API title | `AI Customer Support API` |
| `APP_VERSION` | API version | `0.1.0` |
| `ENVIRONMENT` | Runtime environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATABASE_URL` | Async PostgreSQL URL | local support database |
| `EMBEDDING_MODEL` | Sentence-transformer model | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Vector dimension | `384` |
| `JWT_SECRET_KEY` | Signing secret for access tokens | development placeholder |
| `LLM_BASE_URL` | OpenAI-compatible provider URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | Provider credential | unset |
| `LLM_MODEL` | Chat model name | `gpt-4o-mini` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | same-origin only |
| `RATE_LIMIT_MAX_REQUESTS` | Requests per protected endpoint and window | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate-limit window length | `60` |

## Verification

```powershell
pytest
```

The configured suite requires at least 75% backend coverage.

## Troubleshooting

- If migrations cannot connect, verify PostgreSQL is running and `DATABASE_URL` is correct.
- If pgvector creation fails, use the `pgvector/pgvector:pg16` image or install the PostgreSQL extension.
- The first real embedding call may download the configured transformer model.
- The customer console is available at `http://localhost:8000/`. The first request can take longer while the embedding model downloads.
