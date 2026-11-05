"""Local Claude Code usage and cost, read straight from session transcripts.

Every session under `~/.claude/projects/*/*.jsonl` already logs a real
`usage` block on each assistant turn: input/output tokens, cache
write/read tokens, and the model. Nothing here calls out, uploads
anything, or depends on a third-party package -- it is a pure read of
files Claude Code already writes, the same trust model as the rest of
this dashboard.

Cost is an estimate, not a bill. Anthropic doesn't put a live price on
each transcript line, so `PRICING` is a small table of published
per-model rates, and cache writes/reads are priced by the public
multiplier convention (5m write 1.25x base input, 1h write 2x, read
0.1x) applied to that model's own input rate. A price change or a model
missing from the table shows as `None` rather than a silently wrong
number.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
from collections import defaultdict

PROJECTS_ROOT = pathlib.Path.home() / ".claude" / "projects"

# $ per million tokens: (input, output) or (input, output, cache read) when
# the cache read isn't the usual 10% of input. Source: the claude-api skill's
# cached pricing table, 2026-09-25. Update here when rates change --
# nothing else in this module hardcodes a rate.
PRICING: dict[str, tuple[float, ...]] = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # Transcripts carry the dated id for Haiku; found 2026-09-15 when a
    # claude-code-guide run showed 807k tokens as unpriced.
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-fable-5": (10.00, 50.00),
}

CACHE_WRITE_5M_MULTIPLIER = 1.25
CACHE_WRITE_1H_MULTIPLIER = 2.00
CACHE_READ_MULTIPLIER = 0.10


def _project_label(cwd: str) -> str:
    """A short, readable label for a session's working directory.

    Sessions inside a vault sub-project (`.../second-brain/projects/<name>`)
    are labelled by that name, since that is the unit a person thinks in;
    everything else falls back to the last path component.
    """
    norm = cwd.replace("\\", "/").rstrip("/")
    marker = "second-brain/projects/"
    idx = norm.find(marker)
    if idx != -1:
        rest = norm[idx + len(marker):]
        return rest.split("/")[0] if rest else "second-brain"
    if norm.endswith("second-brain"):
        return "second-brain (vault)"
    return norm.rsplit("/", 1)[-1] or norm


def _project_dirs(root: pathlib.Path):
    if not root.exists():
        return
    for project_dir in sorted(root.iterdir()):
        if project_dir.is_dir():
            yield project_dir


def _iter_json(path: pathlib.Path):
    """Yield each JSON object in a transcript, streamed line by line.

    A line that isn't valid JSON is skipped rather than raising -- a
    transcript is a live, append-only file and a torn last line is
    expected, not corruption. An unreadable file yields nothing.
    """
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _assistant_turns(path: pathlib.Path):
    """Yield (obj, message, when) once per assistant message with a timestamp.

    Claude Code writes one line per content block, each repeating the whole
    message's `usage`, so lines sharing a message id are yielded only once;
    summing every line over-counted 1.6-3x (found 2026-09-30).
    """
    seen: set[str] = set()
    for obj in _iter_json(path):
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        mid = msg.get("id")
        if mid:
            if mid in seen:
                continue
            seen.add(mid)
        when = _parse_ts(obj.get("timestamp"))
        if when is None:
            continue
        yield obj, msg, when


def _usage_record(obj: dict, msg: dict, usage: dict, when: dt.datetime, project_dir: pathlib.Path, path: pathlib.Path) -> dict:
    cache_creation = usage.get("cache_creation") or {}
    return {
        "session_id": obj.get("sessionId") or path.stem,
        "session_file": path.name,
        "project_dir": project_dir.name,
        "project": _project_label(obj.get("cwd") or project_dir.name),
        "model": msg.get("model") or "unknown",
        "when": when,
        "date": when.date().isoformat(),
        "input_tokens": usage.get("input_tokens") or 0,
        "output_tokens": usage.get("output_tokens") or 0,
        "cache_read_input_tokens": usage.get("cache_read_input_tokens") or 0,
        "cache_write_5m": cache_creation.get("ephemeral_5m_input_tokens") or 0,
        "cache_write_1h": cache_creation.get("ephemeral_1h_input_tokens") or 0,
        # Older transcripts predate the split cache_creation object and only
        # carry the flat total; treat that as a 5m write, the default TTL,
        # rather than dropping it.
        "cache_write_untyped": (
            usage.get("cache_creation_input_tokens") or 0
            if not cache_creation else 0
        ),
    }


def iter_records(root: pathlib.Path = PROJECTS_ROOT):
    """Yield one dict per main-session assistant turn that carries a usage block.

    Reads every top-level `*.jsonl` under every project folder. Subagent
    transcripts (`<session>/subagents/*.jsonl`) are deliberately not
    included here; `iter_subagent_runs` reads those, so their tokens show
    on the Agents page rather than being folded into the session totals.
    """
    for project_dir in _project_dirs(root):
        for path in sorted(project_dir.glob("*.jsonl")):
            for obj, msg, when in _assistant_turns(path):
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                yield _usage_record(obj, msg, usage, when, project_dir, path)


def _parse_ts(ts) -> dt.datetime | None:
    if not isinstance(ts, str):
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def estimate_cost_usd(rec: dict) -> float | None:
    """Dollar estimate for one record, or None if its model has no known
    rate -- callers must not silently treat that as zero."""
    rate = PRICING.get(rec["model"])
    if rate is None:
        return None
    input_rate, output_rate = rate[:2]
    read_rate = rate[2] if len(rate) > 2 else input_rate * CACHE_READ_MULTIPLIER
    cost = rec["input_tokens"] * input_rate
    cost += rec["output_tokens"] * output_rate
    cost += rec["cache_write_5m"] * input_rate * CACHE_WRITE_5M_MULTIPLIER
    cost += rec["cache_write_1h"] * input_rate * CACHE_WRITE_1H_MULTIPLIER
    cost += rec["cache_write_untyped"] * input_rate * CACHE_WRITE_5M_MULTIPLIER
    cost += rec["cache_read_input_tokens"] * read_rate
    return cost / 1_000_000


def _empty_bucket() -> dict:
    return {
        "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
        "cache_write_tokens": 0, "cost_usd": 0.0, "unpriced_tokens": 0, "turns": 0,
    }


def _add(bucket: dict, rec: dict, cost: float | None) -> None:
    bucket["input_tokens"] += rec["input_tokens"]
    bucket["output_tokens"] += rec["output_tokens"]
    bucket["cache_read_input_tokens"] += rec["cache_read_input_tokens"]
    bucket["cache_write_tokens"] += rec["cache_write_5m"] + rec["cache_write_1h"] + rec["cache_write_untyped"]
    bucket["turns"] += 1
    if cost is None:
        total = rec["input_tokens"] + rec["output_tokens"] + rec["cache_read_input_tokens"]
        total += rec["cache_write_5m"] + rec["cache_write_1h"] + rec["cache_write_untyped"]
        bucket["unpriced_tokens"] += total
    else:
        bucket["cost_usd"] += cost


def aggregate(records, days: int = 30, today: dt.date | None = None) -> dict:
    """One pass over `records` (an iterable, consumed once) producing every
    view the dashboard needs: daily totals, per-project, per-model, and a
    per-session index. `days` bounds only the daily trend; project/model/
    session totals cover everything found."""
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=days - 1)

    daily: dict[str, dict] = defaultdict(_empty_bucket)
    by_project: dict[str, dict] = defaultdict(_empty_bucket)
    by_model: dict[str, dict] = defaultdict(_empty_bucket)
    sessions: dict[str, dict] = {}
    overall = _empty_bucket()

    for rec in records:
        cost = estimate_cost_usd(rec)
        overall_bucket = overall
        _add(overall_bucket, rec, cost)
        by_project_bucket = by_project[rec["project"]]
        _add(by_project_bucket, rec, cost)
        by_model_bucket = by_model[rec["model"]]
        _add(by_model_bucket, rec, cost)
        if rec["date"] >= cutoff.isoformat():
            _add(daily[rec["date"]], rec, cost)

        s = sessions.setdefault(rec["session_id"], {
            "session_id": rec["session_id"], "project": rec["project"],
            "start": rec["when"], "end": rec["when"], "models": set(),
            **_empty_bucket(),
        })
        s["start"] = min(s["start"], rec["when"])
        s["end"] = max(s["end"], rec["when"])
        s["models"].add(rec["model"])
        _add(s, rec, cost)

    session_list = []
    for s in sessions.values():
        s = dict(s)
        s["models"] = sorted(s["models"])
        s["duration_minutes"] = round((s["end"] - s["start"]).total_seconds() / 60, 1)
        s["start"] = s["start"].isoformat()
        s["end"] = s["end"].isoformat()
        session_list.append(s)
    session_list.sort(key=lambda s: s["end"], reverse=True)

    day_list = []
    d = cutoff
    while d <= today:
        iso = d.isoformat()
        bucket = daily.get(iso, _empty_bucket())
        day_list.append({"date": iso, **bucket})
        d += dt.timedelta(days=1)

    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "days": days,
        "overall": overall,
        "daily": day_list,
        "by_project": [{"project": k, **v} for k, v in sorted(by_project.items(), key=lambda kv: -kv[1]["cost_usd"])],
        "by_model": [{"model": k, **v} for k, v in sorted(by_model.items(), key=lambda kv: -kv[1]["cost_usd"])],
        "sessions": session_list,
        "unpriced_models": sorted({k for k, v in by_model.items() if v["unpriced_tokens"] > 0}),
    }


def summary(root: pathlib.Path = PROJECTS_ROOT, days: int = 30, today: dt.date | None = None) -> dict:
    return aggregate(iter_records(root), days=days, today=today)


# --------------------------------------------------------------------------
# Agents and skills
# --------------------------------------------------------------------------

SKILL_BASE_MARKER = "Base directory for this skill: "
_COMMAND_NAME = re.compile(r"<command-name>/([^<\s]+)</command-name>")


def _skill_calls(obj: dict, last_command: str | None):
    """(route, name, description) for each skill use on one transcript line.

    Three routes, verified against real transcripts 2026-09-26:
    - "tool":  an assistant `Skill` tool_use.
    - "slash": a user typed `/name`. The skill body lands as an `isMeta`
      user text block starting with SKILL_BASE_MARKER and *no*
      `sourceToolUseID` (a Skill tool load has one, and is already counted
      as "tool"). Built-ins like /model or /doctor never carry the marker.
      Named from the preceding `<command-name>`, so plugin skills keep
      their `plugin:` prefix; falls back to the base directory's name.
    - "read":  an assistant `Read` of a `SKILL.md`, named by its folder.
      Editing a skill reads it too, so this route is kept separate.
    Only line shape is matched, never substrings: a tool_result quoting a
    transcript contains the same tags.
    """
    msg = obj.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, list):
        return
    if obj.get("type") == "user":
        if not obj.get("isMeta") or obj.get("sourceToolUseID"):
            return
        first = content[0] if content and isinstance(content[0], dict) else {}
        text = first.get("text") if first.get("type") == "text" else None
        if isinstance(text, str) and text.startswith(SKILL_BASE_MARKER):
            base = text[len(SKILL_BASE_MARKER):].split("\n", 1)[0].strip()
            yield "slash", last_command or pathlib.PureWindowsPath(base).name, ""
        return
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        inp = block.get("input") if isinstance(block.get("input"), dict) else {}
        if block.get("name") == "Agent":
            yield "agent", inp.get("subagent_type") or "general-purpose", inp.get("description")
        elif block.get("name") == "Skill" and inp.get("skill"):
            yield "tool", inp["skill"], inp.get("args")
        elif block.get("name") == "Read":
            fp = pathlib.PureWindowsPath(str(inp.get("file_path") or ""))
            if fp.name == "SKILL.md" and fp.parent.name:
                yield "read", fp.parent.name, str(fp)


def iter_invocations(root: pathlib.Path = PROJECTS_ROOT):
    """Yield one dict per Agent call or skill use in a main-session transcript.

    An `Agent` call names its `subagent_type` (missing means the default
    general-purpose agent). Skill uses come by three routes, see
    `_skill_calls`. The description or args string is kept, truncated, so
    the page can show what each call was for.
    """
    for project_dir in _project_dirs(root):
        for path in sorted(project_dir.glob("*.jsonl")):
            last_command = None
            for obj in _iter_json(path):
                msg = obj.get("message")
                if obj.get("type") == "user" and isinstance(msg, dict) and isinstance(msg.get("content"), str):
                    m = _COMMAND_NAME.search(msg["content"])
                    last_command = m.group(1) if m else None
                    continue
                if obj.get("type") not in ("user", "assistant"):
                    continue
                when = _parse_ts(obj.get("timestamp"))
                if when is None:
                    continue
                for route, name, desc in _skill_calls(obj, last_command):
                    if route == "slash":
                        last_command = None
                    yield {
                        "kind": "agent" if route == "agent" else "skill",
                        "route": "tool" if route == "agent" else route,
                        "name": str(name),
                        "description": str(desc or "")[:120],
                        "when": when,
                        "date": when.date().isoformat(),
                        "session_id": obj.get("sessionId") or path.stem,
                        "project": _project_label(obj.get("cwd") or project_dir.name),
                    }


def iter_subagent_runs(root: pathlib.Path = PROJECTS_ROOT):
    """Yield one dict per subagent transcript, with its own token totals.

    Claude Code writes each spawned agent to
    `<project>/<session>/subagents/agent-<id>.jsonl` plus a `.meta.json`
    naming the `agentType`. The assistant turns inside carry the same
    `usage` block as a main session, so they are priced the same way.
    """
    for project_dir in _project_dirs(root):
        for meta_path in sorted(project_dir.glob("*/subagents/agent-*.meta.json")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {}
            if not isinstance(meta, dict):
                meta = {}
            jsonl = meta_path.with_name(meta_path.name[: -len(".meta.json")] + ".jsonl")
            bucket = _empty_bucket()
            models: set[str] = set()
            start = end = None
            cwd = session = None
            for obj, msg, when in _assistant_turns(jsonl):
                usage = msg.get("usage")
                if not isinstance(usage, dict):
                    continue
                rec = _usage_record(obj, msg, usage, when, project_dir, jsonl)
                _add(bucket, rec, estimate_cost_usd(rec))
                models.add(rec["model"])
                cwd = cwd or obj.get("cwd")
                session = session or obj.get("sessionId")
                start = when if start is None else min(start, when)
                end = when if end is None else max(end, when)
            yield {
                "agent_id": jsonl.stem,
                "agent_type": str(meta.get("agentType") or "unknown"),
                "description": str(meta.get("description") or "")[:120],
                "session_id": session or meta_path.parent.parent.name,
                "project": _project_label(cwd or project_dir.name),
                "models": sorted(models),
                "start": start,
                "end": end,
                **bucket,
            }


def _empty_agent_row(name: str) -> dict:
    return {
        "name": name, "invocations": 0, "invocations_recent": 0, "runs": 0, "turns": 0,
        "tokens": 0, "cost_usd": 0.0, "unpriced_tokens": 0, "last_used": "",
        "projects": set(), "models": set(), "routes": defaultdict(int),
    }


def agent_activity(root: pathlib.Path = PROJECTS_ROOT, days: int = 30, today: dt.date | None = None) -> dict:
    """Everything the Agents page shows about real use: per subagent type
    and per skill, how often it was called (all time and in the last
    `days`), what the subagent runs cost, and the most recent calls."""
    today = today or dt.date.today()
    cutoff = (today - dt.timedelta(days=days - 1)).isoformat()

    by_agent: dict[str, dict] = {}
    by_skill: dict[str, dict] = {}
    recent: list[dict] = []

    for inv in iter_invocations(root):
        table = by_agent if inv["kind"] == "agent" else by_skill
        row = table.setdefault(inv["name"], _empty_agent_row(inv["name"]))
        row["invocations"] += 1
        row["routes"][inv["route"]] += 1
        if inv["date"] >= cutoff:
            row["invocations_recent"] += 1
        row["last_used"] = max(row["last_used"], inv["date"])
        row["projects"].add(inv["project"])
        recent.append(inv)

    runs_total = 0
    runs_cost = 0.0
    for run in iter_subagent_runs(root):
        runs_total += 1
        runs_cost += run["cost_usd"]
        row = by_agent.setdefault(run["agent_type"], _empty_agent_row(run["agent_type"]))
        row["runs"] += 1
        row["turns"] += run["turns"]
        row["tokens"] += (run["input_tokens"] + run["output_tokens"]
                          + run["cache_read_input_tokens"] + run["cache_write_tokens"])
        row["cost_usd"] += run["cost_usd"]
        row["unpriced_tokens"] += run["unpriced_tokens"]
        row["projects"].add(run["project"])
        row["models"].update(run["models"])
        if run["end"] is not None:
            row["last_used"] = max(row["last_used"], run["end"].date().isoformat())

    def finish(table: dict) -> list[dict]:
        rows = []
        for r in table.values():
            r = dict(r)
            r["projects"] = sorted(r["projects"])
            r["models"] = sorted(r["models"])
            r["routes"] = dict(sorted(r["routes"].items()))
            rows.append(r)
        rows.sort(key=lambda r: (r["last_used"], r["invocations"]), reverse=True)
        return rows

    recent.sort(key=lambda r: r["when"], reverse=True)
    recent_out = []
    for r in recent[:25]:
        r = dict(r)
        r["when"] = r["when"].isoformat()
        recent_out.append(r)

    skill_calls_recent = sum(r["invocations_recent"] for r in by_skill.values())
    agent_calls_recent = sum(r["invocations_recent"] for r in by_agent.values())
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "days": days,
        "by_agent": finish(by_agent),
        "by_skill": finish(by_skill),
        "recent": recent_out,
        "totals": {
            "subagent_runs": runs_total,
            "subagent_cost_usd": runs_cost,
            "agent_calls_recent": agent_calls_recent,
            "skill_calls_recent": skill_calls_recent,
        },
    }
