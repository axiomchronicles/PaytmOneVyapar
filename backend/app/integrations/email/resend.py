from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.errors import ProviderAuthenticationError, ProviderError, ProviderTimeoutError

logger = logging.getLogger(__name__)


class ResendEmailProvider:
    """Resend email service provider using async HTTPX."""

    API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str = "Paytm ONE Vyapar <auth@tuboxlabs.com>",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.from_email = from_email
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None and not self._client.is_closed:
            return self._client
        return httpx.AsyncClient(timeout=10.0)

    async def send_email(
        self,
        *,
        to: str | list[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
        from_email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        recipients = [to] if isinstance(to, str) else to
        sender = from_email or self.from_email
        payload: dict[str, Any] = {
            "from": sender,
            "to": recipients,
            "subject": subject,
        }
        if html:
            payload["html"] = html
        if text:
            payload["text"] = text
        if not html and not text:
            payload["text"] = subject

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        client = await self._get_client()
        should_close = client is not self._client

        try:
            response = await client.post(self.API_URL, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Resend email delivery timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(f"Resend connection failed: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

        if response.status_code == 401:
            raise ProviderAuthenticationError("Invalid Resend API key")
        if response.status_code >= 400:
            error_data = (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            message = error_data.get("message", response.text)
            raise ProviderError(f"Resend email sending failed ({response.status_code}): {message}")

        return response.json()

    async def send_otp(
        self,
        to_email: str,
        otp: str,
        *,
        idempotency_key: str | None = None,
    ) -> str:
        subject = f"{otp} is your Paytm ONE Vyapar verification code"
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
    .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: #002970; padding: 28px 24px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .content {{ padding: 32px 28px; color: #1e293b; }}
    .otp-card {{ background: #f1f5f9; border-radius: 8px; border: 1px dashed #cbd5e1; text-align: center; padding: 20px; margin: 24px 0; }}
    .otp-code {{ font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #002970; font-family: monospace; }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #f1f5f9; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Paytm ONE Vyapar</h1>
    </div>
    <div class="content">
      <h2 style="margin-top:0;font-size:18px;">Verification Code</h2>
      <p style="font-size:14px;color:#475569;line-height:1.5;">Use the following One-Time Password (OTP) to securely sign in or complete your merchant verification. This code is valid for <strong>5 minutes</strong>.</p>
      <div class="otp-card">
        <span class="otp-code">{otp}</span>
      </div>
      <p style="font-size:13px;color:#64748b;line-height:1.4;">If you did not request this code, please ignore this email. Never share your OTP with anyone, including Paytm support.</p>
    </div>
    <div class="footer">
      &copy; Paytm ONE Vyapar &bull; Autonomous Merchant Operations Platform
    </div>
  </div>
</body>
</html>"""
        text = f"Your Paytm ONE Vyapar verification code is: {otp}\nValid for 5 minutes. Do not share this code."
        result = await self.send_email(
            to=to_email,
            subject=subject,
            html=html,
            text=text,
            idempotency_key=idempotency_key,
        )
        return result.get("id", "")

    async def send_welcome_email(
        self,
        to_email: str,
        *,
        business_name: str,
        store_name: str,
    ) -> str:
        subject = f"Welcome to Paytm ONE Vyapar, {business_name}!"
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
    .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: #002970; padding: 28px 24px; text-align: center; }}
    .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; }}
    .content {{ padding: 32px 28px; color: #1e293b; line-height: 1.6; }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #f1f5f9; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Paytm ONE Vyapar</h1>
    </div>
    <div class="content">
      <h2>Welcome aboard!</h2>
      <p>Your business <strong>{business_name}</strong> (Store: <strong>{store_name}</strong>) is now registered on Paytm ONE Vyapar.</p>
      <p>You can now manage stock, access AI voice Munim assistant, automated replenishment with A2A suppliers, and WhatsApp approvals.</p>
    </div>
    <div class="footer">
      &copy; Paytm ONE Vyapar &bull; Autonomous Merchant Operations Platform
    </div>
  </div>
</body>
</html>"""
        text = f"Welcome to Paytm ONE Vyapar!\n\nBusiness: {business_name}\nStore: {store_name}\n\nYour account is active."
        result = await self.send_email(
            to=to_email,
            subject=subject,
            html=html,
            text=text,
        )
        return result.get("id", "")
