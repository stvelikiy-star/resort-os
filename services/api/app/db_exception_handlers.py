from asyncpg.exceptions import ExclusionViolationError, UniqueViolationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def install_database_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UniqueViolationError)
    async def unique_violation_handler(_request: Request, exc: UniqueViolationError):
        constraint = getattr(exc, "constraint_name", None)
        if constraint == "active_room_operational_task_type_unique":
            detail = {
                "code": "ACTIVE_TASK_EXISTS",
                "message": "An active housekeeping or maintenance task already exists for this room. Reload the operational snapshot instead of creating a duplicate.",
                "constraint": constraint,
            }
        else:
            detail = {
                "code": "DB_UNIQUE_CONFLICT",
                "message": "The record conflicts with an existing unique value. The transaction was rolled back.",
                "constraint": constraint,
            }
        return JSONResponse(status_code=409, content={"detail": detail})

    @app.exception_handler(ExclusionViolationError)
    async def exclusion_violation_handler(_request: Request, exc: ExclusionViolationError):
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "ROOM_CONFLICT_RACE",
                    "message": "Room inventory changed before commit. The transaction was rolled back; reload the PMS grid and retry.",
                    "constraint": getattr(exc, "constraint_name", None),
                }
            },
        )
