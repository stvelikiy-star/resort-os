from __future__ import annotations

PLACEHOLDER_MARKERS = ("change_me", "example.invalid", "example.com")
MIN_WEBHOOK_SECRET_LENGTH = 24


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def validate_provider_env(values: dict[str, str]) -> list[str]:
    """Return fail-closed provider credential/secret configuration errors.

    Providers remain optional. Validation becomes mandatory only when the
    corresponding provider/model path is configured.
    """
    errors: list[str] = []

    telegram_sales_token = values.get("TELEGRAM_SALES_BOT_TOKEN", "").strip()
    telegram_sales_secret = values.get("TELEGRAM_SALES_WEBHOOK_SECRET", "").strip()
    if telegram_sales_token:
        if is_placeholder(telegram_sales_token):
            errors.append("TELEGRAM_SALES_BOT_TOKEN is still a placeholder")
        if is_placeholder(telegram_sales_secret):
            errors.append("Telegram Sales is enabled without a real TELEGRAM_SALES_WEBHOOK_SECRET")
        elif len(telegram_sales_secret) < MIN_WEBHOOK_SECRET_LENGTH:
            errors.append(f"TELEGRAM_SALES_WEBHOOK_SECRET must be at least {MIN_WEBHOOK_SECRET_LENGTH} characters")

    green_id = values.get("GREEN_API_ID_INSTANCE", "").strip()
    green_token = values.get("GREEN_API_TOKEN_INSTANCE", "").strip()
    green_secret = values.get("GREEN_API_WEBHOOK_SECRET", "").strip()
    if green_id or green_token:
        if is_placeholder(green_id) or is_placeholder(green_token):
            errors.append("GREEN API credentials are partially configured or still placeholders")
        if is_placeholder(green_secret):
            errors.append("GREEN API is enabled without a real GREEN_API_WEBHOOK_SECRET")
        elif len(green_secret) < MIN_WEBHOOK_SECRET_LENGTH:
            errors.append(f"GREEN_API_WEBHOOK_SECRET must be at least {MIN_WEBHOOK_SECRET_LENGTH} characters")

    openai_key = values.get("OPENAI_API_KEY", "").strip()
    configured_models = [
        values.get("OPENAI_PUBLIC_ASSISTANT_MODEL", "").strip(),
        values.get("OPENAI_WHATSAPP_MODEL", "").strip(),
        values.get("OPENAI_SALES_MODEL", "").strip(),
        values.get("OPENAI_TRANSCRIBE_MODEL", "").strip(),
    ]
    if openai_key and is_placeholder(openai_key):
        errors.append("OPENAI_API_KEY is still a placeholder")
    if any(configured_models) and is_placeholder(openai_key):
        errors.append("An OpenAI model is configured without a real OPENAI_API_KEY")

    staff_bot_token = values.get("TELEGRAM_BOT_TOKEN", "").strip()
    transcribe_model = values.get("OPENAI_TRANSCRIBE_MODEL", "").strip()
    staff_webhook_secret = values.get("TELEGRAM_STAFF_WEBHOOK_SECRET", "").strip()
    if staff_bot_token and transcribe_model:
        if is_placeholder(staff_bot_token):
            errors.append("TELEGRAM_BOT_TOKEN is still a placeholder for Staff Voice")
        if is_placeholder(staff_webhook_secret):
            errors.append("Staff Voice transcription is enabled without a real TELEGRAM_STAFF_WEBHOOK_SECRET")
        elif len(staff_webhook_secret) < MIN_WEBHOOK_SECRET_LENGTH:
            errors.append(f"TELEGRAM_STAFF_WEBHOOK_SECRET must be at least {MIN_WEBHOOK_SECRET_LENGTH} characters")

    return errors
