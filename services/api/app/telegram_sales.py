import hmac
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status

from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message

router = APIRouter(prefix="/api/v1/channels/telegram", tags=["channel-telegram"])

TELEGRAM_SALES_BOT_TOKEN = os.environ.get("TELEGRAM_SALES_BOT_TOKEN")
TELEGRAM_SALES_WEBHOOK_SECRET = os.environ.get("TELEGRAM_SALES_WEBHOOK_SECRET")
TELEGRAM_SALES_CHANNEL_CODE = os.environ.get("TELEGRAM_SALES_CHANNEL_CODE", "TELEGRAM_SALES")
TELEGRAM_SALES_DISPLAY_NAME = os.environ.get("TELEGRAM_SALES_DISPLAY_NAME", "Telegram Sales")
TELEGRAM_SALES_ACCOUNT_ID = os.environ.get("TELEGRAM_SALES_ACCOUNT_ID")
TELEGRAM_PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("TELEGRAM_PROVIDER_TIMEOUT_SECONDS", "10"))


def telegram_sales_inbound_configured() -> bool:
    return bool(TELEGRAM_SALES_WEBHOOK_SECRET)


def telegram_sales_outbound_configured() -> bool:
    return bool(TELEGRAM_SALES_BOT_TOKEN)


def _require_webhook_secret(value: str | None) -> None:
    if not TELEGRAM_SALES_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram Sales webhook is not configured",
        )
    if not value or not hmac.compare_digest(value, TELEGRAM_SALES_WEBHOOK_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret",
        )


def _contact_name(sender: dict[str, Any]) -> str | None:
    parts = [sender.get("first_name"), sender.get("last_name")]
    value = " ".join(str(part).strip() for part in parts if part and str(part).strip())
    return value[:180] or None


def _content_type(message: dict[str, Any]) -> str:
    if message.get("text") is not None:
        return "TEXT"
    if message.get("voice") is not None:
        return "VOICE"
    if message.get("audio") is not None:
        return "AUDIO"
    if message.get("photo") is not None:
        return "PHOTO"
    if message.get("video") is not None:
        return "VIDEO"
    if message.get("video_note") is not None:
        return "VIDEO_NOTE"
    if message.get("document") is not None:
        return "DOCUMENT"
    if message.get("contact") is not None:
        return "CONTACT"
    if message.get("location") is not None:
        return "LOCATION"
    if message.get("sticker") is not None:
        return "STICKER"
    return "OTHER"


def _telegram_message(update: dict[str, Any]) -> dict[str, Any] | None:
    # Initial Sales adapter intentionally processes new user messages only.
    # Edited/channel/business/callback updates remain ignored until an explicit
    # contract is approved for them.
    message = update.get("message")
    return message if isinstance(message, dict) else None


async def send_telegram_text(chat_id: str, text: str) -> dict[str, Any]:
    """Call Telegram Bot API sendMessage and report evidence, not assumptions.

    SENT means Telegram returned HTTP success with `ok=true` and a Message.
    FAILED means Telegram returned a definite provider rejection.
    UNKNOWN means the network/timeout failed and Core cannot know whether the
    provider received the request. UNKNOWN must never be retried automatically
    with the same business intent because Bot API sendMessage has no client
    idempotency key.
    """
    if not TELEGRAM_SALES_BOT_TOKEN:
        return {
            "state": "FAILED",
            "description": "Telegram Sales outbound is not configured",
            "provider_status_code": None,
            "provider_payload": None,
            "message_id": None,
            "sent_at": None,
        }

    url = f"https://api.telegram.org/bot{TELEGRAM_SALES_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json={"chat_id": chat_id, "text": text})
    except httpx.RequestError as exc:
        return {
            "state": "UNKNOWN",
            "description": f"Telegram request transport error: {exc.__class__.__name__}",
            "provider_status_code": None,
            "provider_payload": None,
            "message_id": None,
            "sent_at": None,
        }

    try:
        data = response.json()
    except ValueError:
        data = {"ok": False, "description": "Telegram returned non-JSON response"}

    if not isinstance(data, dict):
        data = {"ok": False, "description": "Telegram returned invalid response payload"}

    result = data.get("result") if isinstance(data.get("result"), dict) else None
    message_id = result.get("message_id") if result else None

    if response.is_success and data.get("ok") is True and isinstance(message_id, int):
        unix_date = result.get("date")
        sent_at = (
            datetime.fromtimestamp(unix_date, tz=timezone.utc)
            if isinstance(unix_date, int) and unix_date >= 0
            else datetime.now(timezone.utc)
        )
        return {
            "state": "SENT",
            "description": None,
            "provider_status_code": response.status_code,
            "provider_payload": data,
            "message_id": message_id,
            "sent_at": sent_at,
        }

    description = data.get("description")
    if not isinstance(description, str):
        description = f"Telegram rejected sendMessage with HTTP {response.status_code}"
    return {
        "state": "FAILED",
        "description": description[:1000],
        "provider_status_code": response.status_code,
        "provider_payload": data,
        "message_id": None,
        "sent_at": None,
    }


