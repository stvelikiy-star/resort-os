"""Isolated P0 regression: foreign-hotel QR must fail before DB writes.

Run: python3 scripts/verify_marina_qr_origin_guard.py
No database, network, third-party packages or production services required.
"""
import ast
import asyncio
import os
import pathlib
import secrets
import uuid
from unittest.mock import patch
from typing import Any
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


def load_function(path, name, namespace):
    source = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    matches = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    assert len(matches) == 1, (path, name)
    module = ast.fix_missing_locations(ast.Module(body=matches, type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[name]


class FakeConn:
    def __init__(self):
        self.writes = 0

    async def fetchrow(self, query, *args):
        return {"id": uuid.uuid4(), "code": "POOL", "name": "Pool", "isActive": True}

    async def fetchval(self, query, *args):
        return None

    async def execute(self, query, *args):
        self.writes += 1


def guest_test():
    ns = {
        "os": os, "urlsplit": urlsplit, "HTTPException": HTTPException,
        "MARINA_SHARED_AUTH_PREVIEW_ENABLED": False,
        "PROPERTY_CODE": "ALPHA",
        "PUBLIC_BASE_URL": "https://3korony.com",
    }
    origin = load_function("services/api/app/guest_os.py", "guest_qr_public_origin", ns)
    with patch.dict(os.environ, {}, clear=True):
        try:
            origin()
            raise AssertionError("foreign hotel inherited legacy guest QR URL")
        except HTTPException as exc:
            assert exc.status_code == 503
    with patch.dict(os.environ, {"GUEST_OS_PUBLIC_BASE_URL": "https://alpha.example"}, clear=True):
        ns["PUBLIC_BASE_URL"] = "https://alpha.example"
        assert origin() == "https://alpha.example"
    ns["PROPERTY_CODE"] = "THREE_CROWNS"
    with patch.dict(os.environ, {}, clear=True):
        ns["PUBLIC_BASE_URL"] = "https://3korony.com"
        assert origin() == "https://3korony.com"


async def service_point_test():
    ns = {
        "os": os, "uuid": uuid, "secrets": secrets, "Any": Any,
        "HTTPException": HTTPException, "PROPERTY_CODE": "ALPHA",
        "PUBLIC_BASE_URL": "https://3korony.com",
        "hash_secret": lambda token: "fakehash",
        "qr_svg": lambda url: "<svg/>",
    }
    issue = load_function("services/api/app/service_points.py", "issue_qr", ns)
    with patch.dict(os.environ, {}, clear=True):
        db = FakeConn()
        try:
            await issue(db, pid=uuid.uuid4(), point_id=uuid.uuid4())
            raise AssertionError("foreign service point QR issued without origin")
        except HTTPException as exc:
            assert exc.status_code == 503
            assert db.writes == 0, "rejected QR must not touch database"
    with patch.dict(os.environ, {"SERVICE_POINT_PUBLIC_BASE_URL": "https://alpha.example"}, clear=True):
        ns["PUBLIC_BASE_URL"] = "https://alpha.example"
        db = FakeConn()
        value = await issue(db, pid=uuid.uuid4(), point_id=uuid.uuid4())
        assert value["public_url"].startswith("https://alpha.example/p/")
        assert db.writes == 1
    ns["PROPERTY_CODE"] = "THREE_CROWNS"
    ns["PUBLIC_BASE_URL"] = "https://3korony.com"
    with patch.dict(os.environ, {}, clear=True):
        db = FakeConn()
        value = await issue(db, pid=uuid.uuid4(), point_id=uuid.uuid4())
        assert value["public_url"].startswith("https://3korony.com/p/")


if __name__ == "__main__":
    guest_test()
    asyncio.run(service_point_test())
    print("PASS: foreign guest/service QR fail closed; no premature database write; legacy safe")
