# Vyapaar Commander backend

Vyapaar Commander is a FastAPI modular monolith that detects inventory needs, forecasts demand,
negotiates with supplier agents, pauses for a merchant decision, and executes only the exact
approved order. PostgreSQL is the durable source of truth. Redis handles locks, cache, pub/sub,
and ARQ coordination, but never owns permanent business state.

## Workflow and boundaries

```text
inventory → deterministic forecast → supplier A2A → constrained negotiation
          → proposal + SHA-256 hash → human approval interrupt
          → signed-token validation → transaction service → supplier confirmation → outbox
```

LLMs can return structured suggestions only. They do not receive database mutation, approval,
order, or payment capabilities. Provider calls implement the contracts in `app/domain/contracts.py`.
The default demo is deterministic and does not require LLM, Meta, Sarvam, or supplier credentials.

See [architecture](docs/architecture.md), [A2A protocol](docs/a2a-protocol.md), and
[local development](docs/local-development.md) for detailed contracts and operations.

## Layout

- `app/api`: REST, WebSocket, and webhook transport
- `app/application`: business use cases and transaction boundaries
- `app/agents`: LangGraph state, nodes, tools, runtime, and narrow agent roles
- `app/a2a`: the project-owned signed `vyapaar-a2a-v1` protocol
- `app/channels`: WhatsApp and Sarvam voice channels
- `app/ml`: deterministic baseline and LightGBM forecasting
- `app/integrations`: Azure/OpenAI, supplier, WhatsApp, and storage adapters
- `app/infrastructure`: SQLAlchemy, Redis, outbox, and observability
- `migrations`: Alembic environment and initial schema
- `scripts`: idempotent demo seed and credential-free happy path
- `tests`: unit, API, agent, voice, and end-to-end coverage

## Requirements

- Python 3.12–3.14 (the checked environment uses Python 3.13)
- [uv](https://docs.astral.sh/uv/)
- external PostgreSQL 15 or newer
- Docker for the local Redis container

## Quick start

```bash
cd backend
cp .env.example .env
# Set DATABASE_URL and replace the development AUTH_/A2A_ secrets.
uv sync --frozen
docker compose up -d redis
uv run alembic upgrade head
uv run python scripts/seed_demo.py
uv run uvicorn app.main:app --reload
```

Run the worker separately:

```bash
uv run arq app.workers.worker.WorkerSettings
```

The demo login is created only by the seed script:

```text
merchant@vyapaar.local / demo-change-me
```

Change it outside a disposable hackathon environment.

## End-to-end demo

The local demonstration uses an in-memory LangGraph checkpointer and the signed mock supplier A2A
adapter. It still passes through the approval token and hash checks.

```bash
make demo
```

Example API workflow start (replace the token and IDs with seeded values):

```bash
curl -X POST http://localhost:8000/api/v1/agents/runs \
  -H 'Authorization: Bearer <access-token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id":"flutter-req-0001",
    "store_id":"<store-uuid>",
    "sku":"COLD-COLA-300",
    "quantity_on_hand":3,
    "reorder_point":8,
    "required_quantity":0,
    "unit":"crate",
    "target_price":450,
    "max_price":480,
    "spending_limit":50000,
    "delivery_deadline":"2026-09-20T12:00:00+05:30",
    "sales_history":[
      {"date":"2026-09-16T00:00:00Z","sales":6,"inventory":12,"price":600},
      {"date":"2026-09-17T00:00:00Z","sales":7,"inventory":6,"price":600}
    ]
  }'
```

The response is suspended at `human_approval` and includes the approval ID, exact proposal,
order hash, and short-lived token. Resume through the authenticated approval endpoint using the
same `request_id`. Modification creates a new proposal, hash, token, and approval.

## External providers

Set `LLM_PROVIDER=azure` with the `AZURE_` fields to enable structured Azure OpenAI calls. Set the
`SARVAM_` fields for realtime `saaras:v4-realtime` STT and `bulbul:v3` streaming TTS. Set all
`WHATSAPP_` fields, including an explicit current Graph API version, to enable Meta delivery.
Missing optional credentials do not stop the API; their endpoints report the integration as
unavailable. Production configuration rejects a memory checkpointer or weak JWT secret.

Raw audio, credentials, approval tokens, and access tokens are not logged. Raw audio is streamed
and discarded.

## Verification

```bash
make lint
make test
make demo
curl http://localhost:8000/api/v1/health
```
