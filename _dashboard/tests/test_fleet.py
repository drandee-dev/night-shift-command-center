"""Tests for the fleet probe (runs on the box) and the puller (runs here). Nothing here touches the network.

Run from the vault root:  python -m unittest discover -s _dashboard/tests
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import fleet_pull  # noqa: E402

PROBE = pathlib.Path(fleet_pull.HERE) / "fleet_probe.py"


class Probe(unittest.TestCase):
    def test_reads_spend_and_jobs_read_only_and_survives_missing_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            db = sqlite3.connect(home / "spend.db")
            db.execute("CREATE TABLE calls (ts_utc TEXT, month TEXT, agent TEXT, usd REAL)")
            db.executemany("INSERT INTO calls VALUES (?,?,?,?)", [
                ("2026-10-30T01:00:00", "2026-10", "ephraim", 9.0), ("2026-11-02T01:00:00", "2026-11", "ephraim", 1.25),
                ("2026-11-03T01:00:00", "2026-11", "cassius", 0.5)])
            db.commit()
            db.close()
            (home / "scheduler_state.json").write_text(json.dumps({"ephraim-career": "2026-11-03T13:00:00+00:00"}))
            before = (home / "spend.db").stat().st_mtime_ns
            # a docker command that cannot exist; an empty PATH is not enough on Windows, which still searches its own folders
            env = {**os.environ, "FLEET_HOME": str(home), "FLEET_DOCKER": "docker-missing-for-test"}
            out = json.loads(subprocess.run([sys.executable, str(PROBE)], capture_output=True, text=True, env=env).stdout)
            self.assertEqual(out["spend"]["month"], "2026-11")
            self.assertEqual((out["spend"]["total_usd"], out["spend"]["by_agent"]), (1.75, {"cassius": 0.5, "ephraim": 1.25}))
            self.assertEqual(out["jobs"], {"ephraim-career": "2026-11-03T13:00:00+00:00"})
            self.assertIn("containers_error", out)
            self.assertEqual((home / "spend.db").stat().st_mtime_ns, before)  # read-only: file untouched

    def test_missing_files_are_reported_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "FLEET_HOME": tmp, "FLEET_DOCKER": "docker-missing-for-test"}
            out = json.loads(subprocess.run([sys.executable, str(PROBE)], capture_output=True, text=True, env=env).stdout)
            self.assertIsNone(out["spend"])
            self.assertIn("spend_error", out)
            self.assertIn("jobs_error", out)


class Pull(unittest.TestCase):
    def test_success_then_failure_keeps_last_good_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "state" / "fleet.json"
            good = mock.Mock(returncode=0, stdout=json.dumps({"spend": {"total_usd": 3.0}}), stderr="")
            with mock.patch("fleet_pull.subprocess.run", return_value=good):
                self.assertTrue(fleet_pull.pull(out, ["ssh"]))
            first = json.loads(out.read_text())
            self.assertEqual((first["ok"], first["data"]["spend"]["total_usd"]), (True, 3.0))
            bad = mock.Mock(returncode=255, stdout="", stderr="Permission denied (publickey)")
            with mock.patch("fleet_pull.subprocess.run", return_value=bad):
                self.assertFalse(fleet_pull.pull(out, ["ssh"]))
            second = json.loads(out.read_text())
            self.assertFalse(second["ok"])
            self.assertIn("Permission denied", second["error"])
            self.assertEqual(second["data"], first["data"])  # last good data kept
            self.assertEqual(second["last_ok"], first["pulled_at"])

    def test_command_is_the_fixed_read_only_ssh(self):
        env = {"NIGHT_SHIFT_FLEET_HOST": "user@box.example", "NIGHT_SHIFT_FLEET_KEY": "k.key"}
        cmd = fleet_pull.ssh_cmd(env, pathlib.Path("missing.json"))
        self.assertEqual(cmd[0], "ssh")
        self.assertIn("BatchMode=yes", cmd)
        self.assertEqual(cmd[-4:], ["--", "user@box.example", "python3", "-"])  # options end before the host; probe from stdin

    def test_host_and_key_come_from_config_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = pathlib.Path(tmp) / "fleet-ssh.json"
            with self.assertRaises(ValueError):
                fleet_pull.ssh_cmd({}, cfg)  # nothing configured
            cfg.write_text(json.dumps({"host": "user@box.example", "key": "k.key"}))
            self.assertIn("user@box.example", fleet_pull.ssh_cmd({}, cfg))
            for bad in ("-oProxyCommand=x", "-F@x", "user@-oProxy", "box.example", "user@box example", "user@box;rm"):
                with self.assertRaises(ValueError, msg=bad):
                    fleet_pull.ssh_cmd({"NIGHT_SHIFT_FLEET_HOST": bad, "NIGHT_SHIFT_FLEET_KEY": "k"}, cfg)
            with tempfile.TemporaryDirectory() as t2:  # unconfigured pull records the error, never runs ssh
                out = pathlib.Path(t2) / "fleet.json"
                with mock.patch("fleet_pull.CONFIG", pathlib.Path(t2) / "none.json"), mock.patch.dict("os.environ", {}, clear=True), \
                        mock.patch("fleet_pull.subprocess.run") as run:
                    self.assertFalse(fleet_pull.pull(out))
                    run.assert_not_called()
                self.assertIn("not configured", json.loads(out.read_text())["error"])


if __name__ == "__main__":
    unittest.main()
