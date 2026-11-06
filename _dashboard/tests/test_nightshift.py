"""Tests for the Night Shift live-state readers.

Run from the vault root:  python -m unittest discover -s _dashboard/tests
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import actions  # noqa: E402
import nightshift  # noqa: E402

NOW = dt.datetime(2026, 11, 4, 15, 0, tzinfo=dt.timezone.utc)


class Sessions(unittest.TestCase):
    def test_active_by_recency_and_bad_files_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            (d / "a.json").write_text(json.dumps({"id": "a", "topic": "t", "last": "2026-11-04T14:58:00Z"}))
            (d / "b.json").write_text(json.dumps({"id": "b", "last": "2026-11-04T12:00:00Z"}))
            (d / "c.json").write_text("{not json")
            (d / "d.json").write_text(json.dumps({"id": "d"}))  # no timestamp
            out = nightshift.sessions(d, NOW)
        self.assertEqual([(s["id"], s["active"]) for s in out], [("a", True), ("b", False)])


class Objects(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runner = actions.Runner({
            "x1": {"argv": [], "cwd": ".", "kind": "check", "timeout": 1, "object": "projects"},
            "x2": {"argv": [], "cwd": ".", "kind": "check", "timeout": 1, "object": "projects"},
            "y": {"argv": [], "cwd": ".", "kind": "check", "timeout": 1, "object": "tooling"},
            "z": {"argv": [], "cwd": ".", "kind": "check", "timeout": 1},  # no scene object
        }, pathlib.Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_running_beats_failed_beats_ok_and_timeout_reads_as_failed(self):
        w = self.runner._write
        w("x1", {"id": "x1", "status": "ok", "finished": "t"})
        w("x2", {"id": "x2", "status": "timeout"})
        w("y", {"id": "y", "status": "ok", "finished": "t2"})
        w("z", {"id": "z", "status": "failed"})
        got = nightshift.objects(self.runner)
        self.assertEqual({k: v["state"] for k, v in got.items()}, {"projects": "failed", "tooling": "ok"})
        w("x1", {"id": "x1", "status": "running"})
        self.assertEqual(nightshift.objects(self.runner)["projects"]["state"], "running")

    def test_equal_rank_later_finish_wins(self):
        w = self.runner._write
        w("x1", {"id": "x1", "status": "ok", "finished": "2026-11-04T10:00:00+00:00"})
        w("x2", {"id": "x2", "status": "ok", "finished": "2026-11-04T11:00:00+00:00"})
        self.assertEqual(nightshift.objects(self.runner)["projects"]["action"], "x2")
        w("x1", {"id": "x1", "status": "ok", "finished": "2026-11-04T12:00:00+00:00"})
        self.assertEqual(nightshift.objects(self.runner)["projects"]["action"], "x1")

    def test_never_run_gives_no_entry(self):
        self.assertEqual(nightshift.objects(self.runner), {})


class Fleet(unittest.TestCase):
    def test_missing_file_and_cap_from_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            self.assertEqual(nightshift.fleet(d / "none.json", d / "fleet.yaml"), {"present": False})
            (d / "fleet.json").write_text(json.dumps({"ok": True, "data": {"spend": {"total_usd": 1.5}}}))
            (d / "fleet.yaml").write_text("budget:\n  monthly_cap_usd: 30.00\n")
            got = nightshift.fleet(d / "fleet.json", d / "fleet.yaml")
            self.assertEqual((got["present"], got["cap_usd"], got["data"]["spend"]["total_usd"]), (True, 30.0, 1.5))
            self.assertIsNone(nightshift.fleet(d / "fleet.json", d / "missing.yaml")["cap_usd"])  # no config: no cap shown

    def test_pull_is_a_check_on_the_fleet_object(self):
        a = actions.default_actions()["fleet-pull"]
        self.assertEqual((a["kind"], a["object"]), ("check", "fleet"))


class Schedules(unittest.TestCase):
    def fake_run(self, rows):
        return mock.patch("nightshift.subprocess.run", return_value=mock.Mock(stdout=json.dumps(rows)))

    def test_results_classified_and_single_task_object_accepted(self):
        row = {"name": "SecondBrain-LedgerRefresh", "state": "Ready", "last": "2026-11-01T10:00:00", "result": 0, "next": None}
        with self.fake_run(row):  # one task serialises as an object, not a list
            got = nightshift.schedules()
        self.assertEqual([(s["name"], s["ok"], s["log"]) for s in got], [("SecondBrain-LedgerRefresh", True, "ledger-refresh")])
        bad = dict(row, name="SecondBrain-WeeklyReview", result=1)
        running = dict(row, name="SecondBrain-Dashboard", result=267009)
        with self.fake_run([bad, running]):
            got = {s["name"]: s["ok"] for s in nightshift.schedules()}
        self.assertEqual(got, {"SecondBrain-WeeklyReview": False, "SecondBrain-Dashboard": True})
        stopped = dict(row, name="SecondBrain-WeeklyReview", result=267014)  # ended by the user, not a failure
        restarted = dict(row, name="SecondBrain-Dashboard", state="Running", result=1)  # killed, then started again
        with self.fake_run([stopped, restarted]):
            self.assertTrue(all(s["ok"] for s in nightshift.schedules()))

    def test_every_logged_schedule_has_ask_claude_and_its_script(self):
        # SCHEDULE_LOGS (nightshift.py) and the ask-* table (actions.py) are kept by hand; the mart drawer needs both
        table = actions.default_actions()
        here = pathlib.Path(nightshift.__file__).parent
        launchers = any(here.glob("run_*.cmd"))  # not in the public snapshot: they hold this PC's paths
        for task, log in nightshift.SCHEDULE_LOGS.items():
            if log is None:
                continue
            self.assertIn(f"ask-{log}", table, task)
            script = re.search(r"_dashboard/(run_\w+\.cmd)", table[f"ask-{log}"]["argv"][-1])
            self.assertIsNotNone(script, task)
            if launchers:
                self.assertTrue((here / script.group(1)).exists(), task)

    def test_failed_read_is_reported_not_no_data(self):
        with mock.patch.dict(nightshift._sched_cache, {"at": 0.0, "data": [], "busy": False, "error": False}), \
                mock.patch("nightshift.schedules", side_effect=OSError("powershell missing")), \
                mock.patch("nightshift.threading.Thread", lambda target, daemon: mock.Mock(start=target)):
            self.assertEqual(nightshift.schedules_view(), {"rows": [], "error": True})

    def test_failed_schedule_lights_the_mart(self):
        runner = actions.Runner({}, pathlib.Path(tempfile.gettempdir()) / "ns-none")
        with mock.patch("nightshift.schedules_cached", return_value=[{"ok": True}]):
            self.assertNotIn("mart", nightshift.live(runner)["objects"])
        with mock.patch("nightshift.schedules_cached", return_value=[{"ok": True}, {"ok": False}]):
            self.assertEqual(nightshift.live(runner)["objects"]["mart"]["state"], "failed")

    def test_log_tail_allowlist_and_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            (d / "weekly-review.log").write_text("\n".join(f"l{i}" for i in range(100)))
            (d / "secret.log").write_text("no")
            self.assertEqual(nightshift.log_tail("weekly-review", 3, d), "l97\nl98\nl99")
            for bad in ("secret", "../secret", None, ""):
                self.assertIsNone(nightshift.log_tail(bad, 3, d), bad)
            self.assertEqual(nightshift.log_tail("ledger-refresh", 3, d), "")  # allowed name, no file yet
            (d / "fleet-pull.log").write_text("ssh: timeout")
            self.assertEqual(nightshift.log_tail("fleet-pull", 3, d), "ssh: timeout")  # a check action's log
            self.assertIsNone(nightshift.log_tail("resume-mtg-web", 3, d))  # session actions stay off the list
            (d / "dashboard.log").write_text("\n".join(f"line {i:05d}" for i in range(20000)))  # well past TAIL_BYTES
            self.assertEqual(nightshift.log_tail("dashboard", 2, d), "line 19998\nline 19999")
            every = nightshift.log_tail("dashboard", 100000, d).splitlines()
            self.assertTrue(all(len(x) == 10 for x in every), every[0])  # the line the byte cut landed in is dropped
            self.assertLess(len(every), 20000)  # only the end was read


    def test_dusty_lists_unused_and_old_skills_only(self):
        skills = [{"name": n, "brief": n + " brief"} for n in ("fresh", "old", "never", "handoff")]  # handoff: session-end
        by_skill = [{"name": "fresh", "last_used": "2026-11-01"}, {"name": "old", "last_used": "2026-09-01"},
                    {"name": "gone", "last_used": "2026-01-01"}]  # used once, no longer installed
        rows = nightshift.dusty(skills, by_skill, dt.date(2026, 11, 5))
        self.assertEqual([r["name"] for r in rows], ["never", "old"])  # never used first, then oldest
        self.assertEqual(rows[1]["last_used"], "2026-09-01")


if __name__ == "__main__":
    unittest.main()
