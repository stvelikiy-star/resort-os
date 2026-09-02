from __future__ import annotations

PLACEHOLDER_MARKERS = ("change_me", "example.invalid", "example.com")
MIN_WEBHOOK_SECRET_LENGTH = 24


def is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return not lowered or any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def validate_provider_env(values: dict[str, str]) -> list[str]:
    """Return fail-closed provider credential/secret configuration errors.

    Providers remain optional. Validation becomes mandatory only when the
    corresponding launch credential is configured.
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

    return errors
