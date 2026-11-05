"""Pull the fleet's status from the Oracle box into ~/.second-brain/state/fleet.json.

    python _dashboard/fleet_pull.py            # one pull; run by the dish drawer's button, never on a timer (pins.md)

One fixed read-only ssh command: it feeds fleet_probe.py to `python3 -` on the box. Nothing on the box changes and
no argument comes from a caller. BatchMode means a missing key or a changed host key fails instead of prompting.
On failure the file keeps the last good data and records the error, so the panel can say "stale since ...".
Decided 2026-11-04 (projects/night-shift-control-room.md, decision 3: pull, not tunnel; read-only, no box change).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path.home() / ".second-brain" / "state" / "fleet.json"
# The box's address and key live outside the code: env vars, else ~/.second-brain/fleet-ssh.json {"host": "user@addr", "key": "path"}
CONFIG = pathlib.Path.home() / ".second-brain" / "fleet-ssh.json"
# user@host and nothing else, starting with a letter or digit so it can never read as an ssh option (and "--" ends options anyway)
HOST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.-]*")


def ssh_cmd(env: dict | None = None, config: pathlib.Path | None = None) -> list[str]:
    """The fixed read-only ssh command. Raises ValueError when the host or key is not configured or not well formed."""
    env = os.environ if env is None else env
    config = CONFIG if config is None else config
    try:
        cfg = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    host = env.get("NIGHT_SHIFT_FLEET_HOST") or cfg.get("host") or ""
    key = env.get("NIGHT_SHIFT_FLEET_KEY") or cfg.get("key") or ""
    if not HOST_RE.fullmatch(host) or not key:
        raise ValueError(f"fleet host or key not configured: set NIGHT_SHIFT_FLEET_HOST and NIGHT_SHIFT_FLEET_KEY, or {config.name}")
    return ["ssh", "-i", key, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "--", host, "python3", "-"]


def pull(out: pathlib.Path = OUT, cmd: list[str] | None = None) -> bool:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        old = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    try:
        cmd = cmd or ssh_cmd()
        run = subprocess.run(cmd, input=(HERE / "fleet_probe.py").read_text(encoding="utf-8"), capture_output=True,
                             text=True, timeout=60)
        if run.returncode != 0:
            raise RuntimeError(f"ssh exit {run.returncode}: {run.stderr.strip()[-200:]}")
        data = json.loads(run.stdout)
        result = {"ok": True, "pulled_at": now, "data": data}
    except Exception as exc:  # noqa: BLE001 - any failure is recorded, last good data kept
        result = {"ok": False, "pulled_at": now, "error": str(exc)[:300], "data": old.get("data"),
                  "last_ok": old.get("pulled_at") if old.get("ok") else old.get("last_ok")}
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(result), encoding="utf-8")
    tmp.replace(out)
    return result["ok"]


if __name__ == "__main__":
    sys.exit(0 if pull() else 1)
