# Backend contract map

Source of truth: FastAPI OpenAPI generated from `backend/app`, verified 19 September 2026. The API prefix is `/api/v1`. Merchant routes require a bearer access token and scope every query through the authenticated merchant; IDs supplied by Flutter never establish ownership.

Errors use `{"error":{"code","message","request_id","details"}}`. List resources use bounded cursor pages (`items`, `next_cursor`) except supplier products, which use bounded `limit`, `offset`, and `total`.

## Authentication

| Method | Path | Contract |
| --- | --- | --- |
| POST | `/auth/token` | Password-form login; returns access/refresh tokens and expiry. |
| POST | `/auth/refresh` | Rotates a hashed, server-side refresh session. |
| POST | `/auth/logout` | Revokes the authenticated refresh session. |
| POST | `/auth/otp/request` | Creates a rate-limited phone challenge for `LOGIN` or `REGISTRATION`. |
| POST | `/auth/otp/verify` | Consumes a six-digit challenge; returns a session or one-time registration token. |
| POST | `/auth/otp/resend` | Rotates the code subject to cooldown and resend limit. |
| POST | `/auth/register` | Atomically creates User, Merchant, Store, and session from verified OTP/OAuth state. |
| POST | `/auth/oauth/{provider}/start` | Creates state/nonce challenge for `google` or `apple`. |
| POST | `/auth/oauth/{provider}/exchange` | Verifies provider ID token/JWKS, state, nonce, issuer, audience, expiry, and account link. |
| POST | `/auth/oauth/{provider}/link` | Authenticated explicit account linking. |

OTP values are Argon2-hashed and never returned or logged. Production OTP delivery uses configured Meta WhatsApp credentials. OAuth client IDs are public configuration; provider secrets never enter Flutter.

## Merchant business contracts

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/health` | Service and Redis health. |
| GET | `/merchants/me` | Merchant profile and stores. |
| GET | `/inventory` | Tenant-scoped inventory, optionally by store. |
| POST | `/inventory/events` | Locked inventory mutation plus durable outbox event. |
| GET | `/recommendations` | Deterministic inventory recommendation ranks. |
| POST | `/agents/runs` | Starts backend-authoritative replenishment using DB stock, sales, product, and spending limit. |
| GET | `/approvals` | Cursor-paged approvals with domain status/date filters. |
| GET | `/approvals/{id}` | Exact proposal, revision, hash, expiry, status, and short-lived action token. |
| POST | `/approvals/{id}/approve` | Locked, token/hash-bound, idempotent approval and workflow execution. |
| POST | `/approvals/{id}/modify` | Supersedes the exact revision and returns a new proposal/approval. |
| POST | `/approvals/{id}/reject` | Locked, idempotent rejection. |
| GET | `/orders` | Cursor-paged orders with status/store/supplier/date/search filters. |
| GET | `/orders/{id}` | Order items and real persisted approval/order timeline. |
| GET | `/suppliers` | Cursor-paged accessible global/merchant suppliers. |
| GET | `/suppliers/{id}` | Supplier profile and bounded catalog preview. |
| GET | `/suppliers/{id}/products` | Paginated merchant-product availability and exact prices. |
| GET | `/negotiations` | Cursor-paged persisted negotiation snapshots. |
| GET | `/negotiations/{id}` | Quote, constraints, proposal binding, and event history. |
| GET | `/a2a/activity` | Cursor-paged human-readable A2A activity with filters. |
| GET | `/a2a/conversations/{correlation_id}` | Ordered merchant-visible A2A conversation. |
| POST | `/a2a/messages` | Signed inbound `vyapaar-a2a-v1` transport. |
| GET | `/a2a/mock-supplier/inventory` | Deterministic supplier test catalog. |
| POST | `/a2a/mock-supplier/messages` | Signed deterministic supplier exchange. |
| GET | `/history/activity` | Cursor-paged audit history with resource/action/date filters. |
| GET | `/history/inventory` | Cursor-paged inventory events. |
| GET | `/notifications` | Cursor-paged notification inbox. |
| GET | `/notifications/{id}` | Fresh notification detail. |
| PATCH | `/notifications/{id}/read` | Marks one notification read. |
| POST | `/notifications/read-all` | Marks the authenticated user's notifications read. |
| GET | `/analytics/overview` | Bounded overview for date/store. |
| GET | `/analytics/sales` | Day/week/month sales-value points. |
| GET | `/analytics/inventory` | Category inventory-health aggregates. |
| GET | `/analytics/procurement` | Supplier order count/spend aggregates. |
| POST | `/voice/sessions` | Creates authenticated voice session and advertises input/output audio contracts. |

Meta provider webhooks remain at `/webhooks/whatsapp` and are not Flutter APIs.

## WebSockets

| Path | Contract |
| --- | --- |
| `/api/v1/ws` | One authenticated merchant connection. Receives versioned outbox projections and heartbeat frames. |
| `/api/v1/voice/sessions/{id}/stream` | PCM microphone/control input; transcript/action/response/audio events and binary TTS output. |
| `/api/v1/a2a/ws/{agent_id}` | Signed agent transport, not a merchant feed. |

Merchant event envelopes contain `event_id`, `event_type`, `aggregate_type`, `aggregate_id`, `merchant_id`, `occurred_at`, `correlation_id`, `trace_id`, `payload`, and `version`.
