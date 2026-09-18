import asyncio
import hashlib
import hmac

import httpx

from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError


class MetaWhatsAppProvider:
    def __init__(
        self,
        *,
        access_token: str,
        phone_number_id: str,
        graph_api_version: str,
        client: httpx.AsyncClient,
    ) -> None:
        if not graph_api_version:
            raise ValueError("WHATSAPP_GRAPH_API_VERSION is required when WhatsApp is enabled")
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.graph_api_version = graph_api_version
        self.client = client

    async def send_text(self, recipient: str, body: str, *, idempotency_key: str) -> str:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        return await self._send(payload, idempotency_key)

    async def send_approval(self, recipient: str, proposal: dict, *, idempotency_key: str) -> str:
        approval_id = proposal["approval_id"]
        body = (
            f"Purchase {proposal['quantity']} {proposal['unit']} of {proposal['sku']} "
            f"at INR {proposal['unit_price']} each? Total INR {proposal['total_amount']}."
        )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": f"approval:{approval_id}:APPROVE", "title": "Approve"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": f"approval:{approval_id}:MODIFY", "title": "Modify"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": f"approval:{approval_id}:REJECT", "title": "Reject"},
                        },
                    ]
                },
            },
        }
        return await self._send(payload, idempotency_key)

    async def _send(self, payload: dict, idempotency_key: str) -> str:
        url = f"https://graph.facebook.com/{self.graph_api_version}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
        }
        for attempt in range(3):
            try:
                response = await self.client.post(url, json=payload, headers=headers)
                if response.status_code in {401, 403}:
                    raise ProviderAuthenticationError("Meta WhatsApp authentication failed")
                response.raise_for_status()
                return response.json()["messages"][0]["id"]
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise ProviderTimeoutError("Meta WhatsApp request timed out") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == 2:
                    raise ProviderError(
                        "Meta WhatsApp request failed",
                        details={"status": exc.response.status_code},
                    ) from exc
            await asyncio.sleep(0.25 * (2**attempt))
        raise ProviderError("Meta WhatsApp request failed")


def verify_webhook_signature(
    raw_body: bytes, signature_header: str | None, app_secret: str
) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    supplied = signature_header.removeprefix("sha256=")
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)
