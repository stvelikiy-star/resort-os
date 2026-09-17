import os

from fastapi import APIRouter


router = APIRouter(prefix="/api/v1/runtime", tags=["runtime-capabilities"])


def env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def capabilities() -> dict[str, bool]:
    return {
        "public_site": env_flag("ENABLE_PUBLIC_SITE", True),
        "pms": env_flag("ENABLE_PMS", True),
        "crm": env_flag("ENABLE_CRM", True),
        "staff": env_flag("ENABLE_STAFF", True),
        "guest_os": env_flag("ENABLE_GUEST_OS", True),
        "kitchen": env_flag("ENABLE_KITCHEN", True),
        "automation": env_flag("ENABLE_AUTOMATION", True),
        "ai_sales": env_flag("ENABLE_AI_SALES", True),
        # Financial/provider features are fail-closed. They require an explicit
        # future rollout flag in addition to any provider credentials.
        "payment_operations": env_flag("ENABLE_PAYMENT_OPERATIONS", False),
        "service_point_qr": env_flag("ENABLE_SERVICE_POINT_QR", False),
        "mkassa": env_flag("ENABLE_MKASSA", False),
        "nfc_wallet": False,
    }


@router.get("/capabilities")
async def runtime_capabilities():
    values = capabilities()
    return {
        "profile": os.environ.get("LAUNCH_PROFILE", "FULL_NO_PAYMENTS"),
        "capabilities": values,
        "financial_integrations_enabled": bool(
            values["payment_operations"] or values["service_point_qr"] or values["mkassa"]
        ),
    }
