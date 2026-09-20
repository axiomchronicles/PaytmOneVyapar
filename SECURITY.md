# Security Policy

Paytm ONE Vyapar (Vyapaar Commander) is an autonomous procurement and inventory platform designed with defense-in-depth and strict cryptographic boundaries. We take the security of merchants, suppliers, and transaction data seriously.

---

## 1. Supported Versions

| Component | Supported Version | Status |
| :--- | :--- | :--- |
| **Vyapaar Commander Backend** | `0.1.x` (FastAPI) | :white_check_mark: Supported |
| **Vyapar Mobile Client** | `1.0.x` (Flutter) | :white_check_mark: Supported |
| **Vyapaar A2A Protocol** | `v1` (`vyapaar-a2a-v1`) | :white_check_mark: Supported |

---

## 2. Core Security Architecture & Invariants

Vyapaar Commander adheres to six non-negotiable security invariants across its backend and client layers:

### 1. Dual-Token & Cryptographic Proposal Hashing
- When the autonomous agent finishes supplier negotiation, it produces a structured `PurchaseProposal`.
- The exact proposal shown to the merchant is canonicalized (keys sorted, compact JSON separators) and hashed with **SHA-256**.
- The server generates an `ApprovalRecord` with a unique nonce and creates a short-lived **Action Token** (JWT) specifically bound to that approval ID, proposal hash, merchant ID, and expiration timestamp.
- Executing an order (`POST /api/v1/approvals/{id}/approve`) requires both an authenticated merchant **Access Token** AND the valid **Action Token**.
- The server verifies:
  1. The Action Token signature with `AUTH_APPROVAL_SECRET` (distinct from `AUTH_JWT_SECRET`).
  2. That the hash in the token exactly matches the stored SHA-256 hash of the proposal.
  3. That the approval is in `PENDING` status and unexpired.
  4. That the nonce has never been used.
- Any modification creates a new revision with a new proposal ID, hash, nonce, and action token.

### 2. Strict LLM Non-Delegation
- Large Language Models (Azure OpenAI, Sarvam, etc.) are restricted to generating structured output (Pydantic models).
- **LLMs are never granted direct write access to the database, payment gateways, or supplier order placement.**
- All execution paths pass through typed application services (`OrderService`, `DatabaseTransactionExecutor`) with business spending limit validation.

### 3. Signed Agent-to-Agent (vyapaar-a2a-v1) Protocol
- Communication between buyer agents and supplier agents uses signed envelopes over HTTP and WebSockets.
- Every message envelope is signed using **HMAC-SHA256** with a secret key known to the registered agents.
- The transport layer enforces:
  - Cryptographic signature validity over canonical sorted JSON.
  - Nonce uniqueness across messages to block replay attacks.
  - Maximum clock-skew tolerance (default: 300 seconds).
  - Schema discrimination and intent allowlists.

### 4. Zero Raw Audio & Credential Logging
- Streaming audio from the Flutter client for Sarvam AI voice sessions is piped in-memory and discarded.
- Raw audio bytes, plain-text passwords, OTP codes, Action Tokens, and bearer tokens are strictly scrubbed from structured application logs (`structlog`) and telemetry spans.

### 5. Multi-Factor & Cryptographic Authentication
- Passwords and one-time passwords (OTP) are hashed with **Argon2id** (`pwdlib[argon2]`). Plain OTP codes are never logged or stored in the database.
- OTP challenges enforce strict rate-limiting, cooldown intervals, and maximum attempt quotas.
- OAuth token exchanges (Google & Apple) validate provider JWKS signatures, issuers, audiences, nonces, and account bindings.

### 6. Transactional Outbox & Ephemeral Redis
- PostgreSQL is the sole durable source of truth.
- Business state changes and event notifications are committed atomically in the same PostgreSQL transaction.
- Redis handles distributed locks and pub/sub fanout. Redis failure cannot cause data corruption or duplicate order execution.

---

## 3. Reporting a Vulnerability

If you discover a potential security vulnerability in Paytm ONE Vyapar, please report it privately:

- **Email**: Send vulnerability reports to `security@vyapaar.local` or create a confidential issue on the repository if security advisories are enabled.
- **Content**: Include detailed reproduction steps, potential impact, and affected components or endpoints.
- **Response Time**: We aim to acknowledge reports within 48 hours and provide remediation updates within 7 business days.

Please do **not** disclose vulnerabilities publicly or file public GitHub issues before a fix has been coordinated and released.

---

## 4. Secret Management Best Practices

For production deployments:
1. Never commit `.env` files or API credentials into Git.
2. Set `AUTH_JWT_SECRET`, `AUTH_APPROVAL_SECRET`, `AUTH_OTP_SECRET`, and `A2A_SIGNING_SECRET` to cryptographically secure random values (minimum 32 characters each).
3. Rotate JWT secrets and API tokens periodically using a dedicated secret manager (e.g., Azure Key Vault, AWS Secrets Manager, or HashiCorp Vault).
4. Run all web traffic through TLS (HTTPS / WSS) via Nginx or a managed API gateway.
