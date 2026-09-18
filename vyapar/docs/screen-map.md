# Screen map

Every business screen below is backed by a typed FastAPI contract and Riverpod repository/notifier. Lists use lazy slivers and server pagination; detail/deep-link screens refetch authoritative state.

| Screen | App route | Backend contract |
| --- | --- | --- |
| Bootstrap/session recovery | `/splash`, `/session-recovery` | Refresh rotation and `GET /merchants/me` validation |
| Welcome/sign in | `/welcome`, `/sign-in` | Password token, Google/Apple OAuth start/exchange |
| OTP | `/otp` | OTP request, verify, resend with real challenge state |
| Registration | `/register` | Verified registration transaction creating User/Merchant/Store/session |
| Home | `/home` | Merchant, inventory, recommendations, analytics; notification deep link |
| Inventory/detail | `/inventory`, `/inventory/:id` | Inventory list and event mutation |
| Recommendations/detail | `/recommendations`, `/recommendations/:sku` | Deterministic ranked backend signals |
| Munim/voice | `/munim`, `/voice` | Agent data and authenticated voice WebSocket |
| Approval inbox/detail | `/approvals`, `/approval/:id` | Paged list, exact proposal/hash/revision, approve/modify/reject |
| Orders/detail | `/orders`, `/order/:id` | Paged orders, line items, real status timeline |
| Suppliers/detail | `/suppliers`, `/suppliers/:id` | Paged accessible suppliers and catalog availability |
| Negotiations/detail | `/negotiations`, `/negotiations/:id` | Paged negotiation snapshots, quotes, and event history |
| A2A activity/conversation | `/a2a-activity`, `/a2a-activity/:correlationId` | Human-readable persisted A2A history |
| Business history | `/history` | Audit history with Today/Yesterday/week/month/custom ranges |
| Notifications | `/notifications` | Persistent inbox, read state, stable-ID deep links |
| Analytics/detail | `/analytics`, `/analytics/:metric` | Overview plus sales/inventory/procurement aggregates |
| Profile/settings | `/more/profile`, `/more/settings` | Merchant profile and local language preference |

All loading, empty, error, refresh, pagination, mutation-processing, and terminal states are rendered explicitly. OAuth/OTP/voice configuration errors remain visible and are never replaced with mock success.
