# Realtime architecture

```text
business service transaction
  -> PostgreSQL entity + OutboxEvent (same commit)
  -> ARQ OutboxPublisher (row lock + skip locked)
  -> Redis channel vyapaar:events
  -> RedisRealtimeBridge
  -> tenant-keyed RealtimeHub
  -> one authenticated Flutter RealtimeCoordinator
  -> EventDecoder + duplicate suppression + EventRouter
  -> targeted Riverpod invalidation
  -> authoritative REST refetch
```

The envelope is versioned and contains event/aggregate IDs, merchant routing, occurrence time, correlation/trace IDs, payload, and version. Redis or socket failure never rolls back business state: unsuccessful Redis publication leaves `published_at` null and increments the outbox attempt count. WebSocket delivery is not durable; reconnection therefore emits `REALTIME_RESYNC_REQUIRED` and refreshes all merchant state.

The client uses bounded exponential backoff with jitter, native heartbeat/ping, app foreground control, a 512-event duplicate window, and no feature-owned sockets. Out-of-order events are safe because they trigger refetch rather than patching complex domain state.

Current event types: `INVENTORY_UPDATED`, `INVENTORY_LOW`, `DEMAND_SURGE_DETECTED`, `APPROVAL_REQUIRED`, `APPROVAL_GRANTED`, `APPROVAL_REJECTED`, `ORDER_EXECUTED`, `ORDER_FAILED`, `SUPPLIER_CONFIRMATION_RECEIVED`, `NEGOTIATION_UPDATED`, `A2A_MESSAGE_RECEIVED`, and `NOTIFICATION_CREATED`. Envelope version is `1`.
