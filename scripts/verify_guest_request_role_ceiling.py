#!/usr/bin/env python3
"""Guest OS role/service-code ceiling regression with no database or provider calls."""
import asyncio
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from fastapi import HTTPException
from app.staff_guest_requests import guest_request_codes, load_routed_task_for_update


def identity(role, modules, custom=True):
    return {"role": role, "module_permissions": modules, "module_permissions_custom": custom}


class StubConn:
    def __init__(self, code):
        self.code = code

    async def fetchrow(self, *_args):
        return {"id": uuid.uuid4(), "serviceCode": self.code, "status": "OPEN",
                "assignedToId": None, "stayId": None, "source": "GUEST_OS_" + self.code}


async def assert_routed(role, modules, code, expected):
    try:
        await load_routed_task_for_update(StubConn(code), uuid.uuid4(), uuid.uuid4(), identity(role, modules))
    except HTTPException as exc:
        assert not expected and exc.status_code == 403, (role, code, exc.status_code)
    else:
        assert expected, (role, code, "unexpected access")


async def main():
    assert guest_request_codes(identity("MAID", ["OPS"])) == {"HOUSEKEEPING", "TOWELS", "LINEN"}
    assert guest_request_codes(identity("TECHNICIAN", ["OPS"])) == {"MAINTENANCE"}
    assert guest_request_codes(identity("MAID", ["FINANCE"])) == set()
    assert guest_request_codes(identity("STORE_STAFF", ["OPS", "SERVICES"])) == set()
    assert guest_request_codes(identity("CONTENT_MANAGER", ["OPS"])) == set()
    assert guest_request_codes(identity("COOK", ["DINING", "OPS"])) == {"MEALS"}
    assert guest_request_codes(identity("OWNER", ["OPS"])) == {"*"}
    await assert_routed("MAID", ["OPS"], "ADMIN", False)
    await assert_routed("MAID", ["OPS"], "MAINTENANCE", False)
    await assert_routed("MAID", ["OPS"], "TOWELS", True)
    await assert_routed("TECHNICIAN", ["OPS"], "TOWELS", False)
    await assert_routed("TECHNICIAN", ["OPS"], "MAINTENANCE", True)
    await assert_routed("COOK", ["DINING", "OPS"], "ADMIN", False)
    await assert_routed("STORE_STAFF", ["OPS", "SERVICES"], "ADMIN", False)
    await assert_routed("OWNER", ["OPS"], "ADMIN", True)
    await assert_routed("MANAGER", ["OPS"], "MAINTENANCE", True)
    print("PASS: guest request role ceiling holds on list and mutations")


if __name__ == "__main__":
    asyncio.run(main())
