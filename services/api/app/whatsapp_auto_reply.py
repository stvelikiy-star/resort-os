"""Deterministic, narrowly scoped WhatsApp quote replies. No external effects."""
import re
from datetime import datetime, timezone, date

def activation_time(env):
    if (env.get("ENABLE_GREEN_API_AI_AUTO_SEND") != "true"
            or env.get("GREEN_API_AI_AUTO_SEND_CONFIRM") != "OWNER_APPROVED_SINGLE_HOTEL_QUOTES"
            or env.get("ENABLE_GREEN_API_SINGLE_OUTBOUND") != "true"):
        return None
    try:
        value = datetime.fromisoformat(env.get("GREEN_API_AI_AUTO_SEND_FROM", ""))
        return value.astimezone(timezone.utc) if value.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def build_quote_reply(intent, availability, currency, messages):
    """Only exact, positively available PMS options. Other cases stay manual."""
    if intent.get("intent") != "availability" or not isinstance(availability, dict) or currency != "KGS":
        return None
    search = intent.get("search") or {}
    try:
        start = date.fromisoformat(str(availability["check_in"]))
        end = date.fromisoformat(str(availability["check_out"]))
        if (start.isoformat() != search["check_in"] or end.isoformat() != search["check_out"]
                or availability["adults"] != search["adults"] or availability["children"] != search["children"]
                or availability["nights"] != (end-start).days):
            return None
    except (KeyError, ValueError, TypeError):
        return None
    options = availability.get("options")
    if not isinstance(options, list) or not options:
        return None
    latest = []
    for m in reversed(messages):
        if m.get("direction") != "INBOUND":
            break
        latest.append(str(m.get("text") or ""))
    text = " ".join(latest)
    # No guessed language: use explicit occupancy markers in supported formats.
    if re.search(r"\b(?:adults?|children|kids?)\b", text, re.I):
        lang = "en"
    elif re.search(r"чоң|баласыз|бала", text, re.I):
        lang = "kg"
    elif re.search(r"взросл|детей|реб[её]н", text, re.I):
        lang = "ru"
    else:
        return None
    lines = []
    for item in options[:3]:
        if not isinstance(item, dict):
            return None
        name, price, count = item.get("room_type_name"), item.get("total_kgs"), item.get("available_count")
        if (not isinstance(name, str) or not re.fullmatch(r"[\w .()/-]{1,100}", name)
                or type(price) is not int or price <= 0 or type(count) is not int or count <= 0):
            return None
        lines.append(f"• {name}: {price:,}".replace(",", " ") + (" KGS" if lang == "en" else " сом"))
    dates = f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"
    headers = {
        "ru": f"MARINA AI: по данным гостиницы на {dates} доступны следующие варианты. Стоимость за весь указанный период:",
        "kg": f"MARINA AI: {dates} күндөрүнө мейманкананын маалыматы боюнча төмөнкү варианттар бар. Көрсөтүлгөн мөөнөттүн жалпы баасы:",
        "en": f"MARINA AI: the hotel currently has the following options for {dates}. Total price for the requested stay:",
    }
    footers = {
        "ru": "Наличие и цена могут измениться. Это не бронь. Если хотите оформить заявку, напишите нам.",
        "kg": "Бош орундар жана баа өзгөрүшү мүмкүн. Бул брондоо эмес. Өтүнмө калтыргыңыз келсе, бизге жазыңыз.",
        "en": "Availability and prices may change. This is not a reservation. Reply if you would like to submit a request.",
    }
    return headers[lang] + "\n" + "\n".join(lines) + "\n" + footers[lang]
