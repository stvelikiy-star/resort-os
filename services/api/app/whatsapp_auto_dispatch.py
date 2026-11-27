"""Single-hotel automatic quote dispatch, via the same Inbox and GREEN-API adapter."""
import json
import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from .communication_ingest import NormalizedChannelMessage, ingest_normalized_channel_message
from .green_api_webhook import DIRECT_CHAT, single_property_binding
from .green_outbound import _provider_send
from .whatsapp_connection import _configuration
from .whatsapp_auto_reply import activation_time, build_quote_reply


async def dispatch_quote(app, lane, binding, pid, cid, mid, context, intent, still_current):
    cutoff = activation_time(os.environ)
    if cutoff is None:
        return None
    text = build_quote_reply(intent, context.get("current_availability"),
                             context["property"]["currency"], context["messages"])
    if not text:
        return None
    if single_property_binding() != binding or str(pid) != binding["bound_property_id"]:
        return None
    config = _configuration({"property_code": binding["property_code"]})
    if config is None or config[1] != binding["external_account_id"]:
        return None
    source = ("OUTBOX_" + binding["channel_code"])[:60]
    key = "ai-quote:" + str(mid)
    async with lane.transaction():
        # Serialize automatic reservation of dispatch with human outbox admission.
        row = await lane.fetchrow(
            '''SELECT c."externalConversationId",c."externalContactId",ch."displayName"
               FROM conversations c JOIN communication_channels ch ON ch.id=c."channelId"
               WHERE c.id=$1 AND c."propertyId"=$2 AND ch."propertyId"=$2
                 AND ch.kind='WHATSAPP' AND ch.code=$3 AND ch."externalAccountId"=$4
               FOR UPDATE OF c''', cid, pid, binding["channel_code"], binding["external_account_id"])
        if not row or not DIRECT_CHAT.fullmatch(str(row["externalConversationId"])):
            return None
        if not await still_current(lane, pid, cid, mid):
            return "superseded"
        if not await lane.fetchval(
            '''SELECT EXISTS(SELECT 1 FROM conversation_messages
               WHERE id=$1 AND "conversationId"=$2 AND direction='INBOUND'
                 AND "createdAt">=$3::timestamp)''', mid, cid, cutoff.replace(tzinfo=None)):
            return None
        recent = await lane.fetchval(
            '''SELECT COUNT(*)::int FROM automation_inbound_events
               WHERE "propertyId"=$1 AND source=$2 AND "eventType"='COMMUNICATION_OUTBOUND_DISPATCH'
                 AND "payloadJson"->>'auto_send'='true' AND "createdAt">now()-interval '1 hour' ''', pid, source)
        if recent >= 30:
            return None
        if await lane.fetchval(
            '''SELECT EXISTS(SELECT 1 FROM automation_inbound_events
               WHERE "propertyId"=$1 AND source=$2 AND "eventType"='COMMUNICATION_OUTBOUND_DISPATCH'
                 AND "payloadJson"->>'conversation_id'=$3 AND "payloadJson"->>'auto_send'='true'
                 AND "createdAt">now()-interval '5 minutes')''', pid, source, str(cid)):
            return None
        dispatch_id = await lane.fetchval(
            '''INSERT INTO automation_inbound_events
               (id,"propertyId",source,"idempotencyKey","eventType","payloadJson","createdAt","updatedAt")
               VALUES ($1,$2,$3,$4,'COMMUNICATION_OUTBOUND_DISPATCH',$5::jsonb,now(),now())
               ON CONFLICT ("propertyId",source,"idempotencyKey") DO NOTHING RETURNING id''',
            uuid.uuid4(), pid, source, key,
            json.dumps({"conversation_id":str(cid),"channel_code":binding["channel_code"],
                        "actor_id":"marina-ai-quote","auto_send":True,"inbound_message_id":str(mid),"text":text}))
    if not dispatch_id:
        return "duplicate"
    # Durable reservation is committed BEFORE any irreversible provider call.
    # Never retry an ambiguous result, even if the API process restarts.
    try:
        if activation_time(os.environ) != cutoff:
            await lane.execute('''UPDATE automation_inbound_events SET "resultResource"='AiDispatchCancelled',"updatedAt"=now() WHERE id=$1''', dispatch_id)
            return "superseded"
        identifier = await _provider_send(config, row["externalConversationId"], text)
        payload = NormalizedChannelMessage(
            idempotency_key="ai:queued:" + str(mid), channel_code=binding["channel_code"],
            channel_kind="WHATSAPP", channel_display_name=row["displayName"],
            external_account_id=binding["external_account_id"],
            external_conversation_id=row["externalConversationId"],
            external_contact_id=row["externalContactId"], direction="OUTBOUND",
            external_message_id=identifier, sender_type="AI", sender_external_id="marina-ai-quote",
            text=text, content_type="TEXT", delivery_status="QUEUED", sent_at=datetime.now(timezone.utc),
            raw_payload={"provider":"green-api","evidence":"ACCEPTED_TO_QUEUE_ONLY","auto_send":True})
        result = await ingest_normalized_channel_message(payload, SimpleNamespace(app=app),
                    {**binding,"actor_id":"marina-ai-quote"})
        async with lane.transaction():
            await lane.execute(
                '''UPDATE automation_inbound_events SET "resultResource"='ConversationMessage',
                   "resultResourceId"=$1,"updatedAt"=now() WHERE id=$2''', result["id"], dispatch_id)
            await lane.execute(
                '''UPDATE conversations SET status='WAITING_GUEST',"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2 AND status='OPEN' AND "assignedToId" IS NULL
                     AND NOT EXISTS (SELECT 1 FROM conversation_messages newer, conversation_messages original
                         WHERE original.id=$3 AND newer."conversationId"=$1 AND newer.direction='INBOUND'
                           AND newer."createdAt">original."createdAt")''', cid, pid, mid)
        return "auto_queued"
    except Exception:
        async with lane.transaction():
            await lane.execute(
                '''UPDATE automation_inbound_events SET "resultResource"='OutboundReconciliationRequired',
                   "updatedAt"=now() WHERE id=$1 AND "resultResource" IS NULL''', dispatch_id)
            await lane.execute(
                '''UPDATE conversations SET status='WAITING_STAFF',"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2 AND status='OPEN' AND "assignedToId" IS NULL''', cid,pid)
        return "auto_review_required"
