# Frontend architecture

The Flutter client is a feature-first experience layer over the FastAPI service. It never validates business transactions, invents supplier state, signs A2A messages, or treats WebSocket projections as authoritative.

## Layers

- `app/`: bootstrap, route graph, authenticated shell, lifecycle coordination, and top-level providers.
- `core/`: compile-time configuration, Dio, authentication storage/session, connectivity, structured errors, and the shared realtime coordinator.
- `design_system/`: centralized color/spacing/radius/type/motion tokens, themes, low-cost painted backgrounds, Hugeicons mapping, and reusable state/action components.
- `features/<feature>/`: transport DTOs/domain models, repository, Riverpod state, screens, and focused widgets owned by that feature.
- `shared/`: formatters, validators, and cross-feature presentation helpers.

HTTP calls terminate in repositories, not widgets. Riverpod AsyncNotifiers own remote state and mutations. Detail providers are parameterized by stable IDs. Widgets keep only controllers, focus, animation, and ephemeral form state.

Providers use Riverpod 3's direct `Provider`, `Notifier`, `AsyncNotifier`, family, and stream APIs. Generator packages are intentionally not required by the checked-in client because the installed Dart SDK's builder snapshot compiler is unavailable/incompatible in this environment; the provider graph remains typed and overrideable in tests.

## Networking and authentication

A single Dio instance uses a compile-time base URL, bounded timeouts, bearer injection, UUID request IDs, and central error mapping. Only safe reads are retried, and side-effecting requests use explicit idempotency keys without automatic retries.

Access and rotating refresh tokens live in platform secure storage. Bootstrap restores the access token and validates it with `/merchants/me`. The shared HTTP interceptor performs one synchronized refresh on a 401, retries the original request once, and clears the session only when refresh fails. OTP and OAuth verification produce either the same session contract or an explicit registration token; no credential is stored in preferences.

## Navigation

`go_router` owns auth redirects, OTP/registration state, OAuth cancellation/success, stable entity deep links, and a persistent stateful shell for Home, Inventory, Munim, Orders, and More. Approvals, orders, suppliers, negotiations, notifications, A2A activity, history, and analytics drill-down always fetch fresh backend entities by stable ID.

## Realtime

One authenticated `RealtimeCoordinator` connects to `/api/v1/ws`. The decoder validates versioned outbox envelopes, a bounded event-ID set suppresses duplicate delivery, and `RealtimeEventRouter` maps events to targeted Riverpod invalidations. Reconnect emits a resynchronization signal before normal event handling. Backgrounding closes the shared connection; foregrounding reconnects and refetches authoritative HTTP state. Partial payloads are never used to reconstruct transactional state.

## Voice

The voice controller requests microphone permission, creates a backend session, streams mono PCM16 microphone frames, consumes transcript/action/response/control events, supports barge-in and lifecycle shutdown, and keeps credentials server-side. `AUDIO_START` advertises codec/sample rate. Raw PCM uses a 300 ms prebuffer and continuous feed; unsupported compressed streams are never played as independent chunks.

## Rendering and performance

Non-trivial pages use `CustomScrollView` and lazy slivers. Cursor notifiers prevent duplicate page requests, preserve loaded rows on page failure, and stop at `next_cursor == null`. Search/filter values are sent to backend query contracts. Provider selection limits rebuild scope; decorative backgrounds remain low-cost static painters.

## Design system

The palette is derived from the supplied references: deep Paytm navy, bright cyan, near-white surfaces, pale blue backgrounds, cool slate text, and restrained status colors. App screens rely on whitespace, dividers, typography, and occasional grouped surfaces rather than universal cards. Hugeicons stroke-rounded glyphs are accessed only through `VyaparIcons`.

## Persistence and optional integrations

Secure storage is used only for access and refresh tokens. Local preferences hold language choice. PostgreSQL-backed notifications arrive through REST and the shared realtime projection; notification payloads only carry stable IDs and the destination screen refetches current state. No client database is introduced.

## Verification

The supported screens have unit/widget coverage plus mobile-size goldens for Welcome, Sign In, Home, Inventory, Approval, Munim, Voice, and Orders. The app has been analyzed, tested, built as Android debug and release APKs, built through the macOS integration-test runner, and exercised against an isolated real FastAPI/PostgreSQL/Redis stack.
