"""Runs ON THE BOX, fed over ssh stdin by fleet_pull.py: `ssh box python3 - < fleet_probe.py`.

Read-only and stdlib only. It opens the fleet's spend store with mode=ro, reads the scheduler's state file and asks
docker for the fleet-* containers (stopped ones too, so a dead one shows as Exited), then prints one JSON object. It writes nothing on the box and sends nothing anywhere.
FLEET_HOME overrides ~/.fleet (the tests use that).
"""

import datetime as dt
import json
import os
import sqlite3
import subprocess

home = os.environ.get("FLEET_HOME") or os.path.expanduser("~/.fleet")
out = {"probed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "spend": None, "jobs": None, "containers": None}

try:
    db = sqlite3.connect(f"file:{home}/spend.db?mode=ro", uri=True, timeout=5)
    month = db.execute("SELECT MAX(month) FROM calls").fetchone()[0]
    rows = db.execute("SELECT agent, ROUND(SUM(usd), 2) FROM calls WHERE month = ? GROUP BY agent", (month,)).fetchall()
    out["spend"] = {"month": month, "total_usd": round(sum(r[1] for r in rows), 2), "by_agent": dict(rows),
                    "last_call_utc": db.execute("SELECT MAX(ts_utc) FROM calls").fetchone()[0]}
    db.close()
except Exception as exc:  # noqa: BLE001 - report the failure in the output instead of dying
    out["spend_error"] = str(exc)[:200]

try:
    with open(f"{home}/scheduler_state.json", encoding="utf-8") as fh:
        out["jobs"] = json.load(fh)  # job name -> ISO time of its last handled fire
except Exception as exc:  # noqa: BLE001
    out["jobs_error"] = str(exc)[:200]

try:
    ps = subprocess.run(["docker", "ps", "-a", "--filter", "name=fleet-", "--format", "{{.Names}}\t{{.Status}}"], capture_output=True, text=True, timeout=15)
    out["containers"] = dict(line.split("\t", 1) for line in ps.stdout.splitlines() if "\t" in line)
except Exception as exc:  # noqa: BLE001
    out["containers_error"] = str(exc)[:200]

print(json.dumps(out))
