"""Night Shift's HTTP routes: the action endpoint and the live-state API the dashboard note polls.

Shared by app.py (the full vault dashboard on 8790) and night_shift_server.py (Night Shift alone).

Security model: the server binds 127.0.0.1 only and has no auth. Every route checks the Host header (blocks DNS
rebinding); POST also needs the X-Night-Shift header, which forces a CORS preflight that fails because no CORS headers
are ever sent, so a web page in a browser cannot start an action. A click sends an action id from a fixed allowlist
(actions.py) and at most one short typed string, which actions.Runner.start validates.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import actions
import nightshift

ACTION_HEADER = "x-night-shift"


def guard(request: Request, need_header: bool) -> JSONResponse | None:
    # Host check blocks DNS rebinding; the custom header makes a browser preflight a
    # cross-origin POST, and this server sends no CORS headers, so the preflight fails.
    host = (request.headers.get("host") or "").rsplit(":", 1)[0]
    if host not in ("127.0.0.1", "localhost"):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if need_header and request.headers.get(ACTION_HEADER) != "1":
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return None


def register(app: FastAPI, runner: actions.Runner) -> None:
    @app.post("/actions/{action_id}")
    async def action_start(action_id: str, request: Request):
        if (denied := guard(request, True)) is not None:
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
        if (denied := guard(request, False)) is not None:
            return denied
        if action_id not in runner.actions:
            return JSONResponse({"error": "unknown"}, status_code=404)
        return JSONResponse(runner.state(action_id))

    @app.get("/api/night-shift")
    def api_night_shift(request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        return JSONResponse(nightshift.live(runner))

    @app.get("/api/night-shift/schedules")
    def api_night_shift_schedules(request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        return JSONResponse(nightshift.schedules_cached())

    @app.get("/api/night-shift/fleet")
    def api_night_shift_fleet(request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        return JSONResponse(nightshift.fleet())

    @app.get("/api/night-shift/dusty")
    def api_night_shift_dusty(request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        return JSONResponse(nightshift.dusty_cached())

    @app.get("/api/night-shift/log/{name}")
    def api_night_shift_log(name: str, request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        text = nightshift.log_tail(name)
        if text is None:
            return JSONResponse({"error": "unknown"}, status_code=404)
        return JSONResponse({"name": name, "text": text})

    @app.get("/api/night-shift/usage")
    def api_night_shift_usage(request: Request):
        if (denied := guard(request, False)) is not None:
            return denied
        return JSONResponse(nightshift.usage_today())
