import asyncio
from datetime import timedelta
from uuid import UUID

from conftest import MERCHANT_ID
from sqlalchemy import select

from app.core.errors import OAuthCredentialError
from app.core.security import utc_now
from app.infrastructure.db.models import OtpChallenge


class CaptureOtpDelivery:
    def __init__(self) -> None:
        self.codes: list[str] = []

    async def send(self, identifier: str, otp: str, *, idempotency_key: str) -> None:
        self.codes.append(otp)


class FakeOAuthVerifier:
    async def verify(self, provider, id_token, *, client_id, nonce):
        if id_token == "rejected-provider-token-value":
            raise OAuthCredentialError("OAuth credential is invalid or expired")
        if id_token == "new-user-token-value":
            return {
                "sub": "provider-new-user-99",
                "email": "new-user@example.com",
                "email_verified": True,
                "nonce": nonce,
            }
        return {
            "sub": "provider-user-1",
            "email": "merchant@example.com",
            "email_verified": True,
            "nonce": nonce,
        }

    async def exchange_google_code(self, code, *, client_id, client_secret, redirect_uri):
        if code == "invalid-code":
            raise OAuthCredentialError("Failed to exchange Google authorization code")
        return {"id_token": "valid-provider-token-value"}


def test_otp_registration_replay_and_session_refresh(client) -> None:
    delivery = CaptureOtpDelivery()
    client.app.state.otp_delivery = delivery
    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"identifier": "9876543210", "purpose": "REGISTRATION"},
    )
    assert requested.status_code == 201
    assert "otp" not in requested.json()
    assert len(delivery.codes) == 1
    challenge_id = requested.json()["challenge_id"]

    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "otp": delivery.codes[0]},
    )
    assert verified.status_code == 200
    assert verified.json()["registration_required"] is True
    assert "access_token" not in verified.json() or verified.json()["access_token"] is None

    replay = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "otp": delivery.codes[0]},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "OTP_VERIFICATION_FAILED"

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new-merchant@example.com",
            "phone_number": "9876543210",
            "password": "StrongPassword9",
            "business_name": "New Merchant",
            "store_name": "Main Store",
            "registration_token": verified.json()["registration_token"],
        },
    )
    assert registration.status_code == 201
    assert registration.json()["refresh_token"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registration.json()["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != registration.json()["refresh_token"]
    replay_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registration.json()["refresh_token"]},
    )
    assert replay_refresh.status_code == 401


def test_otp_expiry_and_attempt_limit(client, db_factory) -> None:
    delivery = CaptureOtpDelivery()
    client.app.state.otp_delivery = delivery
    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"identifier": "9876543211", "purpose": "REGISTRATION"},
    )
    challenge_id = requested.json()["challenge_id"]
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/otp/verify",
            json={"challenge_id": challenge_id, "otp": "000000"},
        )
        assert response.status_code == 401
    limited = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "otp": delivery.codes[0]},
    )
    assert limited.status_code == 401

    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"identifier": "9876543212", "purpose": "REGISTRATION"},
    )
    expired_id = requested.json()["challenge_id"]

    async def expire() -> None:
        async with db_factory() as session, session.begin():
            row = await session.scalar(
                    select(OtpChallenge).where(OtpChallenge.id == UUID(expired_id))
            )
            row.expires_at = utc_now() - timedelta(seconds=1)

    asyncio.run(expire())
    expired = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": expired_id, "otp": delivery.codes[-1]},
    )
    assert expired.status_code == 401


def test_oauth_existing_account_and_rejection(client, settings) -> None:
    settings.google_oauth_client_id = "google-client-id"
    client.app.state.oauth_verifier = FakeOAuthVerifier()
    start = client.post("/api/v1/auth/oauth/google/start")
    assert start.status_code == 201
    challenge = start.json()
    result = client.post(
        "/api/v1/auth/oauth/google/exchange",
        json={
            "challenge_id": challenge["challenge_id"],
            "state": challenge["state"],
            "nonce": challenge["nonce"],
            "id_token": "valid-provider-token-value",
        },
    )
    assert result.status_code == 200
    assert result.json()["registration_required"] is False
    assert result.json()["access_token"]

    second = client.post("/api/v1/auth/oauth/google/start").json()
    rejected = client.post(
        "/api/v1/auth/oauth/google/exchange",
        json={
            "challenge_id": second["challenge_id"],
            "state": second["state"],
            "nonce": second["nonce"],
            "id_token": "rejected-provider-token-value",
        },
    )
    assert rejected.status_code == 401
    assert rejected.json()["error"]["code"] == "OAUTH_CREDENTIAL_INVALID"


