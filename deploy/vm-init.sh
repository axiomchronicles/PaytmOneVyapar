#!/bin/bash
# Vyapaar Commander — Azure VM bootstrap script
# Runs as root on first boot via cloud-init

set -euo pipefail
exec > >(tee -a /var/log/vyapaar-init.log) 2>&1
echo "[$(date)] Starting Vyapaar VM bootstrap..."

# ── 1. System packages ──────────────────────────────────────────────────────
apt-get update -y
apt-get install -y \
  ca-certificates curl gnupg lsb-release git ufw \
  python3-pip python3-venv htop

# ── 2. Docker ────────────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker
systemctl start docker

# ── 3. Firewall ──────────────────────────────────────────────────────────────
ufw --force enable
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS (future)
ufw allow 8000/tcp  # Direct API (bypass nginx for debugging)

# ── 4. Clone repo ────────────────────────────────────────────────────────────
mkdir -p /opt/vyapaar
cd /opt/vyapaar
git clone https://github.com/axiomchronicles/PaytmOneVyapar.git app
cd /opt/vyapaar/app

# ── 5. Write production .env ─────────────────────────────────────────────────
cat > /opt/vyapaar/app/deploy/.env.prod << 'ENVEOF'
POSTGRES_USER=vyapaar
POSTGRES_PASSWORD=PLACEHOLDER_PG_PASS
POSTGRES_DB=vyapaar

APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_CORS_ORIGINS=*
APP_CHECKPOINTER=redis

DATABASE_URL=postgresql+asyncpg://vyapaar:PLACEHOLDER_PG_PASS@postgres:5432/vyapaar
DATABASE_POOL_SIZE=10

REDIS_URL=redis://redis:6379/0
REDIS_REQUIRED=true

AUTH_JWT_SECRET=PLACEHOLDER_JWT
AUTH_APPROVAL_SECRET=PLACEHOLDER_APPROVAL
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_MINUTES=30
AUTH_REFRESH_TOKEN_DAYS=30
AUTH_APPROVAL_TOKEN_MINUTES=10
AUTH_OTP_SECRET=PLACEHOLDER_OTP
AUTH_OTP_EXPIRY_MINUTES=5
AUTH_OTP_RESEND_SECONDS=45
AUTH_OTP_MAX_ATTEMPTS=5
AUTH_OTP_MAX_RESENDS=3

GOOGLE_OAUTH_CLIENT_ID=706043707662-2ro6mevqfn6u5r2h85e0jppbhrs780rb.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=PLACEHOLDER_GOOGLE_SECRET
GOOGLE_OAUTH_REDIRECT_URI=http://PLACEHOLDER_VM_IP/api/v1/auth/oauth/google/callback

LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.6-luna
AZURE_OPENAI_ENDPOINT=https://pk1769400-5339-resource.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=PLACEHOLDER_AZURE_OPENAI_KEY
AZURE_OPENAI_API_VERSION=

SARVAM_API_KEY=PLACEHOLDER_SARVAM_KEY
SARVAM_STT_MODEL=saaras:v4
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=roopa
SARVAM_TTS_CODEC=linear16

WHATSAPP_ACCESS_TOKEN=PLACEHOLDER_WA_TOKEN
WHATSAPP_PHONE_NUMBER_ID=1231073766765607
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
WHATSAPP_GRAPH_API_VERSION=v21.0

TELEGRAM_BOT_TOKEN=PLACEHOLDER_TG_TOKEN
TELEGRAM_WEBHOOK_SECRET=PLACEHOLDER_TG_SECRET
TELEGRAM_BOT_USERNAME=PaytmOneVyapar_bot

A2A_AGENT_ID=11111111-1111-4111-8111-111111111111
A2A_SIGNING_SECRET=PLACEHOLDER_A2A_SECRET
A2A_MAX_CLOCK_SKEW_SECONDS=300

FORECAST_MODEL=baseline
FORECAST_MODEL_PATH=models/demand.txt
FORECAST_MIN_TRAINING_ROWS=60

RESEND_API_KEY=PLACEHOLDER_RESEND_KEY
RESEND_FROM_EMAIL=Paytm ONE Vyapar <auth@tuboxlabs.com>

TELEMETRY_ENABLED=false
SENTRY_DSN=
ENVEOF

# ── 6. Start containers ───────────────────────────────────────────────────────
cd /opt/vyapaar/app
docker compose -f deploy/docker-compose.prod.yml \
  --env-file deploy/.env.prod \
  up -d --build 2>&1 | tee /var/log/vyapaar-compose.log

# ── 7. Run DB migrations ──────────────────────────────────────────────────────
echo "[$(date)] Waiting 30s for backend to be ready before migrations..."
sleep 30
docker compose -f deploy/docker-compose.prod.yml \
  --env-file deploy/.env.prod \
  exec -T backend python -m alembic upgrade head || \
  echo "[WARNING] Migrations may have failed - check logs"

echo "[$(date)] Vyapaar bootstrap complete!"
