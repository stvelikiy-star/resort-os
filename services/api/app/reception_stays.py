import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from .auth import require_roles
from .stays import check_in as stay_check_in
from .stays import check_out as stay_check_out

router = APIRouter(prefix="/api/v1/admin/stays", tags=["reception-stays"])
reception_access = require_roles("OWNER", "ADMIN", "MANAGER", "RECEPTION")


@router.post("/reservations/{reservation_id}/check-in")
async def reception_check_in(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(reception_access),
):
    return await stay_check_in(reservation_id=reservation_id, request=request, user=user)


@router.post("/reservations/{reservation_id}/check-out")
async def reception_check_out(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(reception_access),
):
    return await stay_check_out(reservation_id=reservation_id, request=request, user=user)
