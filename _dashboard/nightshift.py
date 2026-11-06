"""Live state for the Night Shift scene: what is running, what failed, who is working.

Polled by night-shift-dashboard.md every few seconds, so everything here is cheap
(a few small JSON reads). Usage scans every transcript (about 5 s), so it has its
own cached function and its own route.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import threading
import time

import actions
import usage
import vault

SESSIONS_DIR = actions.VAULT / ".claude" / "sessions"
ACTIVE_SECONDS = 300  # hooks do not record busy/idle yet; a session touched in the last 5 min counts as active
USAGE_TTL = 120


def _parse(ts: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def sessions(directory: pathlib.Path = SESSIONS_DIR, now: dt.datetime | None = None) -> list[dict]:
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for p in directory.glob("*.json"):
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        last = _parse(s.get("last"))
        if last is None:
            continue
        age = (now - last).total_seconds()
        out.append({"id": s.get("id", p.stem), "cwd": s.get("cwd", ""), "topic": s.get("topic", ""),
                    "last": s["last"], "active": age <= ACTIVE_SECONDS})
    return sorted(out, key=lambda s: s["last"], reverse=True)


def objects(runner: actions.Runner) -> dict[str, dict]:
    """One state per scene object, from its actions' last runs: running beats failed beats ok."""
    rank = {"running": 3, "failed": 2, "timeout": 2, "ok": 1}
    found: dict[str, dict] = {}
    for action_id, spec in runner.actions.items():
        obj = spec.get("object")
        st = runner.state(action_id)
        if not obj or st["status"] not in rank:
            continue
        cur = found.get(obj)
        state = "failed" if st["status"] == "timeout" else st["status"]
        # equal rank: the later finish wins, so a fresh "ok" is not hidden behind an older one
        if cur is None or rank[st["status"]] > rank[cur["state"]] or (
                rank[st["status"]] == rank[cur["state"]] and (st.get("finished") or "") > (cur["finished"] or "")):
            found[obj] = {"state": state, "finished": st.get("finished"), "action": action_id}
    return found


def live(runner: actions.Runner) -> dict:
    found = objects(runner)
    if any(not s["ok"] for s in schedules_cached()):
        found["mart"] = {"state": "failed", "finished": None, "action": "schedules"}
    return {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "sessions": sessions(), "objects": found}


# --- local Scheduled Tasks (the 24H Mart) ---------------------------------------------------------------------
# Task name -> log under ~/.second-brain/logs (None: no log of its own). The only names the log route will read.
SCHEDULE_LOGS = {"SecondBrain-Dashboard": "dashboard", "SecondBrain-LedgerRefresh": "ledger-refresh",
                 "SecondBrain-WeeklyReview": "weekly-review", "SecondBrain-Syncthing": None,
                 "SecondBrain-FleetPull": "fleet-pull"}
SCHEDULE_TTL = 60
# 0 success, 267009 running now, 267011 not run yet, 267014 stopped by the user; anything else is a failed last run.
# A task that is running now is fine whatever its last result (the dashboard task after a restart shows 1 or 267014).
SCHEDULE_FINE = {0, 267009, 267011, 267014}
_PS = ("Get-ScheduledTask -TaskName 'SecondBrain-*' | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; "
       "[pscustomobject]@{ name = $_.TaskName; state = [string]$_.State; "
       "last = if ($i.LastRunTime.Year -gt 2000) { $i.LastRunTime.ToString('s') } else { $null }; "
       "result = $i.LastTaskResult; "
       "next = if ($i.NextRunTime -and $i.NextRunTime.Year -gt 2000) { $i.NextRunTime.ToString('s') } else { $null } } } "
       "| ConvertTo-Json -Compress")


def schedules() -> list[dict]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", _PS], capture_output=True, text=True,
                         timeout=30, stdin=subprocess.DEVNULL).stdout.strip()
    rows = json.loads(out) if out else []
    rows = [rows] if isinstance(rows, dict) else rows  # one task serialises as an object, not a list
    for r in rows:
        r["ok"] = r["state"] == "Running" or r["result"] in SCHEDULE_FINE
        r["log"] = SCHEDULE_LOGS.get(r["name"])
    return sorted(rows, key=lambda r: r["name"])


_sched_cache: dict = {"at": 0.0, "data": [], "busy": False, "error": False}
_sched_lock = threading.Lock()


def schedules_cached() -> list[dict]:
    """Last known schedules, never blocking: a stale cache starts a background refresh (PowerShell takes ~1 s)."""
    with _sched_lock:
        stale = time.monotonic() - _sched_cache["at"] > SCHEDULE_TTL and not _sched_cache["busy"]
        if stale:
            _sched_cache["busy"] = True
    if stale:
        def refresh():
            try:
                data = schedules()
                with _sched_lock:
                    _sched_cache.update(data=data, at=time.monotonic(), error=False)
            except Exception as e:  # noqa: BLE001 - keep the last data; the next poll retries after the TTL
                print(f"schedules: could not read the Scheduled Tasks: {e!r}", file=sys.stderr)  # lands in dashboard.log
                with _sched_lock:
                    _sched_cache.update(at=time.monotonic(), error=True)
            finally:
                with _sched_lock:
                    _sched_cache["busy"] = False
        threading.Thread(target=refresh, daemon=True).start()
    return _sched_cache["data"]


