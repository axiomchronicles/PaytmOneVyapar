from typing import Any

from pydantic import BaseModel, Field


class WhatsAppInbound(BaseModel):
    message_id: str
    sender: str
    kind: str
    text: str | None = None
    reply_id: str | None = None
    raw: dict[str, Any] = Field(exclude=True)


def parse_webhook(payload: dict[str, Any]) -> list[WhatsAppInbound]:
    messages: list[WhatsAppInbound] = []
    if payload.get("object") != "whatsapp_business_account":
        return messages
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                kind = message.get("type", "unknown")
                text = message.get("text", {}).get("body") if kind == "text" else None
                reply_id = None
                if kind == "interactive":
                    interaction = message.get("interactive", {})
                    reply = interaction.get("button_reply") or interaction.get("list_reply") or {}
                    reply_id = reply.get("id")
                messages.append(
                    WhatsAppInbound(
                        message_id=message["id"],
                        sender=message["from"],
                        kind=kind,
                        text=text,
                        reply_id=reply_id,
                        raw=message,
                    )
                )
    return messages
