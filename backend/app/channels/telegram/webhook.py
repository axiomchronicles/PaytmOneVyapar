from typing import Any

from pydantic import BaseModel, Field


class TelegramInbound(BaseModel):
    update_id: int
    message_id: str
    chat_id: str
    sender_id: str
    sender_name: str = ""
    username: str | None = None
    kind: str  # "callback_query", "message", "command"
    text: str | None = None
    callback_data: str | None = None
    callback_query_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)


def parse_telegram_webhook(payload: dict[str, Any]) -> list[TelegramInbound]:
    """Parses incoming Telegram webhook payload into a normalized list of TelegramInbound items.

    Telegram typically sends one update per webhook POST, but handling a list allows batching.
    """
    updates = payload if isinstance(payload, list) else [payload]
    results: list[TelegramInbound] = []

    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id", 0)

        # 1. Callback Query (Interactive Button Click)
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = str(cb.get("id", ""))
            from_user = cb.get("from", {})
            sender_id = str(from_user.get("id", ""))
            sender_name = (
                f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()
            )
            username = from_user.get("username")
            msg = cb.get("message", {})
            msg_id = str(msg.get("message_id", cb_id))
            chat_id = str(msg.get("chat", {}).get("id") or sender_id)
            cb_data = cb.get("data")

            results.append(
                TelegramInbound(
                    update_id=update_id,
                    message_id=f"cb:{cb_id}",
                    chat_id=chat_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    username=username,
                    kind="callback_query",
                    text=cb_data,
                    callback_data=cb_data,
                    callback_query_id=cb_id,
                    raw=cb,
                )
            )

        # 2. Standard Message or Command
        elif "message" in update:
            msg = update["message"]
            msg_id = str(msg.get("message_id", ""))
            from_user = msg.get("from", {})
            sender_id = str(from_user.get("id", ""))
            sender_name = (
                f"{from_user.get('first_name', '')} {from_user.get('last_name', '')}".strip()
            )
            username = from_user.get("username")
            chat_id = str(msg.get("chat", {}).get("id", sender_id))
            text = msg.get("text", "")
            kind = "command" if text and text.startswith("/") else "message"

            results.append(
                TelegramInbound(
                    update_id=update_id,
                    message_id=f"msg:{msg_id}",
                    chat_id=chat_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    username=username,
                    kind=kind,
                    text=text,
                    callback_data=None,
                    callback_query_id=None,
                    raw=msg,
                )
            )

    return results
