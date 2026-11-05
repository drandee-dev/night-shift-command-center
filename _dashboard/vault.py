"""Read-only view of the vault for the dashboard.

Everything here reads markdown and YAML off disk and returns plain dicts.
Nothing writes, nothing calls a model, nothing touches the network except
`fleet_status`, which does one localhost GET with a one-second timeout.

Paths are parameters, not globals, so the tests can point every function at
a throwaway vault.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import re
import urllib.request

import yaml

VAULT = pathlib.Path(__file__).resolve().parent.parent
HOME = pathlib.Path.home()
AGENTS_DIR = HOME / ".claude" / "agents" / "howlers"
INSTALLED_PLUGINS = HOME / ".claude" / "plugins" / "installed_plugins.json"
SKILLS_GLOBAL = HOME / ".claude" / "skills"
PONYTAIL_FLAG = HOME / ".claude" / ".ponytail-active"

# Folders that hold vendored or tool-owned files, never notes.
NOISE = ("node_modules", ".venv", "site-packages", ".agents", ".codex", ".claude", ".git", ".obsidian", ".smart-env")
SKIP_TOP = ("templates", "_archive", "_dashboard")

FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.S)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
TASK_RE = re.compile(r"^\s*- \[( |x|X)\] (.+?)\s*$", re.M)
SESSION_RE = re.compile(r"^### (\d\d:\d\d) · ([^<\n]+?)\s*(?:<!--.*?-->)?\s*$", re.M)


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------

def read_frontmatter(path: pathlib.Path) -> dict:
    """Return the YAML frontmatter of a note as a dict, or {} if none or broken."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_noise(path: pathlib.Path, vault: pathlib.Path) -> bool:
    rel = path.relative_to(vault)
    parts = rel.parts
    if any(p in NOISE for p in parts):
        return True
    if parts[0] in SKIP_TOP:
        return True
    # projects/<repo>/... are code repos; only projects/*.md companion notes count.
    if parts[0] == "projects" and len(parts) > 2:
        return True
    return False


def iter_notes(vault: pathlib.Path = VAULT):
    """Yield (path, frontmatter) for every vault note that is not noise."""
    for path in sorted(vault.rglob("*.md")):
        if _is_noise(path, vault):
            continue
        yield path, read_frontmatter(path)


def _as_date(value) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _days_since(value, today: dt.date) -> int | None:
    d = _as_date(value)
    return (today - d).days if d else None


def _mtime_days(path: pathlib.Path, today: dt.date) -> int:
    m = dt.datetime.fromtimestamp(path.stat().st_mtime).date()
    return (today - m).days


# --------------------------------------------------------------------------
# Links
# --------------------------------------------------------------------------

def link_index(vault: pathlib.Path = VAULT) -> dict[str, set[str]]:
    """Map each note (relative path without .md, lowercased) to the set of
    notes that link to it. Links are resolved by full relative path first,
    then by basename, which is how Obsidian resolves an unqualified link."""
    notes = list(iter_notes(vault))
    by_rel = {}
    by_base: dict[str, list[str]] = {}
    for path, _ in notes:
        rel = path.relative_to(vault).with_suffix("").as_posix().lower()
        by_rel[rel] = rel
        by_base.setdefault(path.stem.lower(), []).append(rel)
    incoming: dict[str, set[str]] = {rel: set() for rel in by_rel}
    for path, _ in notes:
        src = path.relative_to(vault).with_suffix("").as_posix().lower()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip().lower()
            if target.endswith(".md"):
                target = target[:-3]
            if target in by_rel:
                incoming[target].add(src)
            else:
                for rel in by_base.get(target.rsplit("/", 1)[-1], []):
                    incoming[rel].add(src)
    return incoming


# --------------------------------------------------------------------------
# Panels
# --------------------------------------------------------------------------

def notes_panel(vault: pathlib.Path = VAULT, today: dt.date | None = None) -> list[dict]:
    """Every note with a `status` property, like _vault-map.base."""
    today = today or dt.date.today()
    incoming = link_index(vault)
    rows = []
    for path, fm in iter_notes(vault):
        if "status" not in fm:
            continue
        rel = path.relative_to(vault).with_suffix("").as_posix()
        # Daily notes stay `seed` by design; only weekly-review drafts need attention.
        journal = rel.startswith("daily/") and "-review" not in path.stem
        rows.append({
            "name": path.stem,
            "rel": rel,
            "folder": rel.rsplit("/", 1)[0] if "/" in rel else "",
            "status": str(fm.get("status", "")),
            "tags": [str(t) for t in (fm.get("tags") or [])],
            "date": str(fm.get("date", "")),
            "idle_days": _mtime_days(path, today),
            "links_in": len(incoming.get(rel.lower(), ())),
            "orphan": len(incoming.get(rel.lower(), ())) == 0,
            "journal": journal,
        })
    rows.sort(key=lambda r: (r["folder"], r["name"].lower()))
    return rows


