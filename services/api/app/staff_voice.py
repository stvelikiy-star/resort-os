import hmac
import json
import os
import re
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status

router = APIRouter(prefix="/api/v1/channels/telegram/staff", tags=["channel-telegram-staff"])

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_STAFF_WEBHOOK_SECRET = os.environ.get("TELEGRAM_STAFF_WEBHOOK_SECRET")
TELEGRAM_BOT_API_BASE_URL = os.environ.get("TELEGRAM_BOT_API_BASE_URL", "https://api.telegram.org").rstrip("/")
TELEGRAM_PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("TELEGRAM_PROVIDER_TIMEOUT_SECONDS", "10"))
STAFF_VOICE_MAX_BYTES = int(os.environ.get("STAFF_VOICE_MAX_BYTES", "20000000"))
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_TRANSCRIBE_MODEL = os.environ.get("OPENAI_TRANSCRIBE_MODEL")
OPENAI_API_BASE_URL = os.environ.get("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_TRANSCRIBE_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_TRANSCRIBE_TIMEOUT_SECONDS", "60"))

ALLOWED_VOICE_ROLES = {"TECHNICIAN", "MANAGER", "OWNER"}
SOURCE = "TELEGRAM_STAFF_VOICE"


def staff_voice_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_STAFF_WEBHOOK_SECRET and OPENAI_API_KEY and OPENAI_TRANSCRIBE_MODEL)


def _require_webhook_secret(value: str | None) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_STAFF_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Telegram staff voice webhook is not configured")
    if not value or not hmac.compare_digest(value, TELEGRAM_STAFF_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid Telegram staff webhook secret")


def _normalize_room_code(value: str) -> str:
    return re.sub(r"\s+", "", value.upper().replace("Ё", "Е"))


def _room_matches(transcript: str, room_codes: list[str]) -> list[str]:
    normalized_text = transcript.upper().replace("Ё", "Е")
    matches: list[str] = []
    for room_code in room_codes:
        code = _normalize_room_code(room_code)
        if not code:
            continue
        pattern = rf"(?<![\w]){re.escape(code)}(?![\w])"
        compact_text = re.sub(r"\s+", "", normalized_text) if any(ch.isalpha() for ch in code) else normalized_text
        if re.search(pattern, compact_text):
            matches.append(room_code)
    return matches


async def _telegram_file_bytes(file_id: str, declared_size: int | None) -> bytes:
    if declared_size is not None and declared_size > STAFF_VOICE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Telegram voice file exceeds configured size limit")

    get_file_url = f"{TELEGRAM_BOT_API_BASE_URL}/bot{TELEGRAM_BOT_TOKEN}/getFile"
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_PROVIDER_TIMEOUT_SECONDS) as client:
            meta_response = await client.post(get_file_url, json={"file_id": file_id})
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Telegram getFile transport error: {exc.__class__.__name__}") from exc

    try:
        meta = meta_response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Telegram getFile returned non-JSON response") from exc
    if not meta_response.is_success or not isinstance(meta, dict) or meta.get("ok") is not True:
        raise HTTPException(status_code=502, detail="Telegram getFile failed")
    result = meta.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("file_path"), str):
        raise HTTPException(status_code=502, detail="Telegram getFile returned no file_path")
    provider_size = result.get("file_size")
    if isinstance(provider_size, int) and provider_size > STAFF_VOICE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Telegram voice file exceeds configured size limit")

    download_url = f"{TELEGRAM_BOT_API_BASE_URL}/file/bot{TELEGRAM_BOT_TOKEN}/{result['file_path'].lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_PROVIDER_TIMEOUT_SECONDS) as client:
            response = await client.get(download_url)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Telegram file download transport error: {exc.__class__.__name__}") from exc
    if not response.is_success:
        raise HTTPException(status_code=502, detail="Telegram file download failed")
    if len(response.content) > STAFF_VOICE_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Telegram voice file exceeds configured size limit")
    if not response.content:
        raise HTTPException(status_code=422, detail="Telegram voice file is empty")
    return response.content


