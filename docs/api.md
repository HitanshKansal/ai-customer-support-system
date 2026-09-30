# API Reference

Interactive OpenAPI documentation is available at `/docs` when the API is running.

## Health

### `GET /health`

Returns basic service information.

Example response:

```json
{
  "status": "ok",
  "service": "AI Customer Support API",
  "version": "0.1.0",
  "environment": "development"
}
```

## Create Escalation

### `POST /escalations`

Creates or refreshes a human-support escalation. If `ticket_id` is omitted, the service creates an urgent support ticket first.

Request:

```json
{
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "reason": "The customer requested a human agent.",
  "ticket_id": null
}
```

Response status: `201 Created`.

## Get Escalation

### `GET /escalations/{escalation_id}`

Returns the current escalation status, ticket, customer, assignment, reason, and timestamps.

Response status: `200 OK` or `404 Not Found`.

## Error Shape

Validation and application errors use a consistent envelope:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "Escalation not found"
  }
}
```

Common codes include `validation_error`, `resource_not_found`, `tool_failure`, `retrieval_failure`, `llm_failure`, and `internal_error`.

## Authenticated Agent Chat

### `POST /agent/chat`

Requires a bearer token from `/auth/login` and routes the message through the LangGraph agent, RAG pipeline, tools, and conversation memory.

Request:

```json
{
  "message": "Where is order ORD-123?",
  "conversation_id": null,
  "order_number": "ORD-123",
  "ticket_id": null
}
```

The `conversation_id` may be omitted to start a new session. The response includes the selected route, answer, sources, tool results, trace, and optional error code.

## Agent Runtime

The `SupportAgent` runtime is also available as a Python service component. The HTTP route supplies the authenticated user's ID and database session before invoking it.
