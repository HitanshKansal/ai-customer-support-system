# AI Customer Support & Ticket Automation System

An end-to-end customer support platform that combines policy-grounded RAG, database-backed support tools, conversation memory, authentication, and human escalation in one FastAPI service.

The project includes a small customer support console served by the API, a PostgreSQL/pgvector data layer, a LangGraph router, and a configurable OpenAI-compatible chat provider.

## Features

- Policy question answering with retrieval-augmented generation (RAG)
- Curated Markdown knowledge base for refunds, cancellations, shipping, payments, and FAQs
- Semantic embeddings and pgvector similarity search
- LangGraph intent routing for policy, order, payment, complex, and human-support requests
- Database-backed order lookup, payment lookup, ticket creation, and human escalation tools
- Conversation memory with remembered order context
- Customer registration, Argon2 password hashing, JWT access tokens, and protected chat
- Responsive customer support console at /
- Request IDs, structured request timing logs, security headers, configurable CORS, and rate limiting
- Alembic migrations and a test suite with a 75% minimum coverage gate

## Architecture

Browser
  |
  | HTML/CSS/JavaScript support console
  v
FastAPI
  |-- /auth/register, /auth/login, /auth/me
  |-- /agent/chat
  |-- /health
  |-- /docs
  |
  |-- JWT authentication
  |-- LangGraph intent router
  |-- RAG service -> embeddings -> pgvector
  |-- Support tools -> orders, payments, tickets, escalations
  |-- Conversation memory -> PostgreSQL
  |
PostgreSQL + pgvector       OpenAI-compatible LLM provider

## Requirements

- Python 3.12 or newer
- PostgreSQL 16 or newer with the vector extension
- An OpenAI-compatible chat provider and API key for live AI responses
- Docker Desktop is optional, not required

## Quick Start with Docker

Docker runs PostgreSQL with pgvector and the API together.

    Copy-Item .env.docker.example .env

Edit .env and set production-safe values, especially:

    JWT_SECRET_KEY=replace-with-a-long-random-secret
    LLM_API_KEY=your-provider-api-key

Start the stack:

    docker compose up --build -d
    docker compose exec api python -m backend.scripts.seed_knowledge_base

Open the application:

- Customer console: http://localhost:8000/
- Health check: http://localhost:8000/health
- Swagger API docs: http://localhost:8000/docs

Stop the stack:

    docker compose down

## Local Setup without Docker

Install PostgreSQL and make sure it is listening on port 5432. Create a database named support_db, then configure .env:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env

Set DATABASE_URL to the credentials used by your local PostgreSQL installation:

    DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/support_db
    JWT_SECRET_KEY=replace-with-a-long-random-secret
    LLM_API_KEY=your-provider-api-key

Apply migrations, load the knowledge base, and start the API:

    alembic upgrade head
    python -m backend.scripts.seed_knowledge_base
    uvicorn backend.app.main:app --reload

Open http://127.0.0.1:8000/.

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| DATABASE_URL | Async PostgreSQL connection URL | Local support_db URL |
| JWT_SECRET_KEY | Access-token signing secret | Development placeholder |
| JWT_ALGORITHM | JWT signing algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access-token lifetime | 60 |
| LLM_BASE_URL | OpenAI-compatible provider base URL | https://api.openai.com/v1 |
| LLM_API_KEY | LLM provider credential | Unset |
| LLM_MODEL | Chat model name | gpt-4o-mini |
| EMBEDDING_MODEL | Sentence-transformer model | sentence-transformers/all-MiniLM-L6-v2 |
| EMBEDDING_DIMENSION | Vector size for the embedding model | 384 |
| CORS_ORIGINS | Comma-separated allowed frontend origins | Same-origin only |
| RATE_LIMIT_MAX_REQUESTS | Requests per protected endpoint per window | 60 |
| RATE_LIMIT_WINDOW_SECONDS | Rate-limit window length | 60 |

Never commit .env or provider credentials. The .env.example files contain placeholders only.

## Using the Application

1. Open the customer console.
2. Create a customer account or sign in.
3. Ask a policy question, provide an order number, or request human support.
4. Review the assistant answer, route, and retrieved source names.

The chat endpoint accepts an optional order_number, ticket_id, and conversation_id. The agent can remember an order number from an earlier turn in the same conversation.

## API Surface

| Method | Endpoint | Purpose | Auth |
| --- | --- | --- | --- |
| GET | /health | Process health | No |
| POST | /auth/register | Create a customer account | No |
| POST | /auth/login | Get a JWT access token | No |
| GET | /auth/me | Get the current customer | Bearer token |
| POST | /agent/chat | Run an authenticated support request | Bearer token |
| GET | /docs | Interactive OpenAPI documentation | No |

## Testing

Run the full suite with coverage:

    python -m pytest

The configured test suite covers authentication, agent routing, tools, RAG, memory, migrations, API contracts, middleware, and failure paths. It requires at least 75% backend coverage.

## Project Layout

    backend/app/agent/        LangGraph routing, tools, memory, and runtime
    backend/app/api/          FastAPI routes, dependencies, and error handlers
    backend/app/auth/         Password hashing and JWT helpers
    backend/app/core/         Settings, logging, and HTTP middleware
    backend/app/db/           SQLAlchemy models, sessions, and metadata
    backend/app/knowledge/    Loading, embeddings, search, and RAG
    backend/app/llm/          OpenAI-compatible chat provider
    backend/scripts/          Operational scripts, including knowledge seeding
    frontend/                 Customer support console assets
    knowledge_base/           Curated policy Markdown documents
    alembic/                  Database migrations
    tests/                    Unit, API, agent, RAG, and integration-style tests
    docs/                     Architecture, setup, API, deployment, and demo guides

## Documentation

- Architecture: docs/architecture.md
- Setup Guide: docs/setup.md
- API Reference: docs/api.md
- Deployment Guide: docs/deployment.md
- Demo Preparation: docs/demo.md

## Production Notes

- Replace the development JWT secret before deployment.
- Keep the LLM API key on the server and restrict provider credentials.
- Configure CORS_ORIGINS explicitly when hosting the frontend separately.
- The built-in rate limiter is process-local. Use a shared gateway or Redis-backed limiter for multiple API replicas.
- Run migrations as a controlled deployment step and back up PostgreSQL before schema changes.
- Live chat requires a working PostgreSQL database, seeded knowledge base, and configured LLM provider.

## License

No license has been declared yet. Add a license before distributing the project publicly.

