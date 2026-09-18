# Architecture

Vyapaar Commander is one deployable FastAPI application with explicit module boundaries. Flutter
is a client over REST, WebSocket, and notification channels; it does not own inventory,
forecasting, approvals, agents, or execution rules.

```text
Flutter / WhatsApp / voice / external agent
                    │
          REST, WebSocket, webhooks
                    │
                 FastAPI
                    │
   application services and typed commands
       │             │              │
   LangGraph     A2A service     channel adapters
       │             │              │
 forecast/risk  signed envelope  Meta / Sarvam
       └─────────────┼──────────────┘
                     │
      SQLAlchemy transaction + outbox
              │              │
         PostgreSQL        Redis
       durable truth   coordination/fanout
```

## Transaction boundary

The strict execution path is:

```text
structured agent output
  → validated command
  → application service
  → identity, authorization, limits, state, hash, expiry, idempotency
  → deterministic transaction service
  → supplier side effect
```

No LLM provider is injected into `OrderService` or either transaction executor. The exact proposal
shown to the merchant is serialized with sorted keys and stable separators and hashed with SHA-256.
An approval record binds merchant, proposal, hash, nonce, expiry, and status. Its signed token binds
the same values. Modified proposals are new revisions with new proposal IDs, hashes, approval rows,
and tokens.

PostgreSQL uniqueness constraints protect proposal execution, transaction creation, A2A nonces,
provider message IDs, and idempotency keys. Redis locks can reduce contention but are never the
correctness boundary.

## Agent workflow

`app/agents/graph.py` builds the LangGraph state machine:

```text
detect_need → forecast_demand → find_supplier → negotiate → risk_check
            → create_proposal → human_approval (interrupt)
                                      ├─ APPROVE → execute_order → verify_result
                                      ├─ MODIFY  → forecast/find/negotiate/new approval
                                      └─ REJECT  → end
```

Risk or supplier exhaustion stops safely. An execution failure records the attempted supplier and
returns to discovery; any alternate supplier causes a different proposal and therefore another
approval. Thread IDs are deterministic: `purchase:{merchant_id}:{request_id}`. Development may use
`InMemorySaver`; normal production configuration requires `AsyncPostgresSaver` and runs its schema
setup during application lifespan.

The specialist definitions are capability allowlists, not autonomous transaction actors. Demand
uses forecasting tools, procurement uses supplier discovery, negotiation uses bounded offers, and
risk reads business state. The mock supplier implements the same signed A2A envelope exchange as a
remote supplier.

## Data and events

SQLAlchemy models cover users, merchants, stores, products, inventory and events, sales, suppliers
and catalogs, orders and items, negotiations, agent sessions/messages/runs, approvals, transactions,
audit logs, A2A agents/messages, voice sessions, channel messages, outbox events, and idempotency
keys. Timestamps are timezone-aware and IDs are UUIDs.

Business changes add outbox rows in the same database transaction. The ARQ worker publishes
pending rows through Redis pub/sub, marks successful delivery, and keeps failed rows for retry.
WebSocket events are projections for clients, never authoritative state.

## Providers and degradation

- `AzureFoundryLLMProvider` exposes structured Pydantic output only.
- `MockSupplierAdapter` and `RestSupplierAdapter` share a canonical procurement model.
- `MetaWhatsAppProvider` owns Graph API payloads, retry classification, and webhook signing.
- `SarvamVoiceProvider` owns realtime STT/TTS SDK payloads; the application sees `VoiceEvent`.
- `BaselineForecaster` is deterministic. `LightGBMForecaster` is selected only with enough data or
  a persisted model and never trains on startup.

Optional providers are constructed only when credentials are present. Provider errors are surfaced
as typed errors; secrets, raw audio, and tokens are excluded from structured logs.