def inbox_panel(vault: pathlib.Path = VAULT, today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    rows = []
    inbox = vault / "_inbox"
    if not inbox.exists():
        return rows
    for path in sorted(inbox.glob("*.md")):
        fm = read_frontmatter(path)
        created = dt.datetime.fromtimestamp(path.stat().st_ctime).date()
        waiting = (today - created).days
        rows.append({
            "name": path.stem,
            "waiting": waiting,
            "heat": "stale" if waiting > 14 else "aging" if waiting > 3 else "fresh",
            "tags": [str(t) for t in (fm.get("tags") or [])],
            "source": str(fm.get("source", "")),
        })
    rows.sort(key=lambda r: -r["waiting"])
    return rows


def daily_panel(vault: pathlib.Path = VAULT, days: int = 14, today: dt.date | None = None) -> list[dict]:
    """The last N daily notes with their logged sessions and tasks."""
    today = today or dt.date.today()
    rows = []
    daily = vault / "daily"
    if not daily.exists():
        return rows
    for path in sorted(daily.glob("????-??-??.md"), reverse=True):
        d = _as_date(path.stem)
        if d is None or (today - d).days > days:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        sessions = [{"time": m.group(1), "project": m.group(2).strip()} for m in SESSION_RE.finditer(text)]
        tasks = [{"done": m.group(1).lower() == "x", "text": m.group(2)} for m in TASK_RE.finditer(text)]
        tasks = [t for t in tasks if t["text"].strip()]
        rows.append({
            "date": path.stem,
            "weekday": d.strftime("%a"),
            "sessions": sessions,
            "open": [t["text"] for t in tasks if not t["done"]],
            "done": [t["text"] for t in tasks if t["done"]],
        })
    return rows


def open_tasks(vault: pathlib.Path = VAULT, days: int = 30, today: dt.date | None = None) -> list[dict]:
    out = []
    for day in daily_panel(vault, days, today):
        for t in day["open"]:
            out.append({"date": day["date"], "text": t})
    return out


def _drift(row: dict) -> str:
    adoption = str(row.get("adoption", ""))
    if adoption == "proposed":
        return "proposed"
    if adoption == "rejected":
        return "rejected"
    up = str(row.get("upstream_ref", "") or "").strip()
    inst = str(row.get("installed_ref", "") or "").strip()
    if not up or up.lower() in ("n/a", "unchecked", "none"):
        return "unchecked"
    if up != inst:
        return "update"
    return "current"


def tooling_panel(vault: pathlib.Path = VAULT, today: dt.date | None = None) -> list[dict]:
    """One row per areas/tooling note, with the same drift rule as _tooling.base."""
    today = today or dt.date.today()
    rows = []
    folder = vault / "areas" / "tooling"
    if not folder.exists():
        return rows
    for path in sorted(folder.glob("*.md")):
        fm = read_frontmatter(path)
        if "kind" not in fm:
            continue
        checked_days = _days_since(fm.get("checked"), today)
        row = {
            "name": path.stem,
            "title": str(fm.get("title", path.stem)),
            "kind": str(fm.get("kind", "")),
            "adoption": str(fm.get("adoption", "")),
            "source": str(fm.get("source", "")),
            "location": str(fm.get("location", "")),
            "installed_ref": str(fm.get("installed_ref", "") or ""),
            "upstream_ref": str(fm.get("upstream_ref", "") or ""),
            "checked": str(fm.get("checked", "") or ""),
            "checked_days": checked_days,
            "stale": checked_days is None or checked_days > 30,
            "update": str(fm.get("update", "")),
        }
        row["drift"] = _drift(row)
        # Staleness only counts for a note that tracks an upstream (drift
        # "current"); written-here and rejected notes have nothing to recheck.
        row["needs_action"] = row["drift"] in ("proposed", "update") or (row["stale"] and row["drift"] == "current")
        rows.append(row)
    rows.sort(key=lambda r: (r["kind"], r["name"]))
    return rows


def agents_panel(agents_dir: pathlib.Path = AGENTS_DIR, crew_dir: pathlib.Path | None = None) -> list[dict]:
    """The Howler subagents, joined to their crew yaml when it exists."""
    crew_dir = crew_dir or (VAULT / "projects" / "agentic-fleet" / "crew")
    rows = []
    if not agents_dir.exists():
        return rows
    for path in sorted(agents_dir.glob("*.md")):
        fm = read_frontmatter(path)
        name = str(fm.get("name", path.stem))
        crew = {}
        crew_path = crew_dir / f"{name}.yaml"
        if crew_path.exists():
            try:
                crew = yaml.safe_load(crew_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                crew = {}
        rows.append({
            "name": name,
            "description": str(fm.get("description", "")),
            "model": str(fm.get("model", "inherit")),
            "tools": str(fm.get("tools", "all")),
            "crew_title": str(crew.get("title", "")),
            "crew_enabled": bool(crew.get("enabled", False)),
            "crew_tier": str((crew.get("model") or {}).get("tier", "")),
            "crew_file": str(crew_path.relative_to(VAULT)) if crew_path.exists() else "",
        })
    return rows


def plugins_panel(installed: pathlib.Path = INSTALLED_PLUGINS) -> list[dict]:
    rows = []
    try:
        data = json.loads(installed.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return rows
    for key, entries in (data.get("plugins") or {}).items():
        for e in entries or []:
            rows.append({
                "name": key,
                "version": str(e.get("version", "")),
                "scope": str(e.get("scope", "")),
                "installed": str(e.get("installedAt", ""))[:10],
                "updated": str(e.get("lastUpdated", ""))[:10],
            })
    return rows


def _ledger_locations(vault: pathlib.Path) -> list[tuple[str, str]]:
    """(note rel path, lowercased `location` field) for every tooling note."""
    out = []
    folder = vault / "areas" / "tooling"
    if not folder.exists():
        return out
    for path in sorted(folder.glob("*.md")):
        fm = read_frontmatter(path)
        if "kind" not in fm:
            continue
        out.append((path.relative_to(vault).with_suffix("").as_posix(), str(fm.get("location", "")).lower()))
    return out


def skills_panel(vault: pathlib.Path = VAULT, global_dir: pathlib.Path = SKILLS_GLOBAL,
                 today: dt.date | None = None) -> list[dict]:
    """Every SKILL.md Claude Code can load here: the global folder and this
    vault's own, each joined to the tooling note whose `location` names it."""
    today = today or dt.date.today()
    ledger = _ledger_locations(vault)
    rows = []
    for scope, folder in (("global", global_dir), ("vault", vault / ".claude" / "skills")):
        if not folder.exists():
            continue
        for skill_md in sorted(folder.glob("*/SKILL.md")):
            folder_name = skill_md.parent.name
            fm = read_frontmatter(skill_md)
            desc = " ".join(str(fm.get("description", "")).split())
            pattern = re.compile(r"(?<![\w-])" + re.escape(folder_name.lower()) + r"(?![\w-])")
            note = next((rel for rel, loc in ledger if pattern.search(loc)), "")
            rows.append({
                "name": str(fm.get("name", folder_name)),
                "folder": folder_name,
                "scope": scope,
                "brief": desc.split(". ")[0][:160],
                "registry": (skill_md.parent / ".skill-meta.json").exists(),
                "idle_days": _mtime_days(skill_md, today),
                "ledger": note,
            })
    rows.sort(key=lambda r: (r["scope"], r["name"].lower()))
    return rows


def _overrides(path: pathlib.Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("skillOverrides") or {}
    except (OSError, ValueError, AttributeError):
        return {}


def loadable_skills(vault: pathlib.Path = VAULT, global_dir: pathlib.Path = SKILLS_GLOBAL,
                    user_settings: pathlib.Path = HOME / ".claude" / "settings.json") -> list[dict]:
    """The skills_panel rows a session at the vault root can load: an "off" override drops a skill, with the
    vault's settings.local.json over its settings.json over the user's settings (Claude Code's precedence)."""
    merged = {**_overrides(user_settings), **_overrides(vault / ".claude" / "settings.json"),
              **_overrides(vault / ".claude" / "settings.local.json")}
    return [r for r in skills_panel(vault, global_dir) if merged.get(r["name"], merged.get(r["folder"])) != "off"]


JOB_TRACKER = VAULT / "projects" / "ai-job-search" / "job_search_tracker.csv"
# Board columns, in pipeline order. The vocabulary is /outcome's "Tracker status
# vocabulary"; legacy space spellings are read as their underscore forms.
JOB_COLUMNS = (("drafted", "Drafted"), ("applied", "Applied"), ("interview", "Interview"),
               ("offer", "Offer / hired"), ("closed", "Closed"))
JOB_FINAL = {"hired", "rejected", "no_response", "offer_declined", "withdrawn"}
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
FOLLOWED_UP_RE = re.compile(r"followed up \d{4}-\d{2}-\d{2}", re.I)


def _job_column(status: str) -> str:
    if status in ("drafted", "interview"):
        return status
    if status in ("offer", "hired"):
        return "offer"
    if status in JOB_FINAL:
        return "closed"
    # /outcome: "a row is active until its status is one of the Final values", so
    # an empty or unrecognised status is open. It shows with its raw status badge.
    return "applied"


def jobs_panel(tracker: pathlib.Path = JOB_TRACKER, today: dt.date | None = None,
               quiet_after: int = 10, weeks: int = 8) -> dict:
    """The job-search tracker as a board. Re-read on every call, so the page is
    as current as the CSV that /apply and /outcome write.

    Follow-up rule is /outcome Step 2b's: a sent, open application whose last
    activity (its date, or the latest past date in its notes) is `quiet_after`
    or more days ago, with fewer than two `followed up` markers."""
    today = today or dt.date.today()
    try:
        # utf-8-sig: Excel's "CSV UTF-8" adds a BOM, which would rename the first
        # column and leave every row undated.
        with tracker.open(encoding="utf-8-sig", newline="") as f:
            raw = list(csv.DictReader(f))
    except (OSError, UnicodeDecodeError, csv.Error):
        return {"found": False, "path": str(tracker)}

    cards = []
    for r in raw:
        def get(key: str, row: dict = r) -> str:  # short rows read as empty
            return (row.get(key) or "").strip()
        status = get("status").lower().replace(" ", "_")
        notes = get("notes")
        applied = _as_date(get("date"))
        activity = [d for d in (_as_date(m) for m in ISO_DATE_RE.findall(notes)) if d and d <= today]
        last = max([applied, *activity]) if applied else None
        quiet = (today - last).days if last else None
        followups = len(FOLLOWED_UP_RE.findall(notes))
        source = get("source")
        cards.append({
            "company": get("company"), "role": get("role"), "status": status,
            "column": _job_column(status), "date": applied, "fit": get("fit_rating"),
            "deadline": _as_date(get("deadline")) if ISO_DATE_RE.fullmatch(get("deadline")) else None,
            "url": source if source.startswith(("https://", "http://")) else "",
            "quiet": quiet, "followups": followups,
            "due": (status != "drafted" and status not in JOB_FINAL and quiet is not None
                    and quiet >= quiet_after and followups < 2),
            # DictReader files surplus fields under None: a comma that escaped the notes
            # quoting shifts every column after it, so say so rather than trust them.
            "shifted": None in r,
        })
    cards.sort(key=lambda c: (c["date"] or dt.date.min, c["company"].lower()), reverse=True)

    monday = today - dt.timedelta(days=today.weekday())
    starts = [monday - dt.timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    sent = [c for c in cards if c["status"] != "drafted" and c["date"]]
    per_week = [{"start": s, "n": sum(1 for c in sent if s <= c["date"] < s + dt.timedelta(days=7))} for s in starts]

    return {
        "found": True,
        "path": str(tracker),
        "columns": [{"key": k, "label": label, "cards": [c for c in cards if c["column"] == k]}
                    for k, label in JOB_COLUMNS],
        "due": sorted((c for c in cards if c["due"]), key=lambda c: -c["quiet"]),
        "undated": [c for c in cards if c["date"] is None],
        "shifted": [c for c in cards if c["shifted"]],
        "sent": len(sent),
        "weeks": per_week,
        "week_max": max((w["n"] for w in per_week), default=0),
        "quiet_after": quiet_after,
    }


def ponytail_status(flag: pathlib.Path = PONYTAIL_FLAG) -> dict:
    """The ponytail plugin writes its active mode to a flag file on first
    prompt; before that the plugin is installed but has not announced itself."""
    try:
        text = flag.read_text(encoding="utf-8").strip()
    except OSError:
        return {"present": False, "mode": ""}
    return {"present": True, "mode": text[:40]}


def fleet_status(url: str = "http://127.0.0.1:8787/") -> dict:
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310 (localhost only)
            return {"up": resp.status == 200, "url": url}
    except Exception:  # noqa: BLE001 - any failure means "down" for a status light
        return {"up": False, "url": url}


def summary(vault: pathlib.Path = VAULT, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    notes = notes_panel(vault, today)
    inbox = inbox_panel(vault, today)
    tooling = tooling_panel(vault, today)
    tasks = open_tasks(vault, 30, today)
    return {
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes_total": len(notes),
        "seeds": sum(1 for n in notes if n["status"] == "seed" and not n["journal"]),
        "orphans": sum(1 for n in notes if n["orphan"] and not n["journal"]),
        "inbox": len(inbox),
        "inbox_stale": sum(1 for i in inbox if i["heat"] == "stale"),
        "open_tasks": len(tasks),
        "tooling_total": len(tooling),
        "tooling_action": sum(1 for t in tooling if t["needs_action"]),
        "fleet": fleet_status(),
    }
