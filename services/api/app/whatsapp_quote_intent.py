"""Conservative offline extraction of explicit WhatsApp quote parameters.

No model request, side effects, inferred year, occupancy or reservation action.
Ambiguous guest messages are left for clarification or staff review.
"""
import re
from datetime import date

_DATE = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4})"
_RANGE = re.compile(r"(?<!\d)(" + _DATE + r")\s*(?:[-–—]|по|до|to|until|чейин)\s*(" + _DATE + r")(?!\d)", re.I)
_DATE_TOKEN = re.compile(r"(?<!\d)" + _DATE + r"(?!\d)")
_ADULT = re.compile(r"(?<!\d)(\d{1,2})\s*(?:взросл(?:ых|ый|ого|ые)?|adult(?:s)?|чоң\s*киши|чоңдор)(?!\w)", re.I)
_CHILD = re.compile(r"(?<!\d)(\d{1,2})\s*(?:дет(?:ей|и)|реб[её]н(?:ок|ка)|child(?:ren)?|kids?|бал(?:а|дар))(?!\w)", re.I)
_NO_CHILD = re.compile(r"\b(?:без детей|no children|no kids|баласыз)\b", re.I)
_HANDOFF = re.compile(r"плат[её]ж|оплат|возврат|отмен|жалоб|администратор|оператор|подтвердите брон|refund|payment|cancel|complaint|human agent|confirm (?:my )?booking|төлөм|кайтар|администраторго", re.I)
_CORRECTION = re.compile(r"\b(?:не|not|instead|вместо|или|or|эмес|же)\b", re.I)


def _date(value: str) -> date:
    if "." in value:
        d, m, y = map(int, value.split("."))
        return date(y, m, d)
    return date.fromisoformat(value)


def extract_quote_intent(messages: list[dict], today: date) -> dict:
    # Only the newest uninterrupted guest turn. Never use assistant text
    # as evidence, and never silently carry old parameters across turns.
    parts = []
    for msg in reversed(messages):
        if msg.get("direction") != "INBOUND":
            break
        if msg.get("content_type") != "TEXT" or not isinstance(msg.get("text"), str):
            return {"intent": "clarify", "search": None}
        parts.append(msg["text"])
        if len(parts) >= 6:
            break
    text = "\n".join(reversed(parts))
    if not text:
        return {"intent": "clarify", "search": None}
    if _HANDOFF.search(text):
        return {"intent": "staff_review", "search": None}
    ranges = list(_RANGE.finditer(text))
    dates = _DATE_TOKEN.findall(text)
    adult = _ADULT.findall(text)
    child = _CHILD.findall(text)
    no_child = bool(_NO_CHILD.search(text))
    if not dates and not adult and not child and not no_child:
        return {"intent": "consultation", "search": None}
    if (len(ranges) != 1 or len(dates) != 2 or len(adult) != 1
            or len(child) > 1 or (child and no_child) or not (child or no_child)
            or _CORRECTION.search(text)):
        return {"intent": "clarify", "search": None}
    try:
        start, end = map(_date, ranges[0].groups())
        adults, children = int(adult[0]), int(child[0]) if child else 0
        if not (today <= start < end and (end - start).days <= 60
                and 1 <= adults <= 20 and 0 <= children <= 20):
            raise ValueError("out of bounds")
    except ValueError:
        return {"intent": "clarify", "search": None}
    return {"intent": "availability", "search": {
        "check_in": start.isoformat(), "check_out": end.isoformat(),
        "adults": adults, "children": children,
    }}
