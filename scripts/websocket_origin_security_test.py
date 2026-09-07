#!/usr/bin/env python3
from __future__ import annotations

import os

os.environ["WS_ENFORCE_SAME_ORIGIN"] = "true"

from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from app.websocket_security import require_websocket_same_origin

app = FastAPI()


@app.websocket("/ws")
async def guarded(websocket: WebSocket):
    if not await require_websocket_same_origin(websocket):
        return
    await websocket.accept()
    await websocket.send_text("origin-ok")
    await websocket.close()


def expect_allowed(client: TestClient, headers: dict[str, str]) -> None:
    with client.websocket_connect("/ws", headers=headers) as ws:
        assert ws.receive_text() == "origin-ok"


def expect_rejected(client: TestClient, headers: dict[str, str]) -> None:
    try:
        with client.websocket_connect("/ws", headers=headers):
            raise AssertionError("websocket origin unexpectedly accepted")
    except Exception as exc:
        if isinstance(exc, AssertionError):
            raise


def main() -> None:
    with TestClient(app) as client:
        expect_allowed(client, {"Origin": "http://testserver", "Host": "testserver"})
        expect_allowed(
            client,
            {
                "Origin": "https://admin.3korony.test",
                "Host": "admin.3korony.test",
                "X-Forwarded-Proto": "https",
            },
        )
        expect_rejected(client, {"Origin": "https://evil.example", "Host": "admin.3korony.test", "X-Forwarded-Proto": "https"})
        expect_rejected(client, {"Host": "admin.3korony.test", "X-Forwarded-Proto": "https"})
        expect_rejected(client, {"Origin": "https://admin.3korony.test/path", "Host": "admin.3korony.test", "X-Forwarded-Proto": "https"})
    print("WEBSOCKET_ORIGIN_SECURITY_PASS")


if __name__ == "__main__":
    main()
