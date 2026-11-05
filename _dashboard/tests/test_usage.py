"""Tests for the local usage/cost reader.

Run from the vault root:  python -m unittest discover -s _dashboard/tests
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import usage as u  # noqa: E402


def write_transcript(root: pathlib.Path, project: str, session: str, lines: list[dict]) -> pathlib.Path:
    d = root / project
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{session}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return p


def assistant_turn(ts: str, model: str, cwd: str, session: str, usage: dict) -> dict:
    return {
        "type": "assistant",
        "sessionId": session,
        "timestamp": ts,
        "cwd": cwd,
        "message": {"model": model, "usage": usage},
    }


def tool_turn(ts: str, cwd: str, session: str, blocks: list[dict]) -> dict:
    return {
        "type": "assistant", "sessionId": session, "timestamp": ts, "cwd": cwd,
        "message": {"model": "claude-sonnet-5", "content": blocks,
                    "usage": {"input_tokens": 1, "output_tokens": 1}},
    }


def block_line(mid: str | None, ts: str, model: str, usage: dict) -> dict:
    """One JSONL line as Claude Code writes it: one content block, the whole message's usage."""
    msg = {"model": model, "usage": usage, "content": [{"type": "text", "text": "x"}]}
    if mid:
        msg["id"] = mid
    return {"type": "assistant", "sessionId": "s1", "timestamp": ts, "cwd": "C:\\x", "message": msg}


