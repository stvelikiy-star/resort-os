"""Opt-in single-property WhatsApp AI draft worker. Never sends messages.

The existing event ledger provides at-most-once model invocation per inbound
message. Claimed events are not retried after an uncertain process failure.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from .ai_sales import ai_sales_configured, _load_context, _draft_prompt, _openai_draft, _verified_availability
from .green_api_webhook import single_property_binding
from .public_ai_admin import AvailabilitySearch
from .whatsapp_quote_intent import extract_quote_intent

SOURCE = "WHATSAPP_AI_DRAFT"
EVENT = "WHATSAPP_AI_DRAFT_CLAIM"

# Only new, unassigned, open direct WhatsApp threads. No historical campaign,
# queued human reply, pre-existing AI draft or previously attempted message.
CANDIDATE_SQL = '''
SELECT c.id AS conversation_id,m.id AS message_id
FROM conversations c
JOIN communication_channels ch ON ch.id=c."channelId"
JOIN LATERAL (
    SELECT id,direction,"contentType","createdAt"
    FROM conversation_messages
    WHERE "conversationId"=c.id AND direction IN ('INBOUND','OUTBOUND')
    ORDER BY "createdAt" DESC,id DESC LIMIT 1
) m ON true
WHERE c."propertyId"=$1 AND ch."propertyId"=$1
  AND ch.kind='WHATSAPP' AND ch.code=$2 AND ch."externalAccountId"=$3
  AND c.status='OPEN' AND c."assignedToId" IS NULL
  AND m.direction='INBOUND' AND m."contentType"='TEXT'
  AND m."createdAt" > now() - interval '5 minutes'
  AND NOT EXISTS (
    SELECT 1 FROM conversation_messages d
    WHERE d."conversationId"=c.id AND d.direction='INTERNAL'
      AND d."senderType"='AI_DRAFT' AND d."createdAt">=m."createdAt"
  )
  AND NOT EXISTS (
    SELECT 1 FROM automation_inbound_events e
    WHERE e."propertyId"=$1 AND e.source=$4 AND e."idempotencyKey"=m.id::text
  )
ORDER BY m."createdAt",m.id LIMIT 1
'''


def worker_enabled() -> bool:
    return os.environ.get("ENABLE_GREEN_API_AI_DRAFT_WORKER") == "true"


async def _finish(conn, pid, job_id, result, resource_id=None):
    await conn.execute(
        '''UPDATE automation_inbound_events
           SET "resultResource"=$1,"resultResourceId"=$2,"updatedAt"=now()
           WHERE id=$3 AND "propertyId"=$4 AND source=$5 AND "resultResource" IS NULL''',
        result, resource_id, job_id, pid, SOURCE,
    )


async def _still_current(conn, pid, cid, mid):
    return await conn.fetchval(
        '''SELECT EXISTS(
             SELECT 1 FROM conversations c
             WHERE c.id=$1 AND c."propertyId"=$2 AND c.status='OPEN'
               AND c."assignedToId" IS NULL
               AND (SELECT id FROM conversation_messages
                    WHERE "conversationId"=c.id AND direction IN ('INBOUND','OUTBOUND')
                    ORDER BY "createdAt" DESC,id DESC LIMIT 1)=$3
               AND NOT EXISTS (
                   SELECT 1 FROM conversation_messages d, conversation_messages original
                   WHERE original.id=$3 AND d."conversationId"=c.id
                     AND d.direction='INTERNAL' AND d."senderType"='AI_DRAFT'
                     AND d."createdAt">=original."createdAt")
               AND NOT EXISTS (
                   SELECT 1 FROM automation_inbound_events e
                   WHERE e."propertyId"=$2 AND e."eventType"='COMMUNICATION_OUTBOUND_DISPATCH'
                     AND e."payloadJson"->>'conversation_id'=c.id::text
                     AND (e."resultResource" IS NULL OR e."resultResource"='OutboundReconciliationRequired'))
           )''', cid, pid, mid,
    )


async def run_once(app) -> str:
    if not worker_enabled():
        return "disabled"
    if not ai_sales_configured():
        return "provider_not_configured"
    binding = single_property_binding()
    pid = uuid.UUID(binding["bound_property_id"])
    pool = app.state.db
    async with pool.acquire() as lane:
        # One worker per hotel across API replicas; session lock is released
        # in finally or automatically when the DB session disconnects.
        lock = "whatsapp-ai-draft:" + str(pid)
        if not await lane.fetchval("SELECT pg_try_advisory_lock(hashtextextended($1,0))", lock):
            return "busy"
        try:
            if not await lane.fetchval('SELECT EXISTS(SELECT 1 FROM properties WHERE id=$1 AND code=$2)', pid, binding["property_code"]):
                return "property_mismatch"
            async with lane.transaction():
                # Make uncertain abandoned claims visible for staff; never
                # retry them or issue another model request for the same ID.
                await lane.execute(
                    '''UPDATE automation_inbound_events SET "resultResource"='AiDraftReviewRequired',"updatedAt"=now()
                       WHERE "propertyId"=$1 AND source=$2 AND "resultResource" IS NULL
                         AND "createdAt"<now()-interval '5 minutes' ''', pid, SOURCE)
                row = await lane.fetchrow(CANDIDATE_SQL, pid, binding["channel_code"], binding["external_account_id"], SOURCE)
                if not row:
                    return "idle"
                cid, mid = row["conversation_id"], row["message_id"]
                job = await lane.fetchval(
                    '''INSERT INTO automation_inbound_events
                       (id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt")
                       VALUES ($1,$2,$3,$4,$5,$6::jsonb,now(),now())
                       ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING RETURNING id''',
                    uuid.uuid4(), pid, SOURCE, str(mid), EVENT,
                    json.dumps({"conversation_id": str(cid), "message_id": str(mid)}),
                )
            if not job:
                return "duplicate"
            try:
                if not await _still_current(lane, pid, cid, mid):
                    await _finish(lane, pid, job, "AiDraftSuperseded")
                    return "superseded"
                context = await _load_context(lane, pid, cid)
                intent = extract_quote_intent(context["messages"], datetime.now(ZoneInfo(context["property"]["timezone"])).date())
                context["quote_intent"] = intent["intent"]
                if intent["intent"] == "staff_review":
                    async with lane.transaction():
                        await lane.execute('SELECT id FROM conversations WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', cid, pid)
                        if await _still_current(lane, pid, cid, mid):
                            await lane.execute("UPDATE conversations SET status='WAITING_STAFF',\"updatedAt\"=now() WHERE id=$1 AND \"propertyId\"=$2", cid, pid)
                            await _finish(lane, pid, job, "AiStaffHandoff")
                            return "handoff"
                        await _finish(lane, pid, job, "AiDraftSuperseded")
                        return "superseded"
                search = AvailabilitySearch.model_validate(intent["search"]) if intent["search"] else None
                context["current_availability"] = await _verified_availability(SimpleNamespace(app=app), pid, context, search)
                provider = await _openai_draft(_draft_prompt(context))
                async with lane.transaction():
                    await lane.execute('SELECT id FROM conversations WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', cid, pid)
                    if not await _still_current(lane, pid, cid, mid):
                        await _finish(lane, pid, job, "AiDraftSuperseded")
                        return "superseded"
                    draft = uuid.uuid4()
                    await lane.execute(
                        '''INSERT INTO conversation_messages
                           (id,"conversationId",direction,"senderType","senderExternalId",text,"contentType","deliveryStatus","rawPayload","createdAt")
                           VALUES ($1,$2,'INTERNAL','AI_DRAFT',NULL,$3,'TEXT','UNKNOWN',$4::jsonb,now())''',
                        draft, cid, provider["text"],
                        json.dumps({"provider":"openai","model":provider["model"],"auto_send":False,"source":"whatsapp_worker","inbound_message_id":str(mid)}),
                    )
                    await lane.execute("UPDATE conversations SET status='WAITING_STAFF',\"updatedAt\"=now() WHERE id=$1 AND \"propertyId\"=$2", cid, pid)
                    await _finish(lane, pid, job, "ConversationMessage", str(draft))
                return "draft_created"
            except Exception:
                async with lane.transaction():
                    await lane.execute('SELECT id FROM conversations WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', cid, pid)
                    if await _still_current(lane, pid, cid, mid):
                        await lane.execute("UPDATE conversations SET status='WAITING_STAFF',\"updatedAt\"=now() WHERE id=$1 AND \"propertyId\"=$2", cid, pid)
                    await _finish(lane, pid, job, "AiDraftReviewRequired")
                # Log no chat content, provider URL, exception or credentials.
                logging.getLogger(__name__).warning("WhatsApp AI draft job requires staff review")
                return "review_required"
        finally:
            await lane.execute("SELECT pg_advisory_unlock(hashtextextended($1,0))", lock)


async def run_worker(app):
    while True:
        try:
            await run_once(app)
        except Exception:
            logging.getLogger(__name__).warning("WhatsApp AI worker unavailable")
        await asyncio.sleep(15)
