import re
import uuid
from typing import Any

from fastapi import HTTPException


def normalize_guest_phone(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        digits = "996" + digits[1:]
    elif len(digits) == 9:
        digits = "996" + digits
    return f"+{digits}"


def normalize_guest_email(value: str | None) -> str | None:
    if value is None:
        return None
    email = value.strip().lower()
    return email or None


async def resolve_or_create_guest(
    conn,
    *,
    property_id: uuid.UUID,
    guest_name: str,
    phone: str | None,
    email: str | None,
) -> dict[str, Any]:
    """Resolve exactly one existing guest or create one without silent history merges."""
    normalized_phone = normalize_guest_phone(phone)
    normalized_email = normalize_guest_email(email)

    phone_matches = []
    email_matches = []

    if normalized_phone:
        phone_matches = await conn.fetch(
            '''
            SELECT id,"firstName","lastName",phone,email
            FROM guests
            WHERE "propertyId"=$1
              AND regexp_replace(COALESCE(phone,''),'\\D','','g') = regexp_replace($2,'\\D','','g')
            ORDER BY "updatedAt" DESC,id
            FOR UPDATE
            ''',
            property_id,
            normalized_phone,
        )
        if len(phone_matches) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "GUEST_IDENTITY_AMBIGUOUS",
                    "message": "Multiple existing guest profiles share this phone. Review duplicate candidates before confirming the reservation.",
                    "identity": "PHONE",
                    "guest_ids": [str(row["id"]) for row in phone_matches],
                },
            )

    if normalized_email:
        email_matches = await conn.fetch(
            '''
            SELECT id,"firstName","lastName",phone,email
            FROM guests
            WHERE "propertyId"=$1 AND lower(trim(COALESCE(email,'')))=$2
            ORDER BY "updatedAt" DESC,id
            FOR UPDATE
            ''',
            property_id,
            normalized_email,
        )
        if len(email_matches) > 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "GUEST_IDENTITY_AMBIGUOUS",
                    "message": "Multiple existing guest profiles share this email. Review duplicate candidates before confirming the reservation.",
                    "identity": "EMAIL",
                    "guest_ids": [str(row["id"]) for row in email_matches],
                },
            )

    phone_match = phone_matches[0] if phone_matches else None
    email_match = email_matches[0] if email_matches else None

    if phone_match and email_match and phone_match["id"] != email_match["id"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "GUEST_IDENTITY_CONFLICT",
                "message": "Phone and email belong to different existing guest profiles. Resolve manually before confirming the reservation.",
                "phone_guest_id": str(phone_match["id"]),
                "email_guest_id": str(email_match["id"]),
            },
        )

    existing = phone_match or email_match
    if existing:
        guest_id = existing["id"]
        await conn.execute(
            '''
            UPDATE guests
            SET "firstName"=CASE WHEN COALESCE(trim("firstName"),'')='' THEN $2 ELSE "firstName" END,
                phone=COALESCE(phone,$3),
                email=COALESCE(email,$4),
                "updatedAt"=now()
            WHERE id=$1
            ''',
            guest_id,
            guest_name.strip() or None,
            normalized_phone,
            normalized_email,
        )
        return {
            "guest_id": guest_id,
            "created": False,
            "matched_by": "PHONE_AND_EMAIL" if phone_match and email_match else ("PHONE" if phone_match else "EMAIL"),
            "phone": normalized_phone or existing["phone"],
            "email": normalized_email or existing["email"],
        }

    guest_id = uuid.uuid4()
    await conn.execute(
        '''
        INSERT INTO guests (id,"propertyId","firstName",phone,email,"createdAt","updatedAt")
        VALUES ($1,$2,$3,$4,$5,now(),now())
        ''',
        guest_id,
        property_id,
        guest_name.strip() or None,
        normalized_phone,
        normalized_email,
    )
    return {
        "guest_id": guest_id,
        "created": True,
        "matched_by": "NEW",
        "phone": normalized_phone,
        "email": normalized_email,
    }
