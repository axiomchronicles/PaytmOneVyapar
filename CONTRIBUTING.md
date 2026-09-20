# Contributing to Paytm ONE Vyapar (Vyapaar Commander)

Thank you for your interest in contributing to **Paytm ONE Vyapar (Vyapaar Commander)**! This document provides guidelines and workflows for contributing to our monorepo containing the autonomous backend and the Flutter mobile client.

---

## 1. Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to understand the behavioral standards expected in this community.

---

## 2. Monorepo Architecture Overview

The repository is structured as a full-stack monorepo:

- **[`backend/`](backend/README.md)**: FastAPI modular monolith powered by LangGraph, SQLAlchemy 2.0 Async ORM, PostgreSQL, Redis, and ARQ background workers.
- **[`vyapar/`](vyapar/README.md)**: Cross-platform Flutter client with Riverpod 3.0 reactive architecture, GoRouter, custom design tokens, and real-time streaming voice/WebSocket clients.
- **[`deploy/`](deploy/)**: Production Docker Compose configurations, Nginx reverse proxy with WebSocket support, and cloud-init bootstrap scripts.
- **[`design_reference/`](design_reference/)**: Visual mockups, typography, and token references.

---

## 3. Getting Started

### Prerequisites

- **Python**: 3.12–3.14 (3.13 recommended)
- **uv**: Fast Python package manager ([installation instructions](https://docs.astral.sh/uv/))
- **Flutter SDK**: 3.24+ / Dart 3.5+
- **Docker & Docker Compose**: For local PostgreSQL and Redis services
- **Git**: Modern git client

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/axiomchronicles/PaytmOneVyapar.git
   cd PaytmOneVyapar
   ```

2. **Install all dependencies:**
   ```bash
   make install
   ```

3. **Start local infrastructure (PostgreSQL & Redis):**
   ```bash
   make infra-up
   ```

4. **Initialize backend environment:**
   ```bash
   cd backend
   cp .env.example .env
   # Update secrets and database settings in .env as needed
   cd ..
   ```

5. **Run migrations and seed deterministic data:**
   ```bash
   make migrate
   make seed
   ```

6. **Verify the installation:**
   ```bash
   make lint
   make test
   make demo
   ```

---

## 4. Development Workflow

### Branch Naming Conventions

Use lowercase branch names prefixed with conventional category identifiers:

- `feat/<feature-name>`: New capabilities or screen flows
- `fix/<bug-description>`: Bug fixes and error handling
- `docs/<doc-name>`: Documentation improvements
- `refactor/<scope>`: Code refactoring without behavioral changes
- `test/<test-scope>`: Adding or modifying test suites
- `chore/<task>`: Dependency updates or build tooling

### Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <short summary>

[optional body explaining motivation and non-obvious choices]

[optional footer(s), e.g., Closes #123]
```

**Allowed types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes only
- `test`: Adding or updating tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Code change that improves performance
- `chore`: Tooling, build configuration, or dependency updates

**Examples:**
- `feat(agents): add supplier negotiation round counter`
- `fix(voice): handle network reconnect gracefully in streaming buffer`
- `test(mobile): add widget test for order detail timeline`

---

## 5. Architectural Invariants (Must Follow)

When contributing to either the backend or client, you **must preserve the following security and architectural invariants**:

1. **Strict Non-Delegable Transaction Boundary**:
   - LLMs return structured data only (via Pydantic schemas).
   - LLMs **never** directly mutate the database, execute orders, or trigger payments.
   - All mutations pass through typed domain services with strict limits and authorization checks.

2. **Dual-Token & Hash-Bound Approvals**:
   - The exact proposal presented to the merchant is canonicalized and hashed with **SHA-256**.
   - An approval record cryptographically binds the proposal hash, merchant ID, nonce, and expiration.
   - The action token submitted to `/api/v1/approvals/{id}/approve` must match the proposal hash and unexpired nonce.
   - Any modification creates a new revision with a new proposal ID, hash, and token.

3. **PostgreSQL as Single Source of Truth**:
   - PostgreSQL owns all durable state.
   - Redis is used strictly for distributed locks, pub/sub fanout, caching, and worker queues. Redis never owns permanent business data.

4. **Transactional Outbox Pattern**:
   - All domain state changes write an outbox event in the same database transaction.
   - The ARQ worker publishes events via Redis pub/sub to WebSockets.
   - Client WebSocket projections are views; clients never treat WebSocket data as authoritative without re-fetching via REST.

5. **Vyapaar A2A Protocol Signing**:
   - Inbound and outbound A2A messages must adhere to the `vyapaar-a2a-v1` envelope specification.
   - Envelopes are signed with lowercase hex HMAC-SHA256 over canonical sorted JSON.
   - Replay attacks are prevented via mandatory unique nonces, clock-skew checks, and idempotency keys.

6. **Privacy & Zero Audio Persistence**:
   - Microphone PCM audio is streamed, processed in-memory for STT, and discarded immediately.
   - Raw audio, JWT tokens, approval action tokens, and passwords/OTPs must **never** be logged.

---

## 6. Code Style Standards

### Backend (Python)

- **Linter & Formatter**: [Ruff](https://astral.sh/ruff)
- **Type Hints**: Mandatory for all function arguments and returns.
- **Async First**: Use async SQLAlchemy 2.0 and asyncpg for database operations.
- **Pydantic V2**: Use `ConfigDict(frozen=True)` for domain models and strict validation.
- **Run verification**:
  ```bash
  make lint-backend
  make format
  ```

### Frontend (Flutter / Dart)

- **Architecture**: Layered approach (`app`, `core`, `design_system`, `features`, `shared`).
- **State Management**: Flutter Riverpod 3.0 (`AsyncNotifier`, `Notifier`, `Provider`).
- **Navigation**: `go_router` with declarative redirect logic and deep-link parameters.
- **Icons**: Hugeicons mapped cleanly via `VyaparIcons`.
- **Design Tokens**: Always use centralized tokens (`VyaparColors`, `VyaparSpacing`, `VyaparRadii`, `VyaparTypography`). Avoid hardcoded magic numbers or colors.
- **Run verification**:
  ```bash
  make lint-frontend
  cd vyapar && dart format .
  ```

---

## 7. Testing Requirements

All contributions must include tests covering new logic or bug fixes:

- **Backend Tests**:
  - Unit tests in `backend/tests/unit/`
  - Integration tests in `backend/tests/integration/`
  - Agent workflow tests in `backend/tests/agents/`
  - Security boundary tests in `backend/tests/security/`
  - Voice tests in `backend/tests/voice/`
  - Run with: `make test-backend`

- **Frontend Tests**:
  - Widget and provider unit tests in `vyapar/test/`
  - Golden snapshot tests in `vyapar/test/goldens/`
  - Integration tests in `vyapar/integration_test/`
  - Run with: `make test-frontend`

---

## 8. Submitting a Pull Request

1. Push your branch to GitHub.
2. Open a Pull Request targeting `main`.
3. Provide a clear description of changes, motivation, and any testing performed.
4. Ensure all CI checks pass (linting, backend tests, flutter tests).
5. Address any feedback during code review promptly.