class RepeatedMessageLines(unittest.TestCase):
    """Real transcripts repeat a message's usage on every content-block line."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        big = {"input_tokens": 10, "output_tokens": 100, "cache_read_input_tokens": 1_000_000}
        write_transcript(self.root, "proj", "s1", [
            block_line("m1", "2026-09-29T10:00:00Z", "claude-opus-5-5", big),
            block_line("m1", "2026-09-29T10:00:01Z", "claude-opus-5-5", big),
            block_line("m1", "2026-09-29T10:00:02Z", "claude-opus-5-5", big),
            block_line("m2", "2026-09-29T10:01:00Z", "claude-opus-5-5", big),
            block_line(None, "2026-09-29T10:02:00Z", "claude-opus-5-5", big),
        ])
        sub = self.root / "proj" / "s1" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-z.meta.json").write_text(json.dumps({"agentType": "sevro"}), encoding="utf-8")
        with (sub / "agent-z.jsonl").open("w", encoding="utf-8") as f:
            for _ in range(3):
                f.write(json.dumps(block_line("a1", "2026-09-29T10:05:00Z", "claude-opus-5-5", big)) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_main_session_counts_each_message_once(self):
        # m1 once, m2 once, the id-less line once: 3, not 5.
        self.assertEqual(len(list(u.iter_records(self.root))), 3)

    def test_subagent_counts_each_message_once_and_prices_opus_5_5(self):
        (run,) = list(u.iter_subagent_runs(self.root))
        self.assertEqual(run["turns"], 1)
        self.assertEqual(run["unpriced_tokens"], 0)
        # $4 in, $20 out, $0.20 cache read per million.
        self.assertAlmostEqual(run["cost_usd"], (10 * 4.00 + 100 * 20.00 + 1_000_000 * 0.20) / 1_000_000, places=9)


class AgentActivity(unittest.TestCase):
    VAULT = r"C:\Users\demo\second-brain"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        write_transcript(self.root, "proj", "s1", [
            tool_turn("2026-09-15T10:00:00Z", self.VAULT, "s1", [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "mustang", "description": "Scope the jury"}},
                {"type": "tool_use", "name": "Skill", "input": {"skill": "retro"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "x"}},
            ]),
            tool_turn("2026-06-01T10:00:00Z", self.VAULT, "s1", [
                {"type": "tool_use", "name": "Agent", "input": {"description": "no type given"}},
            ]),
            # A turn whose content is a plain string must be skipped, not crash.
            {"type": "assistant", "sessionId": "s1", "timestamp": "2026-09-15T11:00:00Z", "cwd": self.VAULT,
             "message": {"model": "claude-sonnet-5", "content": "just text", "usage": {"input_tokens": 1, "output_tokens": 1}}},
        ])
        sub = self.root / "proj" / "s1" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-abc.meta.json").write_text(json.dumps({"agentType": "mustang", "description": "Scope the jury"}), encoding="utf-8")
        with (sub / "agent-abc.jsonl").open("w", encoding="utf-8") as f:
            for ts in ("2026-09-15T10:01:00Z", "2026-09-15T10:02:00Z"):
                f.write(json.dumps(assistant_turn(ts, "claude-sonnet-5", self.VAULT, "s1",
                                                  {"input_tokens": 1000, "output_tokens": 100})) + "\n")
            f.write('{"type":"assistant","torn')  # live file, torn last line

    def tearDown(self):
        self.tmp.cleanup()

    def test_invocations_name_agent_type_and_skill(self):
        inv = sorted(u.iter_invocations(self.root), key=lambda r: r["when"])
        self.assertEqual([(r["kind"], r["name"]) for r in inv],
                         [("agent", "general-purpose"), ("agent", "mustang"), ("skill", "retro")])
        self.assertEqual(inv[1]["description"], "Scope the jury")
        self.assertEqual(inv[1]["project"], "second-brain (vault)")

    def test_subagent_run_is_priced_and_torn_line_skipped(self):
        runs = list(u.iter_subagent_runs(self.root))
        self.assertEqual(len(runs), 1)
        r = runs[0]
        self.assertEqual(r["agent_type"], "mustang")
        self.assertEqual(r["turns"], 2)
        self.assertAlmostEqual(r["cost_usd"], 2 * (1000 * 2.00 + 100 * 10.00) / 1_000_000, places=9)
        self.assertEqual(r["session_id"], "s1")

    def test_activity_joins_calls_and_runs(self):
        act = u.agent_activity(self.root, days=30, today=dt.date(2026, 9, 15))
        by = {r["name"]: r for r in act["by_agent"]}
        self.assertEqual(by["mustang"]["invocations"], 1)
        self.assertEqual(by["mustang"]["runs"], 1)
        self.assertEqual(by["mustang"]["last_used"], "2026-09-15")
        self.assertEqual(by["general-purpose"]["invocations_recent"], 0)
        self.assertEqual(by["general-purpose"]["invocations"], 1)
        self.assertEqual({r["name"]: r["invocations"] for r in act["by_skill"]}, {"retro": 1})
        self.assertEqual(act["totals"]["subagent_runs"], 1)
        self.assertEqual(act["recent"][0]["name"], "mustang")

    def test_session_totals_exclude_subagent_transcripts(self):
        # The Usage page counts main-session turns only; subagent tokens
        # belong to the Agents page. This pins that split so a change to
        # either reader is a deliberate one.
        self.assertEqual(u.summary(self.root, days=30, today=dt.date(2026, 9, 15))["overall"]["turns"], 3)


class SkillRoutes(unittest.TestCase):
    """Line shapes copied from real 2.1.278 transcripts, 2026-09-26."""
    VAULT = r"C:\Users\demo\second-brain"

    def user(self, ts, content, **extra):
        return {"type": "user", "sessionId": "s1", "timestamp": ts, "cwd": self.VAULT,
                "message": {"role": "user", "content": content}, **extra}

    def skill_body(self, ts, base, **extra):
        return self.user(ts, [{"type": "text", "text": f"Base directory for this skill: {base}\n\n# Body"}],
                         isMeta=True, **extra)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        write_transcript(self.root, "proj", "s1", [
            # slash: /retro, then its body with no sourceToolUseID
            self.user("2026-09-22T03:03:46Z", "<command-message>retro</command-message>\n<command-name>/retro</command-name>"),
            self.skill_body("2026-09-22T03:03:46Z", self.VAULT + r"\.claude\skills\retro"),
            # plugin skill by slash keeps its prefix from <command-name>
            self.user("2026-09-22T04:00:00Z", "<command-message>codex:rescue</command-message>\n<command-name>/codex:rescue</command-name>"),
            self.skill_body("2026-09-22T04:00:00Z", r"C:\Users\demo\.claude\plugins\cache\codex\skills\rescue"),
            # tool: a Skill call, whose body carries sourceToolUseID and must not count again
            tool_turn("2026-09-22T05:00:00Z", self.VAULT, "s1", [
                {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "today"}}]),
            self.skill_body("2026-09-22T05:00:01Z", self.VAULT + r"\.claude\skills\today", sourceToolUseID="t1"),
            # read: SKILL.md counts, any other file does not
            tool_turn("2026-09-22T06:00:00Z", self.VAULT, "s1", [
                {"type": "tool_use", "name": "Read", "input": {"file_path": self.VAULT + r"\.claude\skills\triage\SKILL.md"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": self.VAULT + r"\.claude\skills\triage\notes.md"}}]),
            # built-in /model: no skill body, not a skill
            self.user("2026-09-22T07:00:00Z", "<command-name>/model</command-name>"),
            self.user("2026-09-22T07:00:01Z", [{"type": "text", "text": "<local-command-caveat>Caveat</local-command-caveat>"}], isMeta=True),
            # a tool_result quoting a transcript: same tags, not a use
            self.user("2026-09-22T08:00:00Z", [{"type": "tool_result", "tool_use_id": "x",
                      "content": "<command-name>/retro</command-name> Base directory for this skill: C:\\x\\retro"}]),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def skills(self):
        return sorted((r["route"], r["name"]) for r in u.iter_invocations(self.root) if r["kind"] == "skill")

    def test_each_route_counted_once(self):
        self.assertEqual(self.skills(), [
            ("read", "triage"), ("slash", "codex:rescue"), ("slash", "retro"), ("tool", "today")])

    def test_slash_without_command_name_falls_back_to_folder(self):
        write_transcript(self.root, "proj", "s2", [
            self.skill_body("2026-09-22T09:00:00Z", self.VAULT + r"\.claude\skills\capture")])
        self.assertIn(("slash", "capture"), self.skills())

    def test_activity_rows_split_routes(self):
        act = u.agent_activity(self.root, days=30, today=dt.date(2026, 9, 22))
        self.assertEqual({r["name"]: r["routes"] for r in act["by_skill"]}, {
            "retro": {"slash": 1}, "codex:rescue": {"slash": 1}, "today": {"tool": 1}, "triage": {"read": 1}})


class ProjectLabel(unittest.TestCase):
    def test_vault_subproject_gets_its_own_name(self):
        self.assertEqual(u._project_label(r"C:\Users\demo\second-brain\projects\mtg-web"), "mtg-web")
        self.assertEqual(u._project_label("/c/Users/demo/second-brain/projects/mtg-web/frontend"), "mtg-web")

    def test_vault_root_is_labelled_as_the_vault(self):
        self.assertEqual(u._project_label(r"C:\Users\demo\second-brain"), "second-brain (vault)")

    def test_unrelated_path_falls_back_to_basename(self):
        self.assertEqual(u._project_label(r"C:\Users\demo\Claude\some-tool"), "some-tool")


class CostEstimate(unittest.TestCase):
    def test_known_model_prices_all_four_token_kinds(self):
        rec = {
            "model": "claude-sonnet-5",
            "input_tokens": 1_000_000, "output_tokens": 1_000_000,
            "cache_read_input_tokens": 1_000_000,
            "cache_write_5m": 1_000_000, "cache_write_1h": 0, "cache_write_untyped": 0,
        }
        # input $2 + output $10 + cache_read (0.1x of $2) + cache_write_5m (1.25x of $2)
        expected = 2.00 + 10.00 + 0.20 + 2.50
        self.assertAlmostEqual(u.estimate_cost_usd(rec), expected, places=6)

    def test_unpriced_model_returns_none_not_zero(self):
        rec = {"model": "some-future-model", "input_tokens": 100, "output_tokens": 0,
              "cache_read_input_tokens": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_write_untyped": 0}
        self.assertIsNone(u.estimate_cost_usd(rec))

    def test_untyped_cache_creation_treated_as_5m(self):
        rec = {"model": "claude-opus-5", "input_tokens": 0, "output_tokens": 0,
              "cache_read_input_tokens": 0, "cache_write_5m": 0, "cache_write_1h": 0,
              "cache_write_untyped": 1_000_000}
        self.assertAlmostEqual(u.estimate_cost_usd(rec), 5.00 * 1.25, places=6)


class IterRecords(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_usage_and_skips_turns_without_it(self):
        write_transcript(self.root, "proj", "s1", [
            {"type": "user", "message": {"content": "hi"}},
            assistant_turn("2026-09-14T10:00:00Z", "claude-sonnet-5", r"C:\v\projects\mtg-web", "s1",
                          {"input_tokens": 5, "output_tokens": 7}),
            {"type": "assistant", "message": {"model": "x"}},  # no usage: skipped
        ])
        recs = list(u.iter_records(self.root))
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["project"], "mtg-web")
        self.assertEqual(recs[0]["input_tokens"], 5)
        self.assertEqual(recs[0]["date"], "2026-09-14")

    def test_malformed_line_does_not_break_the_rest(self):
        d = self.root / "proj"
        d.mkdir(parents=True)
        p = d / "s1.jsonl"
        p.write_text(
            "not json at all\n"
            + json.dumps(assistant_turn("2026-09-14T10:00:00Z", "claude-sonnet-5", "/x", "s1", {"input_tokens": 1})) + "\n"
            + "{truncated line with no closing brace\n",
            encoding="utf-8",
        )
        recs = list(u.iter_records(self.root))
        self.assertEqual(len(recs), 1)

    def test_split_cache_creation_object_is_read(self):
        write_transcript(self.root, "proj", "s1", [
            assistant_turn("2026-09-14T10:00:00Z", "claude-opus-5", "/x", "s1", {
                "input_tokens": 1, "output_tokens": 1,
                "cache_creation": {"ephemeral_1h_input_tokens": 500, "ephemeral_5m_input_tokens": 200},
            }),
        ])
        rec = next(u.iter_records(self.root))
        self.assertEqual(rec["cache_write_1h"], 500)
        self.assertEqual(rec["cache_write_5m"], 200)
        self.assertEqual(rec["cache_write_untyped"], 0)


class Aggregate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        write_transcript(self.root, "proj", "s1", [
            assistant_turn("2026-09-14T10:00:00Z", "claude-sonnet-5", "/v/projects/mtg-web", "s1",
                          {"input_tokens": 100, "output_tokens": 200}),
            assistant_turn("2026-09-14T10:05:00Z", "claude-sonnet-5", "/v/projects/mtg-web", "s1",
                          {"input_tokens": 50, "output_tokens": 60}),
        ])
        write_transcript(self.root, "proj2", "s2", [
            assistant_turn("2026-09-01T09:00:00Z", "claude-opus-5", "/v/projects/recipe-box", "s2",
                          {"input_tokens": 10, "output_tokens": 10}),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_overall_and_per_project_totals(self):
        result = u.aggregate(u.iter_records(self.root), days=30, today=dt.date(2026, 9, 15))
        self.assertEqual(result["overall"]["turns"], 3)
        self.assertEqual(result["overall"]["input_tokens"], 160)
        projects = {p["project"]: p for p in result["by_project"]}
        self.assertEqual(projects["mtg-web"]["turns"], 2)
        self.assertEqual(projects["recipe-box"]["turns"], 1)

    def test_daily_series_covers_the_full_window_with_zero_days(self):
        result = u.aggregate(u.iter_records(self.root), days=5, today=dt.date(2026, 9, 15))
        self.assertEqual(len(result["daily"]), 5)
        dates = [d["date"] for d in result["daily"]]
        self.assertEqual(dates, ["2026-09-11", "2026-09-12", "2026-09-13", "2026-09-14", "2026-09-15"])
        by_date = {d["date"]: d for d in result["daily"]}
        self.assertEqual(by_date["2026-09-14"]["turns"], 2)
        self.assertEqual(by_date["2026-09-11"]["turns"], 0)

    def test_daily_window_excludes_older_activity_but_totals_still_include_it(self):
        result = u.aggregate(u.iter_records(self.root), days=5, today=dt.date(2026, 9, 15))
        self.assertEqual(sum(d["turns"] for d in result["daily"]), 2)  # the 09-01 turn is outside the window
        self.assertEqual(result["overall"]["turns"], 3)  # but still counted overall

    def test_sessions_grouped_with_duration_and_sorted_newest_first(self):
        result = u.aggregate(u.iter_records(self.root), days=30, today=dt.date(2026, 9, 15))
        self.assertEqual(len(result["sessions"]), 2)
        first = result["sessions"][0]
        self.assertEqual(first["session_id"], "s1")
        self.assertEqual(first["duration_minutes"], 5.0)
        self.assertEqual(first["models"], ["claude-sonnet-5"])

    def test_unpriced_model_tracked_separately_from_cost(self):
        write_transcript(self.root, "proj3", "s3", [
            assistant_turn("2026-09-14T10:00:00Z", "claude-nonexistent", "/v", "s3", {"input_tokens": 1000}),
        ])
        result = u.aggregate(u.iter_records(self.root), days=30, today=dt.date(2026, 9, 15))
        self.assertIn("claude-nonexistent", result["unpriced_models"])
        by_model = {m["model"]: m for m in result["by_model"]}
        self.assertEqual(by_model["claude-nonexistent"]["unpriced_tokens"], 1000)
        self.assertEqual(by_model["claude-nonexistent"]["cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