def schedules_view() -> dict:
    """What the mart drawer shows: the rows, and whether the last read failed (so it never just says "No data yet")."""
    rows = schedules_cached()
    return {"rows": rows, "error": _sched_cache["error"]}


FLEET_FILE = actions.HOME / "state" / "fleet.json"
FLEET_CONFIG = actions.VAULT / "projects" / "agentic-fleet" / "fleet.yaml"


def fleet(path: pathlib.Path = FLEET_FILE, config: pathlib.Path = FLEET_CONFIG) -> dict:
    """The last fleet_pull.py result, plus the monthly cap from the fleet's own config."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"present": False}
    try:
        cap = float(re.search(r"^\s*monthly_cap_usd:\s*([\d.]+)", config.read_text(encoding="utf-8"), re.M).group(1))
    except (OSError, AttributeError, ValueError):
        cap = None
    return {"present": True, "cap_usd": cap, **data}


# check actions' own logs too, for the dashboard's "Read log" on a failed check; session logs only say a window opened
CHECK_LOGS = frozenset(k for k, a in actions.default_actions().items() if a["kind"] == "check")
TAIL_BYTES = 64 * 1024  # far more than 40 lines of any log here


def log_tail(name: str, lines: int = 40, logs_dir: pathlib.Path = actions.HOME / "logs") -> str | None:
    """Last lines of an allowed schedule or check-action log, or None for a name that is not on the list."""
    if name is None or (name not in SCHEDULE_LOGS.values() and name not in CHECK_LOGS):
        return None
    try:
        with open(logs_dir / f"{name}.log", "rb") as f:  # read only the end: the dashboard log grows for months
            size = f.seek(0, 2)
            f.seek(max(0, size - TAIL_BYTES))
            text = f.read().decode("utf-8", errors="replace").replace("\r\n", "\n")  # as read_text gave before
    except OSError:
        return ""
    kept = text.splitlines(keepends=True)
    if size > TAIL_BYTES:
        kept = kept[1:]  # the first line was cut part way
    return "".join(kept[-lines:])


DUSTY_DAYS = 30
DUSTY_TTL = 600  # the transcript scan takes seconds; skill use changes slowly
# the button rule: session-end skills need a session's history, so a fresh "try it" session cannot use them
SESSION_END = frozenset({"retro", "session-cleanup", "handoff"})


def dusty(skills: list[dict], by_skill: list[dict], today: dt.date, days: int = DUSTY_DAYS) -> list[dict]:
    """Loadable skills not used in `days` (never used first, then oldest), with their one-line brief."""
    last = {r["name"]: r["last_used"] for r in by_skill}
    cutoff = (today - dt.timedelta(days=days)).isoformat()
    rows = [{"name": s["name"], "brief": s["brief"], "last_used": last.get(s["name"], "")}
            for s in skills if last.get(s["name"], "") < cutoff and s["name"] not in SESSION_END]
    return sorted(rows, key=lambda r: (r["last_used"], r["name"]))


_dusty_cache: dict = {"at": float("-inf"), "data": None, "busy": False}
_dusty_lock = threading.Lock()


def dusty_cached() -> dict:
    """Never blocks: returns the last result (data None until the first scan ends) and refreshes it in the background."""
    with _dusty_lock:
        stale = time.monotonic() - _dusty_cache["at"] > DUSTY_TTL and not _dusty_cache["busy"]
        if stale:
            _dusty_cache["busy"] = True
    if stale:
        def refresh():
            try:
                data = dusty(vault.loadable_skills(), usage.agent_activity(days=DUSTY_DAYS)["by_skill"], dt.date.today())
                with _dusty_lock:
                    _dusty_cache.update(data=data, at=time.monotonic())
            except Exception:  # noqa: BLE001 - keep the last data; retry after the TTL
                with _dusty_lock:
                    _dusty_cache["at"] = time.monotonic()
            finally:
                with _dusty_lock:
                    _dusty_cache["busy"] = False
        threading.Thread(target=refresh, daemon=True).start()
    return {"days": DUSTY_DAYS, "skills": _dusty_cache["data"]}


_usage_cache: dict = {"at": 0.0, "data": None}
_usage_lock = threading.Lock()


def usage_today() -> dict:
    with _usage_lock:
        if _usage_cache["data"] is None or time.monotonic() - _usage_cache["at"] > USAGE_TTL:
            s = usage.summary(days=1)
            today = s["daily"][-1] if s["daily"] else {}
            _usage_cache["data"] = {
                "date": today.get("date"), "cost_usd": round(today.get("cost_usd", 0.0), 2),
                "turns": today.get("turns", 0), "unpriced_models": s["unpriced_models"],
            }
            _usage_cache["at"] = time.monotonic()
        return _usage_cache["data"]
