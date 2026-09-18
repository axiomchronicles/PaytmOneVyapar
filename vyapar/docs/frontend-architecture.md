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

Access tokens live in platform secure storage. Bootstrap restores the token and validates it with `/merchants/me` before exposing the authenticated shell. The backend has no refresh-token contract, so a 401 clears the session and routes to sign-in.

## Navigation

`go_router` owns auth redirects, deep links, nested detail routes, and a persistent stateful shell for Home, Inventory, Munim, Orders, and More. Orders opens an ID entry/empty capability surface because the backend has no list route; successful approvals can deep-link directly to the returned order ID.

## Realtime

One authenticated coordinator connects to `/api/v1/ws`, decodes only `{type,data}` envelopes, and publishes typed events. Feature controllers selectively invalidate affected data and then re-fetch authoritative HTTP state. Malformed and unknown events are ignored safely. Current backend wiring prevents outbox events from reaching this socket; see `backend-contract-map.md`.

## Voice

The voice controller requests microphone permission, creates a backend session, streams mono PCM16 microphone frames, consumes transcript/action/response/control events, supports interruption and lifecycle shutdown, and keeps secrets server-side. Binary TTS is buffered as a continuous utterance. Continuous PCM playback requires the backend to advertise and emit `linear16`; the current default is unframed MP3, which is recorded as a contract gap rather than decoded chunk-by-chunk.

## Rendering and performance

Non-trivial pages use `CustomScrollView` and lazy slivers. Search is debounced, obsolete requests are cancellable where the API supports server queries, and provider selection limits rebuild scope. Decorative backgrounds are static `CustomPainter` shapes. There are no scrolling blur filters, nested vertical lists, or per-row looping animations.

## Design system

The palette is derived from the supplied references: deep Paytm navy, bright cyan, near-white surfaces, pale blue backgrounds, cool slate text, and restrained status colors. App screens rely on whitespace, dividers, typography, and occasional grouped surfaces rather than universal cards. Hugeicons stroke-rounded glyphs are accessed only through `VyaparIcons`.

## Persistence and optional integrations

Secure storage is used only for the access token. Local preferences hold language choice. Drift is not added because the current unpaginated, read-light API does not justify a second database or an offline synchronization model. Firebase Messaging is not initialized because there is no backend device-registration or notification payload contract.

## Verification

The supported screens have unit/widget coverage plus mobile-size goldens for Welcome, Sign In, Home, Inventory, Approval, Munim, Voice, and Orders. The app has been analyzed, tested, built as Android debug and release APKs, built through the macOS integration-test runner, and exercised against an isolated real FastAPI/PostgreSQL/Redis stack.
