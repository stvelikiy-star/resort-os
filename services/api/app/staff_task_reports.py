import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .auth import current_user

router = APIRouter(prefix="/api/v1/ops", tags=["staff-task-reports"])


class ChecklistItem(BaseModel):
    code: str = Field(min_length=2, max_length=60)
    label: str = Field(min_length=2, max_length=160)
    done: bool


class TaskCompletionReport(BaseModel):
    summary: str = Field(min_length=2, max_length=2000)
    checklist: list[ChecklistItem] = Field(default_factory=list, max_length=20)
    evidence_urls: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_evidence(self):
        clean_urls: list[str] = []
        for value in self.evidence_urls:
            item = value.strip()
            if not item:
                continue
            if len(item) > 1000:
                raise ValueError("evidence URL is too long")
            if not (item.startswith("https://") or item.startswith("http://")):
                raise ValueError("evidence URLs must use http/https")
            clean_urls.append(item)
        self.evidence_urls = clean_urls
        return self


async def _property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval("SELECT id FROM properties WHERE code=$1", property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


@router.post("/tasks/{task_id}/complete-report")
async def complete_task_with_report(
    task_id: uuid.UUID,
    payload: TaskCompletionReport,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    role = user["role"]
    if role not in {"MAID", "TECHNICIAN"}:
        raise HTTPException(status_code=403, detail="Completion reports are for line staff")

    expected_type: Literal["HOUSEKEEPING", "MAINTENANCE"] = "HOUSEKEEPING" if role == "MAID" else "MAINTENANCE"
    actor_id = uuid.UUID(user["id"])

    if expected_type == "HOUSEKEEPING":
        if not payload.checklist:
            raise HTTPException(status_code=422, detail="Housekeeping completion requires a checklist")
        incomplete = [item.code for item in payload.checklist if not item.done]
        if incomplete:
            raise HTTPException(status_code=422, detail={"code": "CHECKLIST_INCOMPLETE", "items": incomplete})

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await _property_id(conn, user["property_code"])
            task = await conn.fetchrow(
                '''
                SELECT t.id,t.type::text AS type,t.status::text AS status,t."roomId",t."assignedToId",t.source,
                       room.code AS room_code
                FROM operational_tasks t
                LEFT JOIN rooms room ON room.id=t."roomId"
                WHERE t.id=$1 AND t."propertyId"=$2
                FOR UPDATE OF t
                ''',
                task_id,
                pid,
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if task["type"] != expected_type:
                raise HTTPException(status_code=403, detail="Task type not allowed for role")
            if task["assignedToId"] != actor_id:
                raise HTTPException(status_code=403, detail="Task must be assigned to current employee")
            if task["status"] != "IN_PROGRESS":
                raise HTTPException(status_code=409, detail={"code": "TASK_NOT_IN_PROGRESS", "status": task["status"]})

            current_room_state = None
            if task["roomId"]:
                current_room_state = await conn.fetchval(
                    '''SELECT "operationalState"::text FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                    task["roomId"],
                    pid,
                )
                if current_room_state is None:
                    raise HTTPException(status_code=409, detail="Task room no longer exists")

            report_json = {
                "summary": payload.summary.strip(),
                "checklist": [item.model_dump() for item in payload.checklist],
                "evidence_urls": payload.evidence_urls,
                "room_code": task["room_code"],
            }

            housekeeping_task_id = None
            remaining_maintenance_tasks = 0
            resulting_room_state = current_room_state
            in_stay_request = task["source"] == "GUEST_PORTAL_IN_STAY"

            # In-stay service requests are fulfilment inside an occupied room. They are
            # not turnover/readiness events and must not mutate the PMS room state.
            if in_stay_request:
                next_status = "DONE"
                await conn.execute(
                    '''UPDATE operational_tasks SET status='DONE',"completedAt"=now(),"updatedAt"=now() WHERE id=$1''',
                    task_id,
                )
            elif expected_type == "HOUSEKEEPING":
                next_status = "IN_INSPECTION"
                await conn.execute(
                    '''UPDATE operational_tasks SET status='IN_INSPECTION',"updatedAt"=now() WHERE id=$1''',
                    task_id,
                )
                if task["roomId"] and current_room_state != "TECH_BLOCK":
                    await conn.execute(
                        '''UPDATE rooms SET "operationalState"='IN_INSPECTION',"updatedAt"=now() WHERE id=$1''',
                        task["roomId"],
                    )
                    resulting_room_state = "IN_INSPECTION"
                elif task["roomId"]:
                    resulting_room_state = "TECH_BLOCK"
            else:
                next_status = "DONE"
                await conn.execute(
                    '''UPDATE operational_tasks SET status='DONE',"completedAt"=now(),"updatedAt"=now() WHERE id=$1''',
                    task_id,
                )
                if task["roomId"]:
                    remaining_maintenance_tasks = int(
                        await conn.fetchval(
                            '''
                            SELECT count(*)::int FROM operational_tasks
                            WHERE "propertyId"=$1 AND "roomId"=$2 AND type='MAINTENANCE'
                              AND id<>$3 AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                            ''',
                            pid,
                            task["roomId"],
                            task_id,
                        )
                        or 0
                    )
                    if remaining_maintenance_tasks > 0:
                        await conn.execute(
                            '''UPDATE rooms SET "operationalState"='TECH_BLOCK',"updatedAt"=now() WHERE id=$1''',
                            task["roomId"],
                        )
                        resulting_room_state = "TECH_BLOCK"
                    else:
                        await conn.execute(
                            '''UPDATE rooms SET "operationalState"='DIRTY',"updatedAt"=now() WHERE id=$1''',
                            task["roomId"],
                        )
                        resulting_room_state = "DIRTY"
                        existing_housekeeping = await conn.fetchval(
                            '''
                            SELECT id FROM operational_tasks
                            WHERE "roomId"=$1 AND type='HOUSEKEEPING'
                              AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                            ORDER BY "createdAt" DESC LIMIT 1
                            ''',
                            task["roomId"],
                        )
                        if existing_housekeeping:
                            housekeeping_task_id = existing_housekeeping
                        else:
                            housekeeping_task_id = uuid.uuid4()
                            await conn.execute(
                                '''
                                INSERT INTO operational_tasks (
                                  id,"propertyId","roomId",type,status,priority,title,description,
                                  "createdByType","createdById",source,"createdAt","updatedAt"
                                ) VALUES ($1,$2,$3,'HOUSEKEEPING','OPEN','HIGH',$4,$5,'SYSTEM',$6,'MAINTENANCE_COMPLETE',now(),now())
                                ''',
                                housekeeping_task_id,
                                pid,
                                task["roomId"],
                                f"Уборка после ремонта · {task['room_code'] or 'номер'}",
                                f"Создано после завершения ремонта {task_id}",
                                str(actor_id),
                            )

            audit_after = {
                "from_status": "IN_PROGRESS",
                "status": next_status,
                "room_state": resulting_room_state,
                "in_stay_service": in_stay_request,
                "report": report_json,
                "remaining_maintenance_tasks": remaining_maintenance_tasks,
                "housekeeping_task_id": str(housekeeping_task_id) if housekeeping_task_id else None,
            }
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
                  "afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'COMPLETE_WITH_REPORT','OperationalTask',$4,'STAFF_PWA','SUCCESS',$5::jsonb,now())
                ''',
                uuid.uuid4(), pid, str(actor_id), str(task_id), json.dumps(audit_after, ensure_ascii=False),
            )

    return {
        "ok": True,
        "task_id": str(task_id),
        "status": next_status,
        "room_code": task["room_code"],
        "room_state": resulting_room_state,
        "remaining_maintenance_tasks": remaining_maintenance_tasks,
        "housekeeping_task_id": str(housekeeping_task_id) if housekeeping_task_id else None,
        "report_recorded": True,
    }
