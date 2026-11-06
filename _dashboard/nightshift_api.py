"""Night Shift's HTTP routes: the action endpoint and the live-state API the dashboard note polls.

Shared by app.py (the full vault dashboard on 8790) and night_shift_server.py (Night Shift alone).

Security model: the server binds 127.0.0.1 only. Every route checks the Host header (blocks DNS rebinding) and needs
the X-Night-Shift header set to a token the server makes at startup and writes to a file only this account can read
(TOKEN_FILE). The token keeps out other accounts and sandboxed programs on this PC; the custom header also forces a CORS
preflight that fails because no CORS headers are ever sent, so a web page in a browser cannot call it. A click sends an
action id from a fixed allowlist (actions.py) and at most one short typed string, which actions.Runner.start validates.
"""

from __future__ import annotations

import os
import pathlib
import secrets
import subprocess
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import actions
import nightshift

ACTION_HEADER = "x-night-shift"
TOKEN_FILE = pathlib.Path.home() / ".second-brain" / "night-shift-token"  # the dashboard note reads the same path


def new_token(path: pathlib.Path = TOKEN_FILE) -> str:
    """Make a fresh token and write it to a file only this account can read. Raises if the file cannot be locked."""
    token = secrets.token_urlsafe(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)  # a fresh file, so no explicit entry an older copy carried survives the lock below
    path.touch(mode=0o600)  # locked while still empty, so the token is never in a file others can read
    if sys.platform == "win32":
        # drop inherited access (the profile grants groups such as Administrators and sandbox users) and keep only this account
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{os.environ['USERNAME']}:F"],
                       check=True, capture_output=True, timeout=30)
    else:
        path.chmod(0o600)
    path.write_text(token, encoding="ascii")  # truncating keeps the ACL
    return token


def guard(request: Request, token: str) -> JSONResponse | None:
    # Host check blocks DNS rebinding; the token header keeps out other local programs and, being a custom header,
    # makes a browser preflight a cross-origin call, which fails because this server sends no CORS headers.
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in ("127.0.0.1", "localhost"):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if not secrets.compare_digest((request.headers.get(ACTION_HEADER) or "").encode(), token.encode()):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return None


def register(app: FastAPI, runner: actions.Runner, token: str) -> None:
    if not token:
        raise ValueError("a token is required")  # an empty token would let an empty header through

    @app.post("/actions/{action_id}")
    async def action_start(action_id: str, request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        text = None
        if await request.body():  # only text actions take a body: {"text": "..."}; runner.start validates it
            try:
                text = (await request.json()).get("text")
            except (ValueError, AttributeError):
                return JSONResponse({"id": action_id, "result": "bad"}, status_code=422)
        result = runner.start(action_id, text)
        code = {"started": 202, "busy": 409, "unknown": 404, "bad": 422}[result]
        return JSONResponse({"id": action_id, "result": result}, status_code=code)

    @app.get("/actions/{action_id}")
    def action_state(action_id: str, request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        if action_id not in runner.actions:
            return JSONResponse({"error": "unknown"}, status_code=404)
        return JSONResponse(runner.state(action_id))

    @app.get("/api/night-shift")
    def api_night_shift(request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        return JSONResponse(nightshift.live(runner))

    @app.get("/api/night-shift/schedules")
    def api_night_shift_schedules(request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        return JSONResponse(nightshift.schedules_view())

    @app.get("/api/night-shift/fleet")
    def api_night_shift_fleet(request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        return JSONResponse(nightshift.fleet())

    @app.get("/api/night-shift/dusty")
    def api_night_shift_dusty(request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        return JSONResponse(nightshift.dusty_cached())

    @app.get("/api/night-shift/log/{name}")
    def api_night_shift_log(name: str, request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        text = nightshift.log_tail(name)
        if text is None:
            return JSONResponse({"error": "unknown"}, status_code=404)
        return JSONResponse({"name": name, "text": text})

    @app.get("/api/night-shift/usage")
    def api_night_shift_usage(request: Request):
        if (denied := guard(request, token)) is not None:
            return denied
        return JSONResponse(nightshift.usage_today())
