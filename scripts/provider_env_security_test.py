#!/usr/bin/env python3
from __future__ import annotations

from provider_env_security import is_placeholder, validate_provider_env


def has(errors: list[str], fragment: str) -> bool:
    return any(fragment in error for error in errors)


def main() -> None:
    for value in (
        "",
        "CHANGE_ME_SECRET",
        "changeme-token",
        "REPLACE_ME_NOW",
        "replace-with-real-secret",
        "PLACEHOLDER_TOKEN",
        "https://example.invalid/token",
        "YOUR_API_TOKEN",
        "your-token-here",
        "NOT_SET",
        "not-set-yet",
        "TODO_SECRET",
    ):
        assert is_placeholder(value), value
    assert not is_placeholder("real-looking-token-value-abcdefghijklmnopqrstuvwxyz")

    assert validate_provider_env({}) == []

    telegram_placeholder = validate_provider_env(
        {
            "TELEGRAM_SALES_BOT_TOKEN": "123456:real-looking-token",
            "TELEGRAM_SALES_WEBHOOK_SECRET": "PLACEHOLDER_SECRET",
        }
    )
    assert has(telegram_placeholder, "real TELEGRAM_SALES_WEBHOOK_SECRET")

    telegram_short = validate_provider_env(
        {
            "TELEGRAM_SALES_BOT_TOKEN": "123456:real-looking-token",
            "TELEGRAM_SALES_WEBHOOK_SECRET": "too-short",
        }
    )
    assert has(telegram_short, "at least 24 characters")

    telegram_good = validate_provider_env(
        {
            "TELEGRAM_SALES_BOT_TOKEN": "123456:real-looking-token",
            "TELEGRAM_SALES_WEBHOOK_SECRET": "telegram-webhook-secret-abcdefghijklmnopqrstuvwxyz",
        }
    )
    assert telegram_good == []

    green_partial = validate_provider_env({"GREEN_API_ID_INSTANCE": "1234567890"})
    assert has(green_partial, "partially configured or still placeholders")
    assert has(green_partial, "real GREEN_API_WEBHOOK_SECRET")

    green_short = validate_provider_env(
        {
            "GREEN_API_ID_INSTANCE": "1234567890",
            "GREEN_API_TOKEN_INSTANCE": "real-looking-token-value",
            "GREEN_API_WEBHOOK_SECRET": "too-short",
        }
    )
    assert has(green_short, "GREEN_API_WEBHOOK_SECRET must be at least 24 characters")

    green_good = validate_provider_env(
        {
            "GREEN_API_ID_INSTANCE": "1234567890",
            "GREEN_API_TOKEN_INSTANCE": "real-looking-token-value",
            "GREEN_API_WEBHOOK_SECRET": "green-webhook-secret-abcdefghijklmnopqrstuvwxyz",
        }
    )
    assert green_good == []

    openai_missing = validate_provider_env({"OPENAI_SALES_MODEL": "gpt-test-model"})
    assert has(openai_missing, "without a real OPENAI_API_KEY")

    openai_placeholder = validate_provider_env(
        {
            "OPENAI_SALES_MODEL": "gpt-test-model",
            "OPENAI_API_KEY": "REPLACE_ME_OPENAI_KEY",
        }
    )
    assert has(openai_placeholder, "OPENAI_API_KEY is still a placeholder")
    assert has(openai_placeholder, "without a real OPENAI_API_KEY")

    openai_good = validate_provider_env(
        {
            "OPENAI_SALES_MODEL": "gpt-test-model",
            "OPENAI_API_KEY": "sk-real-looking-ci-key-abcdefghijklmnopqrstuvwxyz",
        }
    )
    assert openai_good == []

    staff_placeholder = validate_provider_env(
        {
            "TELEGRAM_BOT_TOKEN": "PLACEHOLDER_STAFF_BOT",
            "OPENAI_TRANSCRIBE_MODEL": "transcribe-test-model",
            "OPENAI_API_KEY": "sk-real-looking-ci-key-abcdefghijklmnopqrstuvwxyz",
            "TELEGRAM_STAFF_WEBHOOK_SECRET": "PLACEHOLDER_STAFF_SECRET",
        }
    )
    assert has(staff_placeholder, "TELEGRAM_BOT_TOKEN is still a placeholder for Staff Voice")
    assert has(staff_placeholder, "real TELEGRAM_STAFF_WEBHOOK_SECRET")

    staff_short = validate_provider_env(
        {
            "TELEGRAM_BOT_TOKEN": "123456:real-looking-staff-token",
            "OPENAI_TRANSCRIBE_MODEL": "transcribe-test-model",
            "OPENAI_API_KEY": "sk-real-looking-ci-key-abcdefghijklmnopqrstuvwxyz",
            "TELEGRAM_STAFF_WEBHOOK_SECRET": "too-short",
        }
    )
    assert has(staff_short, "TELEGRAM_STAFF_WEBHOOK_SECRET must be at least 24 characters")

    staff_good = validate_provider_env(
        {
            "TELEGRAM_BOT_TOKEN": "123456:real-looking-staff-token",
            "OPENAI_TRANSCRIBE_MODEL": "transcribe-test-model",
            "OPENAI_API_KEY": "sk-real-looking-ci-key-abcdefghijklmnopqrstuvwxyz",
            "TELEGRAM_STAFF_WEBHOOK_SECRET": "staff-webhook-secret-abcdefghijklmnopqrstuvwxyz",
        }
    )
    assert staff_good == []

    print("PROVIDER_ENV_SECURITY_TEST_OK")


if __name__ == "__main__":
    main()
