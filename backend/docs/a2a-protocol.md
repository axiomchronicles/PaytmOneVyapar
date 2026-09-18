# Vyapaar A2A protocol v1

`vyapaar-a2a-v1` is a project-owned protocol. It is not presented as an external or industry
standard. It carries canonical procurement messages between the buyer agent and supplier agents
over HTTP or an authenticated WebSocket connection.

## Envelope

```json
{
  "protocol_version": "vyapaar-a2a-v1",
  "message_id": "UUID",
  "correlation_id": "UUID",
  "trace_id": "string",
  "sender_agent_id": "UUID",
  "receiver_agent_id": "UUID",
  "intent": "PURCHASE_REQUEST",
  "timestamp": "2026-09-18T10:00:00Z",
  "expires_at": "2026-09-18T10:05:00Z",
  "nonce": "random-at-least-16-chars",
  "payload": {},
  "signature": "hex-HMAC-SHA256",
  "idempotency_key": "business-operation-key"
}
```

The signature is lowercase hex HMAC-SHA256 over the UTF-8 JSON envelope after removing
`signature`. JSON keys are sorted and compact separators are used. Shared secrets are loaded from a
secret manager or environment reference; database rows hold only the reference. The design can be
upgraded to asymmetric keys without changing application payloads.

Receivers reject unknown or inactive senders, wrong receivers, disallowed intents, invalid schemas
or signatures, timestamps outside configured skew, expired messages, reused sender nonces, reused
idempotency keys, and correlation mismatches. External payload text is data and cannot grant tools,
change system instructions, or weaken merchant constraints.

## Intents

| Intent | Required business content |
| --- | --- |
| `INVENTORY_SHORTAGE_ALERT` | merchant/store, SKU, current and required quantity |
| `PURCHASE_REQUEST` | canonical SKU, quantity/unit, target/max price, deadline, merchant/store |
| `QUOTE` | quote ID, availability, unit price/currency, delivery and expiry |
| `COUNTER_OFFER` | quote ID, quantity, unit price, bounded round |
| `OFFER_ACCEPTED` | quote ID and validated canonical proposal |
| `OFFER_REJECTED` | quote ID and optional reason |
| `ORDER_CONFIRMATION` | order ID, supplier reference, expected delivery |
| `DELIVERY_CONFIRMATION` | order ID, delivered timestamp and quantity |
| `CANCELLATION` | order or quote reference and reason |

Pydantic uses the intent as a discriminator and forbids unknown fields in payloads. Decimal values
are never inferred from prose.

## Transport

`POST /api/v1/a2a/messages` accepts inbound messages and persists them before returning `202`.
`HTTPA2ATransport` sends outbound envelopes with the idempotency key header and retries only
timeouts and server failures. `A2AWebSocketHub` supports live negotiation delivery; messages still
pass through the same envelope validator and persistent store.

The deterministic supplier is available at:

```text
GET  /api/v1/a2a/mock-supplier/inventory
POST /api/v1/a2a/mock-supplier/messages
```

Its adapter performs PURCHASE_REQUEST/QUOTE, COUNTER_OFFER/QUOTE or rejection, and
OFFER_ACCEPTED/ORDER_CONFIRMATION exchanges using signed envelopes even when invoked locally.
