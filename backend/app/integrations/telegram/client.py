import asyncio
import html
from typing import Any

import httpx
import structlog

from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError

logger = structlog.get_logger()


class TelegramBotProvider:
    """Telegram Bot API provider for sending notifications, interactive approvals,

    answering callback queries, and managing bot webhooks.
    """

    def __init__(
        self,
        *,
        bot_token: str,
        client: httpx.AsyncClient,
        base_url: str = "https://api.telegram.org",
    ) -> None:
        if not bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is required when Telegram provider is instantiated"
            )
        self.bot_token = bot_token
        self.client = client
        self.base_api_url = f"{base_url.rstrip('/')}/bot{self.bot_token}"

    async def send_text(
        self,
        recipient: str | int,
        body: str,
        *,
        idempotency_key: str | None = None,
        parse_mode: str = "HTML",
    ) -> str:
        """Send a standard text message to a Telegram chat."""
        payload: dict[str, Any] = {
            "chat_id": str(recipient),
            "text": body,
            "parse_mode": parse_mode,
        }
        result = await self._call("sendMessage", payload, idempotency_key=idempotency_key)
        return str(result["message_id"])

    async def send_approval(
        self,
        recipient: str | int,
        proposal: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> str:
        """Send an interactive purchase proposal approval card with inline buttons."""
        approval_id = proposal["approval_id"]
        sku = html.escape(str(proposal.get("sku", "Unknown SKU")))
        quantity = proposal.get("quantity", "0")
        unit = html.escape(str(proposal.get("unit", "units")))
        unit_price = proposal.get("unit_price", "0")
        total_amount = proposal.get("total_amount", "0")
        currency = html.escape(str(proposal.get("currency", "INR")))
        delivery_at = proposal.get("delivery_at")
        supplier_name = html.escape(str(proposal.get("supplier_name", "Preferred Supplier")))

        delivery_line = (
            f"\n📅 <b>Delivery by:</b> {html.escape(str(delivery_at))}" if delivery_at else ""
        )

        text = (
            f"📦 <b>PURCHASE APPROVAL REQUIRED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Item:</b> {sku}\n"
            f"<b>Quantity:</b> {quantity} {unit}\n"
            f"<b>Supplier:</b> {supplier_name}\n"
            f"<b>Rate:</b> {currency} {unit_price} / {unit}\n"
            f"<b>Total:</b> <b>{currency} {total_amount}</b>"
            f"{delivery_line}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Decision required. Tap an action below:</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Approve Order",
                        "callback_data": f"approval:{approval_id}:APPROVE",
                    },
                    {
                        "text": "✏️ Modify",
                        "callback_data": f"approval:{approval_id}:MODIFY",
                    },
                ],
                [
                    {
                        "text": "❌ Decline",
                        "callback_data": f"approval:{approval_id}:REJECT",
                    }
                ],
            ]
        }

        payload: dict[str, Any] = {
            "chat_id": str(recipient),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup,
        }
        result = await self._call("sendMessage", payload, idempotency_key=idempotency_key)
        return str(result["message_id"])

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        *,
        show_alert: bool = False,
    ) -> bool:
        """Acknowledge a button tap from Telegram UI to dismiss loading spinner."""
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        try:
            result = await self._call("answerCallbackQuery", payload)
            return bool(result)
        except Exception as exc:
            logger.warning("telegram_answer_callback_failed", error=str(exc))
            return False

    async def edit_message_text(
        self,
        chat_id: str | int,
        message_id: int | str,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """Update a previously sent message, e.g. after approval decision."""
        payload: dict[str, Any] = {
            "chat_id": str(chat_id),
            "message_id": int(message_id),
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            result = await self._call("editMessageText", payload)
            return bool(result)
        except Exception as exc:
            logger.warning("telegram_edit_message_failed", error=str(exc))
            return False

    async def get_me(self) -> dict[str, Any]:
        """Fetch bot identity from Telegram API."""
        return await self._call("getMe", {})

    async def set_webhook(self, url: str, *, secret_token: str | None = None) -> bool:
        """Configure Telegram webhook endpoint."""
        payload: dict[str, Any] = {"url": url}
        if secret_token:
            payload["secret_token"] = secret_token
        result = await self._call("setWebhook", payload)
        return bool(result)

    async def get_webhook_info(self) -> dict[str, Any]:
        """Retrieve current webhook status from Telegram."""
        return await self._call("getWebhookInfo", {})

    async def delete_webhook(self, drop_pending_updates: bool = False) -> bool:
        """Remove active webhook."""
        payload = {"drop_pending_updates": drop_pending_updates}
        result = await self._call("deleteWebhook", payload)
        return bool(result)

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        limit: int = 100,
        poll_timeout: int = 20,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Long-poll incoming updates from Telegram when webhook is not active."""
        payload: dict[str, Any] = {
            "limit": limit,
            "timeout": poll_timeout,
        }
        if offset is not None:
            payload["offset"] = offset
        if allowed_updates is not None:
            payload["allowed_updates"] = allowed_updates
        result = await self._call("getUpdates", payload, timeout_override=float(poll_timeout + 5))
        return list(result or [])

    async def _call(
        self,
        method: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        timeout_override: float | None = None,
    ) -> Any:
        url = f"{self.base_api_url}/{method}"
        headers = {"Content-Type": "application/json"}
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        for attempt in range(3):
            try:
                kw = {"timeout": timeout_override} if timeout_override else {}
                response = await self.client.post(url, json=payload, headers=headers, **kw)

                if response.status_code in {401, 403}:
                    raise ProviderAuthenticationError(
                        f"Telegram bot authentication failed: {response.text}"
                    )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    desc = data.get("description", "Unknown Telegram API error")
                    raise ProviderError(f"Telegram API error: {desc}")
                return data.get("result")

            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise ProviderTimeoutError("Telegram API request timed out") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == 2:
                    raise ProviderError(
                        "Telegram API request failed",
                        details={"status": exc.response.status_code, "body": exc.response.text},
                    ) from exc
            except (ProviderAuthenticationError, ProviderError):
                raise
            except Exception as exc:
                if attempt == 2:
                    raise ProviderError(f"Telegram client error: {str(exc)}") from exc

            await asyncio.sleep(0.25 * (2**attempt))

        raise ProviderError("Telegram API request failed after retries")


def verify_telegram_secret(received_secret: str | None, expected_secret: str | None) -> bool:
    """Verify the X-Telegram-Bot-Api-Secret-Token header."""
    if not expected_secret:
        return True
    if not received_secret:
        return False
    import hmac

    return hmac.compare_digest(received_secret, expected_secret)
