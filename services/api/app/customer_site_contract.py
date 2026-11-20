"""Explicit, per-property customer site copy. Never inherit legacy resort defaults."""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

CUSTOMER_SITE_FIELDS: dict[str, tuple[str, ...]] = {
    "hero": ("title", "subtitle"),
    "contacts": ("phone", "whatsapp", "email", "address"),
    "seo": ("title", "description"),
}
SITE_LOCALES = frozenset({"ru", "kg", "en"})
PHONE_PATTERN = re.compile(r"\+?[0-9 ()-]{7,25}")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAX_FIELD_LEN = 350
MAX_TEXT_LEN = 1000


def validate_customer_site_content(locale: str, content: Any) -> dict[str, dict[str, str]]:
    """Validate ALL fields on draft and publication; no incomplete default can publish."""
    if locale not in SITE_LOCALES:
        raise HTTPException(404, detail="Unsupported locale")
    if not isinstance(content, dict) or set(content) != set(CUSTOMER_SITE_FIELDS):
        raise HTTPException(422, detail="Customer site requires explicit hero, contacts and seo sections")
    result: dict[str, dict[str, str]] = {}
    for section, allowed in CUSTOMER_SITE_FIELDS.items():
        item = content.get(section)
        if not isinstance(item, dict) or set(item) != set(allowed):
            raise HTTPException(422, detail=f"Customer site section {section} is incomplete")
        cleaned: dict[str, str] = {}
        for field in allowed:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_LEN:
                raise HTTPException(422, detail=f"Customer site {section}.{field} must be nonempty text")
            value = value.strip()
            if any(ord(char) < 32 for char in value) or len(value) > MAX_FIELD_LEN and field != "subtitle":
                raise HTTPException(422, detail=f"Customer site {section}.{field} has invalid characters/length")
            if field in ("phone", "whatsapp") and (
                not PHONE_PATTERN.fullmatch(value) or not 7 <= sum(char.isdigit() for char in value) <= 15
            ):
                raise HTTPException(422, detail=f"Customer site {field} must be a phone number")
            if field == "email" and not EMAIL_PATTERN.fullmatch(value):
                raise HTTPException(422, detail="Customer site email is invalid")
            cleaned[field] = value
        result[section] = cleaned
    return result


def project_legacy_published_content(locale: str, content: Any) -> dict[str, dict[str, str]]:
    """Read-only compatibility view for pre-upgrade published CMS documents.

    Never mutate the original stored JSON or invent missing customer facts.
    New publications remain subject to the exact customer-site schema.
    """
    if not isinstance(content, dict):
        raise HTTPException(422, detail="Legacy published site content must be an object")
    hero = content.get("hero")
    contacts = content.get("contacts")
    seo = content.get("seo")
    if not all(isinstance(section, dict) for section in (hero, contacts, seo)):
        raise HTTPException(422, detail="Legacy published site requires hero, contacts and seo")
    subtitle = hero.get("subtitle") or hero.get("copy")
    projected = {
        "hero": {"title": hero.get("title"), "subtitle": subtitle},
        "contacts": {field: contacts.get(field) for field in CUSTOMER_SITE_FIELDS["contacts"]},
        "seo": {field: seo.get(field) for field in CUSTOMER_SITE_FIELDS["seo"]},
    }
    return validate_customer_site_content(locale, projected)
