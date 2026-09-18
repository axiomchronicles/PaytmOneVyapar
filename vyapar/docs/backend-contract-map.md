# Backend contract map

Source of truth: the FastAPI routers, Pydantic schemas, services, models, and generated OpenAPI in `backend/`, inspected on 18 September 2026.

The API prefix is `/api/v1`. Authenticated HTTP routes require `Authorization: Bearer <access_token>`. The backend returns domain failures as `{"error":{"code","message","request_id","details"}}`; validation failures use the same envelope with code `VALIDATION_FAILED`.

## HTTP contracts

| Method | Path | Auth | Request | Response |
| --- | --- | --- | --- | --- |
| GET | `/health` | No | None | `status`, `service`, `redis` |
| POST | `/auth/token` | No | Form data: `username`, `password` | `access_token`, `token_type` |
| GET | `/merchants/me` | Bearer | None | Merchant `id`, `name`, `currency`, `spending_limit`, `stores[{id,name}]` |
| GET | `/inventory` | Bearer | Optional `store_id` query UUID | Array of `inventory_id`, `store_id`, `product_id`, `sku`, `name`, `unit`, `quantity_on_hand`, `reorder_point`, `is_low` |
| POST | `/inventory/events` | Bearer | `store_id`, `product_id`, `quantity_delta`, `event_type`, `source`, `idempotency_key` | `inventory_id`, `quantity_on_hand` |
| GET | `/recommendations` | Bearer | None | Array of `sku`, `score` |
| GET | `/analytics/overview` | Bearer | None | `sales_quantity`, `low_inventory_products`, `orders_by_status` |
| POST | `/agents/runs` | Bearer | `request_id`, store/SKU/stock values, price constraints, spending limit, deadline, and non-empty sales history | `request_id`, complete workflow `state`; normally pauses with exact approval ID, proposal, hash, and approval token |
| GET | `/approvals/{approval_id}` | Bearer | UUID path | Exact approval metadata and proposal payload; deliberately does not return an approval token |
| POST | `/approvals/{approval_id}/approve` | Bearer | `approval_token`, optional `request_id`, `idempotency_key` | Approval row, or workflow result when `request_id` is supplied |
| POST | `/approvals/{approval_id}/modify` | Bearer | `approval_token`, required `request_id`, optional positive quantity/max price, `idempotency_key` | Superseded ID and new workflow state/revision |
| POST | `/approvals/{approval_id}/reject` | Bearer | Optional `request_id`, `idempotency_key` | Approval row, or workflow result when `request_id` is supplied |
| GET | `/orders/{order_id}` | Bearer | UUID path | Exact order summary |
| POST | `/voice/sessions` | Bearer | Language, microphone sample rate/encoding, optional active proposal/request/token context | Session ID, relative stream URL, provider availability, microphone audio metadata |
| POST | `/a2a/messages` | Signed A2A envelope | Canonical `vyapaar-a2a-v1` envelope | Accepted message ID and intent |
| GET | `/a2a/mock-supplier/inventory` | No | None | Deterministic mock supplier SKU availability and unit price |
| POST | `/a2a/mock-supplier/messages` | Signed A2A envelope | Canonical envelope | Signed response envelope |

The Meta routes at `/webhooks/whatsapp` are provider webhooks, not Flutter APIs.

## WebSocket contracts

| Path | Authentication | Direction | Contract |
| --- | --- | --- | --- |
| `/api/v1/ws` | Bearer header | Server to merchant | JSON `{type,data}` business-event projection. The in-process hub exists, but no Redis-to-hub subscriber is wired in the current application. |
| `/api/v1/voice/sessions/{session_id}/stream` | Bearer header | Bidirectional | Client sends mono PCM bytes and `end`, `interrupt`, or `ping` controls. Server sends JSON voice events and raw binary TTS chunks. |
| `/api/v1/a2a/ws/{agent_id}` | Signed envelope validation | Agent-to-agent | Inbound A2A transport. This is not a merchant activity feed. |

Voice event types are `SESSION_STARTED`, `TRANSCRIPT_PARTIAL`, `TRANSCRIPT_FINAL`, `ACTION`, `RESPONSE_TEXT`, `AUDIO_START`, `AUDIO`, `AUDIO_END`, `ERROR`, and `SESSION_ENDED`.

## Implementation/documentation discrepancies

- Auth implements only OAuth2 password-form email/password login. Phone/OTP, registration, password recovery, Google, Apple, logout/revocation, and token refresh do not exist.
- The access token response has no expiry field. The client validates a restored token by calling `/merchants/me`; expired sessions must sign in again.
- The data model contains rich inventory events, orders, negotiations, agents, A2A messages, voice sessions, channels, and notifications/outbox data, but most have no merchant-facing list or detail APIs.
- Inventory has no pagination, backend search, category field in its response, detail endpoint, event history endpoint, forecast endpoint, or supplier options.
- Recommendations expose only `sku` and a deterministic rank `score`. They do not expose reason, suggested quantity, forecast, expected benefit, or confidence.
- Agent runs can be started but cannot be listed or fetched. Their required sales history and purchase constraints are not exposed by another Flutter-facing API.
- Approvals and orders have detail-by-ID routes only. There is no inbox/list route. Approval GET intentionally cannot recover the short-lived approval token.
- Supplier discovery/detail, negotiation history, A2A activity history, notification history/unread state, store mutation/switch persistence, settings, channel status, and analytics drill-down routes do not exist.
- `/api/v1/ws` is not connected to Redis pub/sub, so outbox events cannot currently reach merchant WebSocket clients.
- Voice defaults to MP3 output, while session creation reports microphone input encoding only. `AUDIO_START` does not advertise output codec/sample rate and binary chunks carry no framing metadata. Continuous raw PCM playback therefore requires backend configuration and an explicit output-audio contract.
- FCM credentials exist in the scaffold, but the backend defines no FCM registration or push payload contract.

## Verification evidence

An isolated local PostgreSQL/Redis environment was migrated and seeded with the backend's own scripts. Against a running FastAPI process, the following real path completed successfully: password token issuance, merchant profile, inventory, recommendation ranking, analytics overview, agent-run creation, exact approval retrieval, signed approval resume, verified order execution, confirmed order retrieval, and voice-session creation.

The Flutter driver build then signed in through the production auth repository, loaded the same merchant dashboard and inventory, opened inventory detail, connected the authenticated merchant WebSocket, and restored the validated secure session after a hot restart.

The voice WebSocket accepted the bearer-authenticated session and emitted `SESSION_STARTED`, but the configured Sarvam credential returned `invalid_subscription_key`; the backend projected that as a typed `ERROR`. Real STT/TTS therefore still requires a valid external Sarvam subscription key and mobile audio-route testing.
