# Local development

## 1. Configure

```bash
cd backend
cp .env.example .env
```

Set `DATABASE_URL` to an existing PostgreSQL database. PostgreSQL is intentionally external and is
not in Compose. Generate separate random values of at least 32 characters for `AUTH_JWT_SECRET`,
`AUTH_APPROVAL_SECRET`, and `A2A_SIGNING_SECRET`.

`APP_CHECKPOINTER=memory` is an explicit local fallback. Use `postgres` for restart-safe approval
interrupts and in production.

## 2. Install and start Redis

```bash
uv sync --frozen
docker compose up -d redis
docker compose ps
```

If port 6379 is already occupied, run `REDIS_PORT=6380 docker compose up -d redis` and set
`REDIS_URL=redis://localhost:6380/0`.

Redis data is persisted in the `vyapaar_redis_data` volume. Stop it with `docker compose down`;
add `-v` only when you intentionally want to delete the local Redis data.

## 3. Migrate and seed PostgreSQL

```bash
uv run alembic upgrade head
uv run python scripts/seed_demo.py
```

The seed is deterministic and creates a merchant, user, store, cold-drink product, low inventory,
90 sales observations with weather/event signals, supplier catalog, and A2A agent registrations.

## 4. Run services

```bash
uv run uvicorn app.main:app --reload
uv run arq app.workers.worker.WorkerSettings
```

Open `http://localhost:8000/docs` in development. Get a token with:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=merchant@vyapaar.local&password=demo-change-me'
```

## 5. Verify

```bash
uv run ruff check .
uv run pytest
uv run python scripts/run_happy_path.py
```

The happy-path script requires neither PostgreSQL nor Redis. It intentionally uses a memory
checkpointer and in-memory approval ledger while retaining signed A2A messages, approval hashes,
tokens, and the secure executor boundary.

## Sarvam voice

Set `SARVAM_API_KEY` to enable session streaming. The adapter uses the current SDK realtime paths:
`saaras:v4` in `codemix` mode for partial/final STT and `bulbul:v3` with a configurable
v3-compatible speaker for streaming MP3 TTS.
Flutter sends mono `linear16` chunks over the authenticated backend WebSocket and receives JSON
transcript/control events plus binary MP3 chunks. Raw audio is not persisted.

Create a voice session through `POST /api/v1/voice/sessions`, then connect to the returned stream
URL with an `Authorization: Bearer …` header. Voice approval additionally requires an
active workflow request and its server-signed approval token in the authenticated session context.

## WhatsApp

Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`,
`WHATSAPP_APP_SECRET`, and an explicit version from the current Meta Graph API documentation in
`WHATSAPP_GRAPH_API_VERSION`. Meta must call `/webhooks/whatsapp`. GET performs the hub challenge;
POST validates `X-Hub-Signature-256`, stores provider message IDs idempotently, maps the sender to a
merchant phone number, and routes approval buttons to the approval workflow.

## Forecast model

The baseline is the default. To use LightGBM, train it explicitly in an offline job, save the model,
set `FORECAST_MODEL=lightgbm`, and point `FORECAST_MODEL_PATH` at the artifact. The application never
trains during startup and falls back to baseline when the configured minimum history is unavailable.
