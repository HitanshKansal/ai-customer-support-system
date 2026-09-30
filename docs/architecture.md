# Architecture

## System Overview

```text
Client
  |
  v
FastAPI
  |
  +--> Agent runtime --> LangGraph router
  |                         |
  |                         +--> RAG --> embeddings --> pgvector
  |                         +--> order/payment tools --> PostgreSQL
  |                         +--> ticket/escalation tools --> PostgreSQL
  |                         +--> conversation memory --> PostgreSQL
  |
  +--> Escalation API --> escalation workflow --> PostgreSQL
```

## Data Flow

```text
Policy document
  -> Markdown loader
  -> text chunks with overlap
  -> embedding model
  -> document_chunks.embedding
  -> pgvector cosine search
  -> attributed context
  -> chat model prompt
  -> grounded response
```

## Agent Routing

```text
Request
  -> classify_request
  -> policy       -> RAG
  -> order        -> check_order_status
  -> payment      -> check_payment_status
  -> complex      -> order lookup + ticket creation
  -> human        -> escalation workflow
  -> general      -> general response
```

## Persistence

- `users` stores customer and agent identities.
- `tickets` stores support issues.
- `orders` and `payments` store operational data used by tools.
- `conversation_messages` stores session history.
- `knowledge_documents` stores source policies.
- `document_chunks` stores chunk text and vectors.
- `escalations` tracks human-support lifecycle separately from tickets.

Alembic migrations are the source of truth for schema evolution. PostgreSQL provides relational storage; pgvector adds vector columns, operators, and the HNSW index.

## Boundaries

The agent runtime receives dependencies for RAG, tools, and memory. This keeps orchestration testable and allows provider replacement without changing routing logic.
