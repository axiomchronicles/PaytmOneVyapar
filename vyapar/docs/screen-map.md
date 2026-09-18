# Screen map

Only screens backed by a real route or a truthful local application concern are enabled. An ID-based detail route always re-fetches authoritative server state where the backend permits it.

| Screen | App route | Backend API | Realtime | Riverpod state | States and interactions |
| --- | --- | --- | --- | --- | --- |
| Bootstrap | `/splash` | `GET /merchants/me` for restored session | No | Auth session | Initial, restoring, authenticated, unauthenticated, recovery error |
| Welcome | `/welcome` | None | No | Auth session | Continue to sign in; no simulated auth |
| Sign in | `/sign-in` | `POST /auth/token`, then `GET /merchants/me` | Starts after auth | Auth controller | Editing, submitting, invalid credentials, network error |
| Language | `/language` | None; selected code is sent when creating voice sessions | No | Local preferences | Supported language selection |
| Home | `/home` | Merchant, inventory, recommendations, analytics overview | Shared socket invalidates affected providers if events arrive | Dashboard composition | Loading, partial, loaded, empty, error, offline/stale |
| Inventory | `/inventory` | `GET /inventory?store_id=` | Inventory events | Inventory controller | Loading, refresh, local query over server-returned collection, empty, error, offline |
| Inventory detail | `/inventory/:inventoryId` | Authoritative object from refreshed inventory collection | Inventory events | Inventory detail family | Loading, loaded, missing, error |
| Recommendations | `/recommendations` | `GET /recommendations`; inventory joined by exact SKU | Recommendation/inventory events | Recommendation controller | Loading, loaded, empty, error |
| Recommendation detail | `/recommendations/:sku` | Recommendations and inventory | Same | Recommendation detail family | Shows only rank and inventory facts actually returned |
| Munim | `/munim` | Recommendations, inventory, analytics | Shared socket | Munim composition | Grounded operational summary; empty when no signals; opens voice |
| Analytics | `/analytics` | `GET /analytics/overview` | Order/inventory events | Analytics controller | Loading, loaded, empty, error |
| Approval detail | `/approval/:approvalId` | `GET /approvals/{id}` | Approval/order events | Approval family | Loading, pending, processing, approved, modified, rejected, expired, error |
| Approval action | Same route | POST approve/modify/reject | Same | Approval action controller | Requires exact short-lived token and request ID retained from a live workflow; never fabricates them |
| Order detail | `/order/:orderId` | `GET /orders/{id}` | Order events | Order family | Loading, current status, failed, missing, error |
| Voice Munim | `/voice` | `POST /voice/sessions`, voice WebSocket | Dedicated voice stream coordinated by one session controller | Voice session controller | Permission, connecting, listening, thinking, speaking, interrupted, disconnected, error |
| Profile | `/more/profile` | `GET /merchants/me` | No | Merchant profile | Merchant/store data, loading, error |
| Settings | `/more/settings` | None | No | Local preferences | Language and local app preferences only |
| Contract limitations | `/more/capabilities` | None | No | Static contract report | Clearly identifies backend-owned unavailable features |

## Screens intentionally not enabled

Phone/OTP, sign-up, forgot password, Google/Apple auth, approval inbox, order list, supplier discovery/detail, negotiation history, A2A activity, notifications, WhatsApp connection, store editing, security settings, inventory history, forecast detail, and analytics drill-down have no usable merchant-facing backend contract. They must not be backed by fake data or invented URLs.

