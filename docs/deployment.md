# Deployment Guide

## Build and Run

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f api
```

The API image runs:

```text
alembic upgrade head
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Production Configuration

Set strong, environment-specific values for:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO` or `WARNING`
- `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`
- `CORS_ORIGINS` when the frontend is hosted on a separate origin
- `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`

Do not commit `.env` files or database credentials.

## Database Operations

Apply migrations:

```powershell
docker compose exec api alembic upgrade head
```

Seed curated knowledge documents:

```powershell
docker compose exec api python -m backend.scripts.seed_knowledge_base
```

Back up the named PostgreSQL volume or use managed PostgreSQL backups before production migrations.

## Health and Observability

- Container health checks call `/health`.
- Application logs include timestamps, severity, logger name, request IDs, paths, status codes, and duration.
- Responses include browser security headers and an `X-Request-ID` correlation header.
- Unexpected exceptions are logged server-side while clients receive safe error messages.

## Scaling Notes

- Run multiple API replicas behind a reverse proxy or load balancer.
- Use managed PostgreSQL for production durability.
- Keep database migrations as a separate controlled deployment step for larger environments.
- Use a shared model cache or external embedding service when scaling API replicas.
- The built-in rate limiter is process-local; use a shared gateway or Redis-backed limiter when running multiple replicas.
- Keep customer-specific operations behind authentication and verify CORS origins before exposing the service publicly.