async def _transcribe_voice(content: bytes) -> str:
    if not OPENAI_API_KEY or not OPENAI_TRANSCRIBE_MODEL:
        raise HTTPException(status_code=503, detail="Audio transcription provider is not configured")
    try:
        async with httpx.AsyncClient(timeout=OPENAI_TRANSCRIBE_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{OPENAI_API_BASE_URL}/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                data={"model": OPENAI_TRANSCRIBE_MODEL},
                files={"file": ("telegram-voice.ogg", content, "audio/ogg")},
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Transcription transport error: {exc.__class__.__name__}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Transcription provider returned non-JSON response") from exc
    if not response.is_success or not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Transcription provider rejected audio")
    text = data.get("text")
    if not isinstance(text, str) or len(text.strip()) < 2:
        raise HTTPException(status_code=422, detail="No usable speech transcript")
    return text.strip()[:8000]


async def _release_failed_event(request: Request, property_id: uuid.UUID, idempotency_key: str) -> None:
    async with request.app.state.db.acquire() as conn:
        await conn.execute(
            '''DELETE FROM automation_inbound_events
               WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3 AND "resultResource" IS NULL''',
            property_id,
            SOURCE,
            idempotency_key,
        )


@router.get("/voice-capabilities")
async def staff_voice_capabilities():
    return {
        "configured": staff_voice_configured(),
        "allowed_roles": sorted(ALLOWED_VOICE_ROLES),
        "max_bytes": STAFF_VOICE_MAX_BYTES,
        "priority_policy": "NORMAL_ONLY_UNTIL_EXPLICIT_SEVERITY_RULES_ARE_APPROVED",
        "room_policy": "EXACT_SINGLE_MATCH_ELSE_REVIEW_WITHOUT_ROOM_BLOCK",
    }


@router.post("/webhook")
async def telegram_staff_voice_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    _require_webhook_secret(x_telegram_bot_api_secret_token)
    if not OPENAI_API_KEY or not OPENAI_TRANSCRIBE_MODEL:
        raise HTTPException(status_code=503, detail="Audio transcription provider is not configured")

    try:
        update = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram JSON payload") from exc
    if not isinstance(update, dict) or not isinstance(update.get("update_id"), int):
        raise HTTPException(status_code=422, detail="Telegram update_id is required")

    update_id = update["update_id"]
    message = update.get("message")
    if not isinstance(message, dict):
        return {"accepted": True, "ignored": True, "reason": "unsupported_update_type", "update_id": update_id}
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return {"accepted": True, "ignored": True, "reason": "non_private_chat", "update_id": update_id}
    if not isinstance(sender, dict) or not isinstance(sender.get("id"), int) or sender.get("is_bot") is True:
        return {"accepted": True, "ignored": True, "reason": "invalid_sender", "update_id": update_id}
    voice = message.get("voice")
    if not isinstance(voice, dict):
        return {"accepted": True, "ignored": True, "reason": "not_voice", "update_id": update_id}
    file_id = voice.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise HTTPException(status_code=422, detail="Telegram voice.file_id is required")

    telegram_user_id = str(sender["id"])
    idempotency_key = f"telegram:update:{update_id}"

    async with request.app.state.db.acquire() as conn:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
        if not property_id:
            raise HTTPException(status_code=503, detail="Property not loaded")
        staff = await conn.fetchrow(
            '''
            SELECT id,username,"displayName",role::text AS role
            FROM staff_users
            WHERE "propertyId"=$1 AND "telegramUserId"=$2 AND "isActive"=true
            ''',
            property_id,
            telegram_user_id,
        )
        if not staff:
            raise HTTPException(status_code=403, detail="Telegram account is not linked to active staff")
        if staff["role"] not in ALLOWED_VOICE_ROLES:
            raise HTTPException(status_code=403, detail="Staff role cannot create maintenance voice intake")

        event_id = await conn.fetchval(
            '''
            INSERT INTO automation_inbound_events (
              id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt"
            ) VALUES ($1,$2,$3,$4,'STAFF_VOICE',$5::jsonb,now(),now())
            ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING
            RETURNING id
            ''',
            uuid.uuid4(), property_id, SOURCE, idempotency_key,
            json.dumps({"update_id": update_id, "telegram_user_id": telegram_user_id, "message_id": message.get("message_id"), "file_unique_id": voice.get("file_unique_id")}),
        )
        if event_id is None:
            existing = await conn.fetchrow(
                '''SELECT "resultResource","resultResourceId" FROM automation_inbound_events
                   WHERE "propertyId"=$1 AND source=$2 AND "idempotencyKey"=$3''',
                property_id, SOURCE, idempotency_key,
            )
            return {
                "accepted": True,
                "idempotent_replay": True,
                "resource": existing["resultResource"] if existing else None,
                "id": existing["resultResourceId"] if existing else None,
                "update_id": update_id,
            }

    try:
        audio = await _telegram_file_bytes(file_id, voice.get("file_size") if isinstance(voice.get("file_size"), int) else None)
        transcript = await _transcribe_voice(audio)

        async with request.app.state.db.acquire() as conn:
            room_rows = await conn.fetch('SELECT id,code,"operationalState"::text AS state FROM rooms WHERE "propertyId"=$1 ORDER BY code', property_id)
            matches = _room_matches(transcript, [row["code"] for row in room_rows])
            room_by_code = {row["code"]: row for row in room_rows}
            matched_room = room_by_code[matches[0]] if len(matches) == 1 else None

            async with conn.transaction():
                task_id = uuid.uuid4()
                room_code = matched_room["code"] if matched_room else None
                title = f"Ремонт · № {room_code}" if room_code else "Ремонт · номер требует уточнения"
                await conn.execute(
                    '''
                    INSERT INTO operational_tasks (
                      id,"propertyId","roomId",type,status,priority,title,description,
                      "createdByType","createdById",source,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,'MAINTENANCE','OPEN','NORMAL',$4,$5,'STAFF',$6,$7,now(),now())
                    ''',
                    task_id, property_id, matched_room["id"] if matched_room else None,
                    title, transcript, str(staff["id"]), SOURCE,
                )
                room_state = matched_room["state"] if matched_room else None
                if matched_room:
                    await conn.execute('UPDATE rooms SET "operationalState"=\'TECH_BLOCK\',"updatedAt"=now() WHERE id=$1', matched_room["id"])
                    room_state = "TECH_BLOCK"

                await conn.execute(
                    '''UPDATE automation_inbound_events
                       SET "resultResource"='OperationalTask',"resultResourceId"=$1,"payloadJson"=$2::jsonb,"updatedAt"=now()
                       WHERE id=$3''',
                    str(task_id),
                    json.dumps({
                        "update_id": update_id,
                        "telegram_user_id": telegram_user_id,
                        "staff_user_id": str(staff["id"]),
                        "transcript": transcript,
                        "room_matches": matches,
                        "room_code": room_code,
                        "priority": "NORMAL",
                    }, ensure_ascii=False),
                    event_id,
                )
                await conn.execute(
                    '''
                    INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                    VALUES ($1,$2,'STAFF',$3,'VOICE_MAINTENANCE_INTAKE','OperationalTask',$4,$5,'SUCCESS',
                      jsonb_build_object('room_code',$6::text,'room_match_count',$7::int,'room_state',$8::text,'priority','NORMAL'),now())
                    ''',
                    uuid.uuid4(), property_id, str(staff["id"]), str(task_id), SOURCE,
                    room_code, len(matches), room_state,
                )

        return {
            "accepted": True,
            "idempotent_replay": False,
            "update_id": update_id,
            "task_id": str(task_id),
            "type": "MAINTENANCE",
            "priority": "NORMAL",
            "transcript": transcript,
            "room_code": room_code,
            "room_match_count": len(matches),
            "needs_room_review": len(matches) != 1,
            "room_state": room_state,
        }
    except HTTPException:
        await _release_failed_event(request, property_id, idempotency_key)
        raise
    except Exception:
        await _release_failed_event(request, property_id, idempotency_key)
        raise
