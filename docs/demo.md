# Demo Preparation

## Demo Goal

Show that the system can ground policy answers, select operational tools, preserve conversation context, create tickets, escalate to humans, and recover safely from failures.

## Before the Demo

Start the stack:

```powershell
docker compose up --build -d
docker compose exec api python -m backend.scripts.seed_knowledge_base
```

Verify the service:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Run the automated safety net:

```powershell
docker compose exec api pytest
```

The agent runtime is currently a Python service component rather than an HTTP route. For a full live agent demonstration, provide a configured chat model and instantiate `SupportAgent` with `AgentDependencies`.

## Scenario 1: RAG Demonstration

User question:

```text
How long can I request a refund after delivery?
```

Expected flow:

```text
Question
  -> policy intent
  -> query embedding
  -> pgvector retrieval
  -> refund policy context
  -> grounded model answer
```

Expected answer should mention the 30-calendar-day policy and cite the refund policy source. It should not invent exceptions that are absent from the retrieved context.

Interview explanation: RAG separates knowledge retrieval from language generation. The model is given relevant source text instead of being trusted to remember policy.

## Scenario 2: Tool Calling

User question:

```text
Where is order ORD-123?
```

Expected flow:

```text
Order intent
  -> check_order_status()
  -> PostgreSQL orders table
  -> structured OrderStatusResult
  -> response
```

The important demonstration point is that the answer comes from live structured data, not from the knowledge base.

## Scenario 3: Conversation Memory

First message:

```text
My order is ORD-45821 and it is late.
```

Follow-up:

```text
When will it arrive?
```

Expected flow:

```text
Persist first turn
  -> load recent session memory
  -> recover ORD-45821
  -> route follow-up to order tool
```

The `conversation_id` identifies the session. Recent turns are bounded so prompt size does not grow forever.

## Scenario 4: Ticket Creation

User message:

```text
My package has not moved for five business days.
```

Expected flow:

```text
Complex complaint
  -> optional order lookup
  -> create_support_ticket()
  -> high-priority ticket
  -> ticket ID returned
```

The ticket is the durable operational record for the customer issue.

## Scenario 5: Human Escalation

HTTP request:

```http
POST /escalations
Content-Type: application/json
```

```json
{
  "customer_id": "00000000-0000-0000-0000-000000000001",
  "reason": "The customer requested a human agent.",
  "ticket_id": null
}
```

Expected result:

- An urgent ticket is created.
- An escalation record is created.
- The response includes both the escalation ID and ticket ID.
- A human agent can later acknowledge, assign, or resolve the escalation.

## Scenario 6: Error Handling

Invalid escalation request:

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/escalations -ContentType 'application/json' -Body '{}'
```

Expected result:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid fields."
  }
}
```

Other recovery cases:

- Unknown order: ask the customer to verify the order number.
- Tool failure: return a safe retry or human-support message.
- Retrieval failure: report temporary knowledge-search unavailability.
- LLM failure: avoid fabricating an answer and recommend retry or escalation.

## Interview Talking Points

### Beginner

The system combines a normal backend with AI capabilities. PostgreSQL holds business data, RAG holds policy knowledge, tools read or change operational records, and LangGraph decides which capability to use.

### Intermediate

The architecture uses dependency injection and typed boundaries. Embedding, retrieval, chat-model, and tool providers can be replaced in tests without changing the agent runtime. Migrations version the relational and vector schema.

### Real-World Example

A refund question should not query the orders table first. It should retrieve the refund policy. A question about a specific order should use the order tool because its answer depends on live data. A request for a person should create an escalation rather than generate a generic answer.

### Common Questions

- Why not ask the LLM to answer everything? Live operational data changes and policy accuracy requires source grounding.
- Why use both RAG and tools? RAG handles unstructured knowledge; tools handle structured data and actions.
- Why keep escalation separate from tickets? A ticket describes the issue; an escalation tracks the human-support lifecycle.
- How do you test an agent? Test routing, tool contracts, memory behavior, retrieval construction, failure paths, and API envelopes independently.
- How do you prevent hallucinations? Restrict policy prompts to retrieved context, require source attribution, and provide an explicit insufficient-context response.

### Best Practices

- Keep tool inputs and outputs typed.
- Validate identifiers before database calls.
- Make migrations reversible and reviewable.
- Preserve source attribution in RAG responses.
- Bound conversation memory.
- Log server-side details while returning safe client messages.
- Escalate when confidence, data availability, or user intent requires a human.