def test_otp_login_for_existing_merchant(client) -> None:
    delivery = CaptureOtpDelivery()
    client.app.state.otp_delivery = delivery
    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"identifier": "919000000000", "purpose": "LOGIN"},
    )
    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={
            "challenge_id": requested.json()["challenge_id"],
            "otp": delivery.codes[0],
        },
    )
    assert verified.status_code == 200
    assert verified.json()["registration_required"] is False
    profile = client.get(
        "/api/v1/merchants/me",
        headers={"Authorization": f"Bearer {verified.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["id"] == str(MERCHANT_ID)


def test_oauth_start_with_configured_google_client_id(client, settings) -> None:
    settings.google_oauth_client_id = "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    client.app.state.oauth_verifier = FakeOAuthVerifier()
    start = client.post("/api/v1/auth/oauth/google/start")
    assert start.status_code == 201
    payload = start.json()
    assert payload["client_id"] == "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    assert payload["provider"] == "GOOGLE"
    assert len(payload["state"]) >= 20
    assert len(payload["nonce"]) >= 20


def test_oauth_callback_endpoint(client) -> None:
    # Ready status when hitting without query params
    response = client.get("/api/v1/auth/oauth/google/callback")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

    # Error status when Google redirects with error
    err_resp = client.get(
        "/api/v1/auth/oauth/google/callback?error=access_denied&error_description=User+denied"
    )
    assert err_resp.status_code == 200
    assert err_resp.json()["status"] == "error"
    assert err_resp.json()["error"] == "access_denied"

    # Success status when Google redirects with code
    success_resp = client.get(
        "/api/v1/auth/oauth/google/callback?code=mock-auth-code&state=xyz123"
    )
    assert success_resp.status_code == 200
    assert success_resp.json()["status"] == "success"
    assert success_resp.json()["code"] == "mock-auth-code"


def test_oauth_code_exchange(client, settings) -> None:
    from pydantic import SecretStr

    settings.google_oauth_client_id = "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    settings.google_oauth_client_secret = SecretStr("TEST_OAUTH_CLIENT_SECRET_PLACEHOLDER")
    client.app.state.oauth_verifier = FakeOAuthVerifier()

    start = client.post("/api/v1/auth/oauth/google/start").json()
    result = client.post(
        "/api/v1/auth/oauth/google/exchange",
        json={
            "challenge_id": start["challenge_id"],
            "state": start["state"],
            "nonce": start["nonce"],
            "code": "sample-google-auth-code",
        },
    )
    assert result.status_code == 200
    assert result.json()["access_token"]


def test_oauth_new_user_registration(client, settings) -> None:
    settings.google_oauth_client_id = "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    client.app.state.oauth_verifier = FakeOAuthVerifier()

    start = client.post("/api/v1/auth/oauth/google/start").json()
    result = client.post(
        "/api/v1/auth/oauth/google/exchange",
        json={
            "challenge_id": start["challenge_id"],
            "state": start["state"],
            "nonce": start["nonce"],
            "id_token": "new-user-token-value",
        },
    )
    assert result.status_code == 200
    assert result.json()["registration_required"] is True
    assert result.json()["registration_token"]
    assert result.json()["email"] == "new-user@example.com"


def test_email_otp_request_and_verify(client) -> None:
    delivery = CaptureOtpDelivery()
    client.app.state.otp_delivery = delivery
    requested = client.post(
        "/api/v1/auth/otp/request",
        json={"identifier": "merchant@tuboxlabs.com", "purpose": "REGISTRATION"},
    )
    assert requested.status_code == 201
    assert "otp" not in requested.json()
    assert requested.json()["destination"] == "me•••@tuboxlabs.com"
    assert len(delivery.codes) == 1
    challenge_id = requested.json()["challenge_id"]

    verified = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_id, "otp": delivery.codes[0]},
    )
    assert verified.status_code == 200
    assert verified.json()["registration_required"] is True
    assert verified.json()["registration_token"]


def test_oauth_authorize_endpoint(client, settings) -> None:
    settings.google_oauth_client_id = "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    client.app.state.oauth_verifier = FakeOAuthVerifier()

    # JSON response
    response = client.get(
        "/api/v1/auth/oauth/google/authorize",
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "https://accounts.google.com/o/oauth2/v2/auth" in data["authorization_url"]
    assert "client_id=" in data["authorization_url"]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Foauth%2Fgoogle%2Fcallback" in data["authorization_url"]

    # Redirect response for browser
    redirect_resp = client.get(
        "/api/v1/auth/oauth/google/authorize",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )
    assert redirect_resp.status_code == 307
    assert "accounts.google.com" in redirect_resp.headers["location"]


def test_oauth_callback_auto_exchange(client, settings) -> None:
    from pydantic import SecretStr

    settings.google_oauth_client_id = "000000000000-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com"
    settings.google_oauth_client_secret = SecretStr("TEST_OAUTH_CLIENT_SECRET_PLACEHOLDER")
    client.app.state.oauth_verifier = FakeOAuthVerifier()

    start_resp = client.get(
        "/api/v1/auth/oauth/google/authorize",
        headers={"Accept": "application/json"},
    )
    state_payload = start_resp.json()["state"]

    # Auto-exchange JSON callback
    callback_resp = client.get(
        f"/api/v1/auth/oauth/google/callback?code=test-auth-code&state={state_payload}",
        headers={"Accept": "application/json"},
    )
    assert callback_resp.status_code == 200
    data = callback_resp.json()
    assert data["status"] == "authenticated"
    assert data["result"]["access_token"]

    # Auto-exchange HTML callback
    start_resp2 = client.get(
        "/api/v1/auth/oauth/google/authorize",
        headers={"Accept": "application/json"},
    )
    state_payload2 = start_resp2.json()["state"]
    html_resp = client.get(
        f"/api/v1/auth/oauth/google/callback?code=test-auth-code&state={state_payload2}",
        headers={"Accept": "text/html"},
    )
    assert html_resp.status_code == 200
    assert "Authentication Successful" in html_resp.text


def test_email_test_endpoint(client, settings) -> None:
    import httpx
    from pydantic import SecretStr
    from app.integrations.email.resend import ResendEmailProvider

    settings.resend_api_key = SecretStr("re_test_key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "mock-email-id-999"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.app.state.email_provider = ResendEmailProvider(
        api_key="re_test_key",
        client=mock_client,
    )

    resp = client.post("/api/v1/auth/email/test?to_email=delivered@resend.dev")
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"
    assert resp.json()["email_id"] == "mock-email-id-999"
