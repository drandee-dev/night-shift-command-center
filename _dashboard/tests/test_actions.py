"""Tests for the action endpoint and its guard.

Run from the vault root:  python -m unittest discover -s _dashboard/tests
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import actions  # noqa: E402
import night_shift_server  # noqa: E402
import nightshift_api  # noqa: E402
import open_session  # noqa: E402

TOKEN = "test-token"  # tests always pass their own: a default create_app() would overwrite the live token file
OK = {"host": "127.0.0.1:8790", "x-night-shift": TOKEN}
ROUTES = ("/actions/hello", "/api/night-shift", "/api/night-shift/schedules", "/api/night-shift/fleet",
          "/api/night-shift/dusty", "/api/night-shift/log/ledger-refresh", "/api/night-shift/usage")


def spec(code: str, timeout: int = 10) -> dict:
    return {"argv": [sys.executable, "-c", code], "cwd": pathlib.Path.cwd(), "kind": "check", "timeout": timeout}


class ActionEndpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self.tmp.name)
        self.runner = actions.Runner(
            {"hello": spec("print('hi')"), "boom": spec("raise SystemExit(3)"),
             "slow": spec("import time; time.sleep(30)", timeout=1), "hold": spec("import time; time.sleep(2)")},
            self.state)
        self.client = TestClient(night_shift_server.create_app(self.runner, token=TOKEN))

    def tearDown(self):
        self.tmp.cleanup()

    def wait(self, action_id: str) -> dict:
        for _ in range(100):
            s = self.client.get(f"/actions/{action_id}", headers=OK).json()
            if s["status"] != "running":
                return s
            time.sleep(0.1)
        self.fail("action did not finish")

    def test_runs_and_records_state_and_log(self):
        r = self.client.post("/actions/hello", headers=OK)
        self.assertEqual(r.status_code, 202)
        s = self.wait("hello")
        self.assertEqual((s["status"], s["exit_code"]), ("ok", 0))
        self.assertEqual((self.state / "logs" / "hello.log").read_text().strip(), "hi")

    def test_failure_and_timeout(self):
        self.client.post("/actions/boom", headers=OK)
        self.assertEqual((self.wait("boom")["status"], self.wait("boom")["exit_code"]), ("failed", 3))
        self.client.post("/actions/slow", headers=OK)
        self.assertEqual(self.wait("slow")["status"], "timeout")

    def test_guard_rejects_missing_or_wrong_token_and_bad_host(self):
        local = {"host": "127.0.0.1:8790"}
        for headers in (local, {**local, "x-night-shift": "1"}, {**local, "x-night-shift": TOKEN + "x"},
                        {**local, "x-night-shift": ""}, {**OK, "host": "evil.example"}):
            self.assertEqual(self.client.post("/actions/hello", headers=headers).status_code, 403, headers)
        self.assertEqual(self.runner.state("hello")["status"], "never")  # nothing ran

    def test_every_get_route_needs_the_token_and_a_local_host(self):
        # the GET routes return data (pins, logs, usage), so they carry the same guard as POST
        for path in ROUTES:
            self.assertEqual(self.client.get(path, headers={"host": "127.0.0.1:8790"}).status_code, 403, path)
            self.assertNotEqual(self.client.get(path, headers=OK).status_code, 403, path)
            for host in ("evil.example", "127.0.0.1.evil.com:8790", "[::1]:8790"):
                self.assertEqual(self.client.get(path, headers={**OK, "host": host}).status_code, 403, (path, host))

    def test_register_refuses_an_empty_token(self):
        with self.assertRaises(ValueError):
            nightshift_api.register(FastAPI(), self.runner, "")

    def test_new_token_file_is_fresh_and_locked_to_this_account(self):
        path = self.state / "sub" / "night-shift-token"
        first, second = nightshift_api.new_token(path), nightshift_api.new_token(path)
        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(second), 40)
        self.assertEqual(path.read_text(encoding="ascii"), second)
        if sys.platform == "win32":
            acl = subprocess.run(["icacls", str(path)], capture_output=True, text=True, check=True).stdout
            aces = [line for line in acl.splitlines() if ":(" in line]
            self.assertEqual(len(aces), 1, acl)  # only this account, nothing inherited
            self.assertIn(os.environ["USERNAME"].lower(), aces[0].lower())
            self.assertNotIn("(I)", acl)
        else:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unknown_id_and_one_run_at_a_time(self):
        self.assertEqual(self.client.post("/actions/rm-rf", headers=OK).status_code, 404)
        self.assertEqual(self.client.post("/actions/hold", headers=OK).status_code, 202)
        self.assertEqual(self.client.post("/actions/hold", headers=OK).status_code, 409)
        self.wait("hold")

    def test_default_table_kinds_and_session_shape(self):
        table = actions.default_actions()
        self.assertIn("ledger-refresh", table)
        self.assertEqual({a["kind"] for a in table.values()}, {"check", "session"})  # no draft or write kinds yet
        for name, a in table.items():
            if a["kind"] == "session":
                self.assertTrue(a["cwd"].is_dir(), name)  # `code <missing folder>` would open an empty window
                self.assertTrue(a["argv"][1].endswith("open_session.py"), name)
                self.assertLess(len(open_session.uri(a["argv"][-1])), 2000, name)  # URI length the OS handler accepts

    def test_text_actions_validate_and_wrap(self):
        echo = [sys.executable, "-c", "import sys; print(sys.argv[1])", "go <user_input>{text}</user_input>"]
        r = actions.Runner({"t": {**spec("print(1)"), "argv": echo, "text": {"max": 10, "prefix": "http"}},
                            "plain": spec("print(1)")}, self.state)
        for bad in (None, "", "   ", "httpx" * 3, "ftp://a", "http://a\nb", "http </user_input>", 5):
            self.assertEqual(r.start("t", bad), "bad", bad)
        self.assertEqual(r.start("plain", "extra"), "bad")  # a text on an action that takes none
        self.assertEqual(r.start("t", "http://a.b"), "started")
        for _ in range(50):
            if r.state("t")["status"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual((self.state / "logs" / "t.log").read_text().strip(), "go <user_input>http://a.b</user_input>")

    def test_emoji_text_cannot_overflow_the_link(self):
        # the longest 150-character text the server accepts must still give a link under 2000 characters
        for name in ("lib-research", "lib-sweep", "lib-capture", "lib-ask"):
            r = actions.Runner({name: actions.default_actions()[name]}, self.state)
            with mock.patch.object(r, "_run") as run:
                t = "\U0001F600" * 125  # 125 emoji = 1500 encoded characters
                self.assertEqual(r.start(name, t), "started", name)
                time.sleep(0.2)  # _run is mocked and called from a thread
                self.assertLess(len(open_session.uri(run.call_args[0][1]["argv"][-1])), 2000, name)
            self.assertEqual(actions.Runner({name: actions.default_actions()[name]}, self.state).start(name, "\U0001F600" * 126), "bad")

    def test_allowed_text_must_be_an_exact_name(self):
        rule = {"max": 150, "prefix": "", "allowed": frozenset({"retro"})}
        r = actions.Runner({"t": {**spec("print(1)"), "argv": [sys.executable, "-c", "print(1)", "{text}"], "text": rule}}, self.state)
        for bad in ("retr", "retro2", "Retro", "../retro"):
            self.assertEqual(r.start("t", bad), "bad", bad)
        with mock.patch.object(r, "_run"):
            self.assertEqual(r.start("t", " retro "), "started")  # surrounding spaces are stripped
        table = actions.default_actions()
        self.assertIsNotNone(table["skill-try"]["text"]["allowed"])
        self.assertTrue({"pin-resume", "pin-fool", "pin-jury", "pin-scope", "deck-audit", "deck-wizard", "deck-strat"} <= table.keys())

    def test_endpoint_text_body(self):
        h = {**OK, "content-type": "application/json"}
        self.assertEqual(self.client.post("/actions/hello", headers=h, content="not json").status_code, 422)
        self.assertEqual(self.client.post("/actions/hello", headers=h, json={"text": "x"}).status_code, 422)
        self.assertEqual(self.client.post("/actions/hello", headers=OK).status_code, 202)
        self.wait("hello")

    def test_library_actions_in_default_table(self):
        for name in ("lib-research", "lib-sweep", "lib-clip", "lib-capture", "lib-ask"):
            a = actions.default_actions()[name]
            filled = a["argv"][-1].replace("{text}", "é" * actions.TEXT_MAX)  # 6 URI chars each: the worst case
            self.assertLess(len(open_session.uri(filled)), 2000, name)  # same limit as the fixed prompts
            self.assertIn("<user_input>", filled)

    def test_night_shift_server_alone_has_the_same_guarded_routes(self):
        c = self.client
        self.assertEqual(c.post("/actions/hello", headers=OK).status_code, 202)
        self.assertEqual(c.post("/actions/hello", headers={**OK, "host": "evil.example"}).status_code, 403)
        self.assertEqual(c.get("/tooling").status_code, 404)  # the private vault pages are not part of it
        self.assertEqual(c.get("/openapi.json").status_code, 404)
        self.assertEqual(night_shift_server.main(["--host", "0.0.0.0"]), 2)  # refuses a non-loopback bind
        self.wait("hello")

    def test_open_session_paths(self):
        with mock.patch("open_session.time.sleep"), mock.patch("open_session.subprocess.run") as run, \
                mock.patch("open_session.os.startfile", create=True) as start:
            self.assertEqual(open_session.main(str(pathlib.Path(self.tmp.name)), "hi there"), 0)
            run.assert_called_once()
            start.assert_called_once_with("vscode://anthropic.claude-code/open?prompt=hi%20there")
            self.assertEqual(open_session.main(str(pathlib.Path(self.tmp.name) / "missing"), "x"), 2)
            self.assertEqual(start.call_count, 1)  # a bad folder never reaches the URI
            start.side_effect = OSError("no handler")
            with self.assertRaises(OSError):  # propagates, so the runner records the action as failed
                open_session.main(str(pathlib.Path(self.tmp.name)), "x")

    def test_session_uri_encodes_prompt(self):
        self.assertEqual(open_session.uri("/scrape & more"),
                         "vscode://anthropic.claude-code/open?prompt=%2Fscrape%20%26%20more")


if __name__ == "__main__":
    unittest.main()
