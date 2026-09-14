from typing import Any

from fastapi import APIRouter, Depends, Request

from .auth import require_roles


router = APIRouter(prefix="/api/v1/admin/agents-context", tags=["agents-context"])
access = require_roles("OWNER", "MANAGER", "RECEPTION")


@router.get("/reservations")
async def reservation_agent_context(request: Request, user: dict[str, Any] = Depends(access)):
    async with request.app.state.db.acquire() as conn:
        property_id = await conn.fetchval('SELECT id FROM properties WHERE code=$1', user["property_code"])
        agents = await conn.fetch(
            '''SELECT id,name,status FROM booking_agents WHERE "propertyId"=$1 ORDER BY status,name''',
            property_id,
        )
        mappings = await conn.fetch(
            '''
            SELECT r.id AS reservation_id,a.id AS agent_id,a.name AS agent_name
            FROM reservations r
            JOIN booking_agents a ON a.id=r."agentId"
            WHERE r."propertyId"=$1
            ''',
            property_id,
        )
    return {
        "agents": [{"id": str(row["id"]), "name": row["name"], "status": row["status"]} for row in agents],
        "reservations": [
            {"reservation_id": str(row["reservation_id"]), "agent_id": str(row["agent_id"]), "agent_name": row["agent_name"]}
            for row in mappings
        ],
    }
