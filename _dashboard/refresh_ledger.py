"""Refresh the tooling ledger's upstream and installed refs.

    python _dashboard/refresh_ledger.py            # rewrite areas/tooling/*.md
    python _dashboard/refresh_ledger.py --dry-run  # report only

For every note in areas/tooling with a GitHub URL in `source:`, asks the
remote for its HEAD commit (`git ls-remote`, no clone) and writes the short
sha into `upstream_ref:`. If `location:` names a clone under
~/.claude/skills-src, reads that clone's HEAD into `installed_ref:`. Sets
`checked:` to today on every note it touched. Only those three lines are
ever rewritten; every other byte of the note is left alone, and each
rewrite is asserted rather than assumed. A note with `refresh: manual` in
its frontmatter is for things whose installed ref is a version rather than a
commit (plugins installed from a marketplace): refs are left alone, and only
`checked` is bumped when every GitHub source answers. A manual note with no
GitHub source is skipped, since there is nothing to reach.

Never raises out of main(): a remote that does not answer is reported per
note and the rest continue. Exit code is 0 unless nothing could be read at
all.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

VAULT = pathlib.Path(__file__).resolve().parent.parent
TOOLING = VAULT / "areas" / "tooling"
SKILLS_SRC = pathlib.Path.home() / ".claude" / "skills-src"

GITHUB_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:/tree/[^\s,;)]*)?(?=[\s,;)]|$)")
# A local git clone the installed_ref can be read from: a skills-src clone or
# a plugin marketplace clone. Both are git repos under ~/.claude.
CLONE_RE = re.compile(r"~/\.claude/(skills-src|plugins/marketplaces)/([A-Za-z0-9_.-]+)")
CLONE_ROOTS = {
    "skills-src": pathlib.Path.home() / ".claude" / "skills-src",
    "plugins/marketplaces": pathlib.Path.home() / ".claude" / "plugins" / "marketplaces",
}
FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
# A plugin key such as ponytail@ponytail, looked up in installed_plugins.json.
PLUGIN_RE = re.compile(r"\b([A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+)")
INSTALLED_PLUGINS = pathlib.Path.home() / ".claude" / "plugins" / "installed_plugins.json"

# Properties this script may rewrite, and nothing else.
FIELDS = ("upstream_ref", "installed_ref", "checked")


def ls_remote(repo: str, timeout: int = 25) -> str | None:
    url = f"https://github.com/{repo}"
    try:
        out = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return out.stdout.split()[0][:7]


def clone_head(name: str, root: str = "skills-src") -> str | None:
    path = CLONE_ROOTS.get(root, SKILLS_SRC) / name
    if not (path / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short=7", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return out.stdout.strip() or None


def plugin_sha(key: str, path: pathlib.Path = INSTALLED_PLUGINS) -> str | None:
    """The commit a plugin was installed from, as Claude Code recorded it."""
    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("plugins", {}).get(key, [])
        return entries[0]["gitCommitSha"][:7]
    except (OSError, ValueError, LookupError, TypeError):
        return None


def set_field(text: str, field: str, value: str) -> tuple[str, bool]:
    """Replace `field: ...` inside the frontmatter only. Returns (text, changed)."""
    match = FM_RE.match(text)
    if not match:
        return text, False
    fm = match.group(1)
    line_re = re.compile(rf"^{field}:.*$", re.M)
    if not line_re.search(fm):
        return text, False
    new_fm = line_re.sub(f"{field}: {value}", fm, count=1)
    if new_fm == fm:
        return text, False
    return text[: match.start(1)] + new_fm + text[match.end(1):], True


def field_value(text: str, field: str) -> str:
    match = FM_RE.match(text)
    if not match:
        return ""
    m = re.search(rf"^{field}:\s*(.*)$", match.group(1), re.M)
    return m.group(1).strip() if m else ""


def refresh_note(path: pathlib.Path, today: str, dry_run: bool = False, remote=ls_remote, local=clone_head, plugin=plugin_sha) -> dict:
    text = path.read_text(encoding="utf-8")
    source = field_value(text, "source")
    location = field_value(text, "location")
    report = {"note": path.stem, "upstream": None, "installed": None, "written": False, "error": None}

    if field_value(text, "refresh") == "manual":
        # Installed ref is a version, not a commit, so refs are never compared
        # here. If every GitHub source still answers, bump `checked` alone:
        # it then means "the remote was reached", not "refs were compared".
        repos = GITHUB_RE.findall(source)
        if not repos or any(remote(r) is None for r in repos):
            report["error"] = "refresh: manual"
            return report
        report["upstream"] = "not compared (manual)"
        new_text, changed = set_field(text, "checked", today)
        if not changed and field_value(text, "checked") != today:
            report["error"] = "checked line missing; not written"
            return report
        if not dry_run and new_text != text:
            path.write_text(new_text, encoding="utf-8")
            if field_value(path.read_text(encoding="utf-8"), "checked") != today:
                report["error"] = "write did not land"
                return report
            report["written"] = True
        return report
    if field_value(text, "adoption") == "rejected":
        report["error"] = "adoption: rejected"
        return report

    repos = GITHUB_RE.findall(source)
    if not repos:
        report["error"] = "no github source"
        return report

    shas = []
    for repo in repos:
        sha = remote(repo)
        if sha is None:
            report["error"] = f"ls-remote failed for {repo}"
            return report
        shas.append((repo, sha))
    upstream = shas[0][1] if len(shas) == 1 else ", ".join(f"{s} ({r.split('/')[-1]})" for r, s in shas)
    report["upstream"] = upstream

    clone = CLONE_RE.search(location)
    key = PLUGIN_RE.search(location)
    installed = plugin(key.group(1)) if key else None
    if installed is None and clone:
        installed = local(clone.group(2), clone.group(1))
    report["installed"] = installed

    new_text, changed_up = set_field(text, "upstream_ref", upstream)
    if not changed_up and field_value(text, "upstream_ref") != upstream:
        report["error"] = "upstream_ref line missing; not written"
        return report
    changed_inst = False
    if installed:
        new_text, changed_inst = set_field(new_text, "installed_ref", installed)
    new_text, changed_checked = set_field(new_text, "checked", today)
    if not changed_checked and field_value(text, "checked") != today:
        report["error"] = "checked line missing; not written"
        return report

    if dry_run:
        return report
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        # Assert the write took.
        back = path.read_text(encoding="utf-8")
        if field_value(back, "upstream_ref") != upstream or field_value(back, "checked") != today:
            report["error"] = "write did not land"
            return report
        report["written"] = True
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--folder", default=str(TOOLING))
    args = parser.parse_args(argv)
    folder = pathlib.Path(args.folder)
    today = dt.date.today().isoformat()
    notes = sorted(p for p in folder.glob("*.md") if p.name != "README.md")
    if not notes:
        print(f"no notes in {folder}", file=sys.stderr)
        return 1
    ok = 0
    for path in notes:
        r = refresh_note(path, today, args.dry_run)
        if r["error"]:
            print(f"skip   {r['note']}: {r['error']}")
            continue
        ok += 1
        flag = "dry   " if args.dry_run else ("wrote " if r["written"] else "same  ")
        inst = f" installed={r['installed']}" if r["installed"] else ""
        print(f"{flag} {r['note']}: upstream={r['upstream']}{inst}")
    print(f"{ok}/{len(notes)} notes refreshed {today}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
