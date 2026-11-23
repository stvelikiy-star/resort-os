#!/usr/bin/env python3
"""Isolated MARINA_FINAL_QA session revocation and forbidden-role API probe.

No business writes, no Production, no passwords or cookies in output.
"""
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request

ORIGIN = "https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core"
ROLES = ("OWNER", "RECEPTION", "COOK", "WAITER", "STORE_STAFF")


def request(opener, path, *, payload=None, method=None, replay_cookie=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if replay_cookie is not None:
        headers["Cookie"] = "resort_session=" + replay_cookie
    req = urllib.request.Request(ORIGIN + path, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=25) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def must(code, expected, check):
    if code != expected:
        raise RuntimeError(f"{check}: expected HTTP {expected}, received HTTP {code}")


def main():
    if os.environ.get("MARINA_QA_ORIGIN") != ORIGIN:
        raise RuntimeError("QA_ORIGIN_BLOCK")
    users = json.loads(os.environ["MARINA_NATIVE_QA_USERS_JSON"])
    if not isinstance(users, dict) or set(users) != set(ROLES):
        raise RuntimeError("QA_SECRET_ROLE_SET_BLOCK")
    for role in ROLES:
        u = users[role]
        if not isinstance(u, dict) or set(u) != {"username", "password"}:
            raise RuntimeError("QA_SECRET_STRUCTURE_BLOCK")
        if not re.fullmatch(r"marina_nativeqa_[A-Za-z0-9_-]{9,70}", u["username"]):
            raise RuntimeError("QA_USERNAME_BLOCK")
        if not isinstance(u["password"], str) or len(u["password"]) < 22:
            raise RuntimeError("QA_SECRET_LENGTH_BLOCK")

    opener = urllib.request.build_opener()
    code, body = request(opener, "/api/v1/auth/mode")
    must(code, 200, "auth-mode")
    if json.loads(body).get("mode") != "single_property":
        raise RuntimeError("QA_AUTH_MODE_BLOCK")
    code, body = request(opener, "/health/ready")
    must(code, 200, "readiness")
    if json.loads(body).get("property") != "MARINA_FINAL_QA":
        raise RuntimeError("QA_PROPERTY_BLOCK")

    for role in ROLES:
        jar = http.cookiejar.CookieJar()
        session = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        code, raw = request(session, "/api/v1/auth/login", payload=users[role])
        must(code, 200, f"{role} login")
        signed = json.loads(raw)
        if signed.get("role") != role:
            raise RuntimeError(f"{role} identity role mismatch")
        code, raw = request(session, "/api/v1/auth/me")
        must(code, 200, f"{role} me")
        verified = json.loads(raw)
        if (verified.get("id"), verified.get("property_code"), verified.get("role")) != (
            signed.get("id"), signed.get("property_code"), role
        ):
            raise RuntimeError(f"{role} verified identity mismatch")
        print(f"QA_{role}_LOGIN_ME_PASS", flush=True)
        # Retain the pre-logout token in process memory only. A fresh client
        # must be rejected even if it replays the cookie after server logout.
        old_tokens = [cookie.value for cookie in jar if cookie.name == "resort_session"]
        if len(old_tokens) != 1:
            raise RuntimeError(f"{role} session cookie was not issued")
        old_token = old_tokens[0]
        if role != "OWNER":
            code, _ = request(session, "/api/v1/admin/dashboard")
            must(code, 403, f"{role} forbidden owner dashboard")
            print(f"QA_{role}_OWNER_DASHBOARD_403_PASS", flush=True)
        code, _ = request(session, "/api/v1/auth/logout", method="POST")
        must(code, 204, f"{role} logout")
        code, _ = request(session, "/api/v1/auth/me")
        must(code, 401, f"{role} locally signed-out session")
        replay_client = urllib.request.build_opener()
        code, _ = request(replay_client, "/api/v1/auth/me", replay_cookie=old_token)
        must(code, 401, f"{role} rejected replay of revoked cookie")
        del old_token, old_tokens
        print(f"QA_{role}_LOGOUT_REVOKED_REPLAY_401_PASS", flush=True)

    print("MARINA_QA_FIVE_ROLE_SERVER_SESSION_RBAC_PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("MARINA_QA_AUTH_CONTRACT_FAIL: " + str(exc), file=sys.stderr)
        sys.exit(1)
