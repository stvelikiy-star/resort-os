import io

import segno
from fastapi import APIRouter, Depends, Query, Response

from .auth import require_roles

router = APIRouter(tags=["my-stay"])
manager_access = require_roles("OWNER", "ADMIN", "MANAGER", "RECEPTION")


@router.get("/api/v1/admin/my-stay/qr.svg")
async def render_my_stay_qr(
    value: str = Query(min_length=10, max_length=600),
    _user=Depends(manager_access),
):
    """Render a QR inside the authenticated PMS; no third-party QR service is used."""
    qr = segno.make(value, error="m")
    output = io.BytesIO()
    qr.save(output, kind="svg", scale=5, border=3, dark="#111111", light="#ffffff")
    return Response(
        output.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff"},
    )
