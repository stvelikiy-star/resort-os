"""Owner-only immutable primary-document bytes for financial correction evidence.

The API computes SHA-256 over the actual received bytes, not a user-declared
string. PostgreSQL stores the original bytes with transactional metadata so a
database backup/restore includes the evidence. The bounded input deliberately
avoids a new S3 or Ubuntu filesystem dependency during this release.
A matching hash proves byte integrity, NOT legal/issuer authenticity.
"""
import base64
import binascii
import hashlib
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from starlette.responses import Response

from .auth import require_roles, trusted_property_id
from .owner_revenue_source_journal import lock_keys

router = APIRouter(prefix="/api/v1/admin/finance/owner/revenue-evidence",
                   tags=["owner-revenue-primary-document"])
owner_only = require_roles("OWNER", module_grant=False)
MAX_BYTES = 2 * 1024 * 1024
MAX_BASE64_LENGTH = ((MAX_BYTES + 2) // 3) * 4
ALLOWED_MEDIA = ("application/pdf", "image/png", "image/jpeg")


class EvidenceUpload(BaseModel):
    id: uuid.UUID
    document_reference: str = Field(min_length=4, max_length=150)
    document_date: date
    file_name: str = Field(min_length=1, max_length=128)
    media_type: Literal["application/pdf","image/png","image/jpeg"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_base64: str = Field(min_length=4, max_length=MAX_BASE64_LENGTH)

    @field_validator("document_reference")
    @classmethod
    def normalize_doc_reference(cls, value):
        normalized=" ".join(value.split())
        if len(normalized)<4:
            raise ValueError("Document reference is blank")
        return normalized

    @field_validator("file_name")
    @classmethod
    def safe_file_name(cls, value):
        if (value != value.strip() or not value.strip() or
            any(ord(ch)<32 or ch in "/\\\"" for ch in value) or
            value in (".","..")):
            raise ValueError("Unsafe filename")
        return value


def content_type_matches(raw:bytes, media_type:str)->bool:
    if media_type=="application/pdf":
        return raw.startswith(b"%PDF-") and len(raw)>=16
    if media_type=="image/png":
        return raw.startswith(bytes.fromhex("89504e470d0a1a0a")) and len(raw)>=24
    if media_type=="image/jpeg":
        return raw.startswith(bytes.fromhex("ffd8ff")) and raw.endswith(bytes.fromhex("ffd9")) and len(raw)>=16
    return False


def decode_and_verify(encoded:str, expected_sha:str, media_type:str)->bytes:
    if len(encoded)>MAX_BASE64_LENGTH:
        raise HTTPException(413,detail={"code":"REVENUE_DOCUMENT_TOO_LARGE"})
    try:
        raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):
        raise HTTPException(422,detail={"code":"REVENUE_DOCUMENT_INVALID_BASE64"})
    if not (16<=len(raw)<=MAX_BYTES):
        raise HTTPException(413,detail={"code":"REVENUE_DOCUMENT_SIZE_INVALID"})
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected_sha:
        raise HTTPException(409,detail={"code":"REVENUE_DOCUMENT_SHA256_MISMATCH"})
    if not content_type_matches(raw,media_type):
        raise HTTPException(422,detail={"code":"REVENUE_DOCUMENT_MEDIA_SIGNATURE"})
    return raw


def evidence_view(row,repeated=False):
    return {
        "id":str(row["id"]),
        "document_reference":row["documentReference"],
        "document_date":row["documentDate"].isoformat(),
        "file_name":row["fileName"],
        "media_type":row["mediaType"],
        "sha256":row["sha256"],
        "size_bytes":row["sizeBytes"],
        "created_at":row["createdAt"].isoformat(),
        "already_processed":repeated,
        "bytes_sha256_verified_by_server":True,
        "document_authenticity_independently_verified":False,
        "recognized_revenue_kgs":None,
        "recognized_profit_kgs":None,
    }


@router.post("",status_code=201)
async def save_evidence(body:EvidenceUpload,request:Request,user=Depends(owner_only)):
    raw=decode_and_verify(body.content_base64,body.sha256,body.media_type)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            owner_id=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"revenue-evidence:"+str(body.id))
            prior=await conn.fetchrow(
                'SELECT * FROM owner_revenue_evidence_documents WHERE id=$1',body.id)
            if prior:
                if (prior["propertyId"]!=pid or
                    prior["documentReference"]!=body.document_reference or
                    prior["documentDate"]!=body.document_date or
                    prior["fileName"]!=body.file_name or
                    prior["mediaType"]!=body.media_type or
                    prior["sha256"]!=body.sha256 or
                    bytes(prior["content"])!=raw or
                    prior["uploadedById"]!=owner_id):
                    raise HTTPException(409,detail={"code":"REVENUE_DOCUMENT_ID_CONFLICT"})
                return evidence_view(prior,True)
            row=await conn.fetchrow(
                '''INSERT INTO owner_revenue_evidence_documents
                    (id,"propertyId","documentReference","documentDate",
                     "fileName","mediaType","sha256",content,"sizeBytes","uploadedById")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *''',
                body.id,pid,body.document_reference,body.document_date,
                body.file_name,body.media_type,body.sha256,raw,len(raw),owner_id)
            return evidence_view(row)


@router.get("/{document_id}")
async def evidence_metadata(document_id:uuid.UUID,request:Request,
                            user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        row=await conn.fetchrow(
            '''SELECT id,"documentReference","documentDate","fileName","mediaType",
                      sha256,"sizeBytes","createdAt"
               FROM owner_revenue_evidence_documents
               WHERE id=$1 AND "propertyId"=$2''',document_id,pid)
        if not row:
            raise HTTPException(404,detail={"code":"REVENUE_DOCUMENT_NOT_FOUND"})
        return evidence_view(row)


@router.get("/{document_id}/content")
async def evidence_bytes(document_id:uuid.UUID,request:Request,
                         user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        row=await conn.fetchrow(
            '''SELECT content,"mediaType",sha256 FROM owner_revenue_evidence_documents
               WHERE id=$1 AND "propertyId"=$2''',document_id,pid)
        if not row:
            raise HTTPException(404,detail={"code":"REVENUE_DOCUMENT_NOT_FOUND"})
        content=bytes(row["content"])
        if hashlib.sha256(content).hexdigest()!=row["sha256"]:
            raise HTTPException(503,detail={"code":"REVENUE_STORED_DOCUMENT_HASH_DRIFT"})
        extension={"application/pdf":"pdf","image/png":"png","image/jpeg":"jpg"}[row["mediaType"]]
        return Response(
            content=content,media_type=row["mediaType"],
            headers={
                "Content-Disposition":f'attachment; filename="evidence-{document_id}.{extension}"',
                "Cache-Control":"private, no-store",
                "X-Content-Type-Options":"nosniff",
                "X-Document-Sha256":row["sha256"],
            })
