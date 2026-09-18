import httpx
import pytest

from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError
from app.integrations.email.resend import ResendEmailProvider


@pytest.mark.asyncio
async def test_resend_send_email_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.resend.com/emails"
        assert request.headers["Authorization"] == "Bearer mock-api-key"
        assert request.headers["Content-Type"] == "application/json"
        assert request.headers["Idempotency-Key"] == "idem-123"
        return httpx.Response(200, json={"id": "msg-001"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(
        api_key="mock-api-key",
        from_email="Paytm ONE Vyapar <auth@tuboxlabs.com>",
        client=client,
    )

    result = await provider.send_email(
        to="merchant@tuboxlabs.com",
        subject="Test Subject",
        html="<p>Test</p>",
        idempotency_key="idem-123",
    )
    assert result["id"] == "msg-001"


@pytest.mark.asyncio
async def test_resend_send_otp_success() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured_payload.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"id": "otp-msg-123"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(
        api_key="mock-api-key",
        from_email="Paytm ONE Vyapar <auth@tuboxlabs.com>",
        client=client,
    )

    email_id = await provider.send_otp("user@tuboxlabs.com", "654321")
    assert email_id == "otp-msg-123"
    assert captured_payload["to"] == ["user@tuboxlabs.com"]
    assert "654321" in captured_payload["subject"]
    assert "654321" in captured_payload["html"]
    assert "654321" in captured_payload["text"]


@pytest.mark.asyncio
async def test_resend_send_welcome_email_success() -> None:
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured_payload.update(json.loads(request.content.decode()))
        return httpx.Response(200, json={"id": "welcome-msg-456"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(
        api_key="mock-api-key",
        from_email="Paytm ONE Vyapar <auth@tuboxlabs.com>",
        client=client,
    )

    email_id = await provider.send_welcome_email(
        "owner@store.com",
        business_name="Sharma Kirana",
        store_name="Main Branch",
    )
    assert email_id == "welcome-msg-456"
    assert "Sharma Kirana" in captured_payload["subject"]
    assert "Sharma Kirana" in captured_payload["html"]


@pytest.mark.asyncio
async def test_resend_auth_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Invalid API key"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(api_key="bad-key", client=client)

    with pytest.raises(ProviderAuthenticationError):
        await provider.send_email(to="test@example.com", subject="Hello")


@pytest.mark.asyncio
async def test_resend_timeout_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Timeout contacting Resend")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(api_key="key", client=client)

    with pytest.raises(ProviderTimeoutError):
        await provider.send_email(to="test@example.com", subject="Hello")


@pytest.mark.asyncio
async def test_resend_bad_request_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "Invalid domain"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = ResendEmailProvider(api_key="key", client=client)

    with pytest.raises(ProviderError) as exc_info:
        await provider.send_email(to="test@example.com", subject="Hello")
    assert "Invalid domain" in str(exc_info.value)