@router.post("/webhook")
async def telegram_sales_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
):
    _require_webhook_secret(x_telegram_bot_api_secret_token)

    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram JSON payload") from exc

    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Telegram update must be an object")

    update_id = update.get("update_id")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=422, detail="Telegram update_id is required")

    message = _telegram_message(update)
    if message is None:
        return {
            "accepted": True,
            "ignored": True,
            "reason": "unsupported_update_type",
            "update_id": update_id,
        }

    chat = message.get("chat")
    if not isinstance(chat, dict) or not isinstance(chat.get("id"), int):
        raise HTTPException(status_code=422, detail="Telegram message.chat.id is required")

    # Sales bot is a direct guest channel. Group/supergroup/channel traffic is
    # ignored rather than silently turning group chatter into sales leads.
    if chat.get("type") != "private":
        return {
            "accepted": True,
            "ignored": True,
            "reason": "non_private_chat",
            "update_id": update_id,
        }

    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    if sender.get("is_bot") is True:
        return {
            "accepted": True,
            "ignored": True,
            "reason": "bot_sender",
            "update_id": update_id,
        }

    message_id = message.get("message_id")
    if not isinstance(message_id, int):
        raise HTTPException(status_code=422, detail="Telegram message_id is required")

    chat_id = str(chat["id"])
    sender_id = str(sender["id"]) if isinstance(sender.get("id"), int) else None
    contact = message.get("contact") if isinstance(message.get("contact"), dict) else {}
    phone_number = contact.get("phone_number") if isinstance(contact.get("phone_number"), str) else None

    unix_date = message.get("date")
    sent_at = (
        datetime.fromtimestamp(unix_date, tz=timezone.utc)
        if isinstance(unix_date, int) and unix_date >= 0
        else None
    )

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        caption = message.get("caption")
        text = caption if isinstance(caption, str) and caption.strip() else None

    payload = NormalizedChannelMessage(
        idempotency_key=f"telegram:update:{update_id}",
        channel_code=TELEGRAM_SALES_CHANNEL_CODE,
        channel_kind="TELEGRAM",
        channel_display_name=TELEGRAM_SALES_DISPLAY_NAME,
        external_account_id=TELEGRAM_SALES_ACCOUNT_ID,
        external_conversation_id=chat_id,
        external_contact_id=sender_id,
        contact_name=_contact_name(sender),
        contact_phone=phone_number,
        contact_username=(
            str(sender["username"])[:180]
            if sender.get("username") is not None
            else None
        ),
        direction="INBOUND",
        external_message_id=f"{chat_id}:{message_id}",
        sender_type="GUEST",
        sender_external_id=sender_id,
        text=text,
        content_type=_content_type(message),
        delivery_status="RECEIVED",
        sent_at=sent_at,
        raw_payload=update,
    )

    result = await ingest_normalized_channel_message(
        payload,
        request,
        {
            "actor_type": "SERVICE",
            "actor_id": "telegram-sales-webhook",
        },
    )

    return {
        "accepted": True,
        "ignored": False,
        "update_id": update_id,
        **result,
    }
