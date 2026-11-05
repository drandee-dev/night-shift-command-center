"""Tests for the vault readers and the ledger refresher.

Run from the vault root:  python -m unittest discover -s _dashboard/tests
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import refresh_ledger  # noqa: E402
import vault  # noqa: E402

TODAY = dt.date(2026, 9, 14)


def write(root: pathlib.Path, rel: str, text: str) -> pathlib.Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class FakeVault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        write(self.root, "areas/a.md", "---\ntitle: A\nstatus: evergreen\ntags: [meta]\n---\nLinks to [[b]] and [[areas/tooling/x]].\n")
        write(self.root, "areas/b.md", "---\ntitle: B\nstatus: seed\n---\nNo links out.\n")
        write(self.root, "areas/tooling/x.md", (
            "---\ntitle: X\nkind: repo\nadoption: installed\nsource: https://github.com/o/x\n"
            "location: ~/.claude/skills-src/x\ninstalled_ref: aaaaaaa\nupstream_ref: bbbbbbb\nchecked: 2026-06-01\n"
            "update: git pull\ntags: [reference]\nstatus: evergreen\n---\nbody stays\n"
        ))
        write(self.root, "areas/tooling/README.md", "---\ntitle: R\n---\n")
        write(self.root, "templates/t.md", "---\nstatus: seed\n---\n")
        write(self.root, "_archive/old.md", "---\nstatus: seed\n---\n")
        write(self.root, "projects/repo/node_modules/pkg/README.md", "---\nstatus: seed\n---\n")
        write(self.root, "projects/repo/CLAUDE.md", "---\nstatus: seed\n---\n")
        write(self.root, "projects/repo.md", "---\ntitle: Repo\nstatus: growing\n---\n[[a]]\n")
        write(self.root, "_inbox/cap.md", "---\ntitle: cap\ntags: [idea]\n---\n")
        write(self.root, "daily/2026-09-13.md", (
            "---\ntitle: 2026-09-13\nstatus: seed\n---\n## Tasks\n\n- [ ] ship it\n- [x] done thing\n- [ ]\n\n"
            "## Sessions\n\n### 11:15 · second-brain <!-- s:abc -->\n\n> prompt\n\n### 19:34 · ai-job-search <!-- s:def -->\n"
        ))

    def tearDown(self):
        self.tmp.cleanup()

    def test_noise_and_skip_folders_are_excluded(self):
        names = {p.relative_to(self.root).as_posix() for p, _ in vault.iter_notes(self.root)}
        self.assertIn("areas/a.md", names)
        self.assertIn("projects/repo.md", names)
        self.assertNotIn("templates/t.md", names)
        self.assertNotIn("_archive/old.md", names)
        self.assertNotIn("projects/repo/CLAUDE.md", names)
        self.assertNotIn("projects/repo/node_modules/pkg/README.md", names)

    def test_backlinks_resolve_by_basename_and_path(self):
        rows = {r["name"]: r for r in vault.notes_panel(self.root, TODAY)}
        self.assertEqual(rows["b"]["links_in"], 1)
        self.assertEqual(rows["x"]["links_in"], 1)
        self.assertEqual(rows["a"]["links_in"], 1)  # from projects/repo.md
        self.assertTrue(rows["repo"]["orphan"])

    def test_tooling_drift(self):
        rows = vault.tooling_panel(self.root, TODAY)
        self.assertEqual(len(rows), 1)  # README has no kind
        self.assertEqual(rows[0]["drift"], "update")
        self.assertTrue(rows[0]["stale"])
        self.assertTrue(rows[0]["needs_action"])

    def test_stale_only_flags_notes_with_an_upstream(self):
        def note(name, adoption, upstream):
            write(self.root, f"areas/tooling/{name}.md", (
                f"---\ntitle: {name}\nkind: app\nadoption: {adoption}\ninstalled_ref: v1\n"
                f"upstream_ref: {upstream}\nchecked: 2026-01-01\n---\n"))
        note("local", "installed", "n/a")
        note("rejected", "rejected", "abc")
        note("tracked", "installed", "v1")
        rows = {r["name"]: r for r in vault.tooling_panel(self.root, TODAY)}
        self.assertFalse(rows["local"]["needs_action"])
        self.assertFalse(rows["rejected"]["needs_action"])
        self.assertTrue(rows["tracked"]["needs_action"])

    def test_drift_rules(self):
        self.assertEqual(vault._drift({"adoption": "proposed"}), "proposed")
        self.assertEqual(vault._drift({"adoption": "rejected"}), "rejected")
        self.assertEqual(vault._drift({"adoption": "installed", "upstream_ref": "n/a", "installed_ref": "x"}), "unchecked")
        self.assertEqual(vault._drift({"adoption": "installed", "upstream_ref": "abc", "installed_ref": "abc"}), "current")
        self.assertEqual(vault._drift({"adoption": "installed", "upstream_ref": "abc", "installed_ref": "abd"}), "update")

    def test_daily_sessions_and_tasks(self):
        days = vault.daily_panel(self.root, 14, TODAY)
        self.assertEqual(len(days), 1)
        d = days[0]
        self.assertEqual([s["project"] for s in d["sessions"]], ["second-brain", "ai-job-search"])
        self.assertEqual(d["open"], ["ship it"])
        self.assertEqual(d["done"], ["done thing"])
        self.assertEqual(vault.open_tasks(self.root, 30, TODAY), [{"date": "2026-09-13", "text": "ship it"}])

    def test_skills_panel_joins_ledger_by_location(self):
        write(self.root, "areas/tooling/reg.md", (
            "---\ntitle: reg\nkind: skill-pack\nadoption: installed\n"
            "location: \"the-jury and the-fool copied to ~/.claude/skills/{the-jury,the-fool}\"\n---\n"
        ))
        g = self.root / "global-skills"
        write(g, "the-jury/SKILL.md", "---\nname: the-jury\ndescription: Use when a decision needs a verdict. Spawns jurors.\n---\n")
        write(g, "the-jury/.skill-meta.json", "{}")
        write(g, "jury-notes/SKILL.md", "---\nname: jury-notes\ndescription: Not the jury.\n---\n")
        write(self.root, ".claude/skills/capture/SKILL.md", "---\nname: capture\ndescription: Capture a thought.\n---\n")
        rows = {r["name"]: r for r in vault.skills_panel(self.root, g, TODAY)}
        self.assertEqual(rows["the-jury"]["ledger"], "areas/tooling/reg")
        self.assertTrue(rows["the-jury"]["registry"])
        self.assertEqual(rows["the-jury"]["brief"], "Use when a decision needs a verdict")
        self.assertEqual(rows["jury-notes"]["ledger"], "")  # substring of a ledger token is not a match
        self.assertEqual(rows["capture"]["scope"], "vault")
        self.assertFalse(rows["capture"]["registry"])

    def test_loadable_skills_follow_override_precedence(self):
        g = self.root / "global-skills"
        for n in ("kept", "user-off", "local-on"):  # not "on": YAML reads a bare on as true
            write(g, f"{n}/SKILL.md", f"---\nname: {n}\ndescription: {n}.\n---\n")
        write(self.root, ".claude/skills/vault-off/SKILL.md", "---\nname: vault-off\ndescription: x.\n---\n")
        write(self.root, "user.json", '{"skillOverrides": {"user-off": "off", "local-on": "off"}}')
        write(self.root, ".claude/settings.local.json", '{"skillOverrides": {"vault-off": "off", "local-on": "on"}}')
        names = {r["name"] for r in vault.loadable_skills(self.root, g, self.root / "user.json")}
        self.assertEqual(names, {"kept", "local-on"})  # the vault's local settings win over the user's

    def test_ponytail_status_without_flag(self):
        self.assertEqual(vault.ponytail_status(self.root / "missing"), {"present": False, "mode": ""})
        write(self.root, "flag", "full\n")
        self.assertEqual(vault.ponytail_status(self.root / "flag"), {"present": True, "mode": "full"})

    def test_summary_counts(self):
        write(self.root, "daily/2026-W37-review.md", "---\ntitle: W37\nstatus: seed\n---\n")
        s = vault.summary(self.root, TODAY)
        self.assertEqual(s["inbox"], 1)
        # b.md plus the review draft; plain daily notes are seeds by design and
        # skipped, as in _vault-map.base "Needs attention".
        self.assertEqual(s["seeds"], 2)
        self.assertEqual(s["orphans"], 2)  # projects/repo.md and the review draft
        self.assertEqual(s["tooling_action"], 1)
        self.assertEqual(s["open_tasks"], 1)


class RefreshLedger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.note = write(self.root, "x.md", (
            "---\ntitle: X\nsource: https://github.com/o/x (MIT); also https://github.com/o/y\n"
            "location: ~/.claude/skills-src/x\ninstalled_ref: aaaaaaa\nupstream_ref: bbbbbbb\nchecked: 2026-06-01\n---\n"
            "body with upstream_ref: text that must not change\n"
        ))

    def tearDown(self):
        self.tmp.cleanup()

    def test_manual_refresh_bumps_checked_only(self):
        p = write(self.root, "m.md", "---\nsource: https://github.com/o/x\nrefresh: manual\ninstalled_ref: 1.0\nupstream_ref: v1\nchecked: 2026-01-01\n---\n")
        r = refresh_ledger.refresh_note(p, "2026-09-14", remote=lambda repo: "1111111", local=lambda n, root="skills-src": None)
        self.assertIsNone(r["error"])
        self.assertTrue(r["written"])
        self.assertEqual(
            p.read_text(encoding="utf-8"),
            "---\nsource: https://github.com/o/x\nrefresh: manual\ninstalled_ref: 1.0\nupstream_ref: v1\nchecked: 2026-09-14\n---\n",
        )

    def test_manual_refresh_unreachable_or_sourceless_is_untouched(self):
        for src, remote in (("https://github.com/o/x", lambda repo: None), ("written here", lambda repo: "1111111")):
            p = write(self.root, "m2.md", f"---\nsource: {src}\nrefresh: manual\nchecked: 2026-01-01\n---\n")
            before = p.read_text(encoding="utf-8")
            r = refresh_ledger.refresh_note(p, "2026-09-14", remote=remote, local=lambda n, root="skills-src": None)
            self.assertEqual(r["error"], "refresh: manual")
            self.assertEqual(p.read_text(encoding="utf-8"), before)

    def test_marketplace_clone_location_is_recognised(self):
        m = refresh_ledger.CLONE_RE.search("~/.claude/plugins/marketplaces/openai-codex (marketplace clone)")
        self.assertEqual((m.group(1), m.group(2)), ("plugins/marketplaces", "openai-codex"))
        m = refresh_ledger.CLONE_RE.search("~/.claude/skills-src/x")
        self.assertEqual((m.group(1), m.group(2)), ("skills-src", "x"))

    def test_rewrites_only_the_three_fields(self):
        remote = lambda repo: {"o/x": "1111111", "o/y": "2222222"}[repo]  # noqa: E731
        local = lambda name, root="skills-src": "3333333" if name == "x" else None  # noqa: E731
        r = refresh_ledger.refresh_note(self.note, "2026-09-14", remote=remote, local=local)
        self.assertIsNone(r["error"])
        self.assertTrue(r["written"])
        text = self.note.read_text(encoding="utf-8")
        self.assertIn("upstream_ref: 1111111 (x), 2222222 (y)\n", text)
        self.assertIn("installed_ref: 3333333\n", text)
        self.assertIn("checked: 2026-09-14\n", text)
        self.assertIn("body with upstream_ref: text that must not change", text)
        self.assertIn("source: https://github.com/o/x (MIT); also https://github.com/o/y\n", text)

    def test_remote_failure_writes_nothing(self):
        before = self.note.read_text(encoding="utf-8")
        r = refresh_ledger.refresh_note(self.note, "2026-09-14", remote=lambda repo: None, local=lambda n, root="skills-src": None)
        self.assertIn("ls-remote failed", r["error"])
        self.assertEqual(self.note.read_text(encoding="utf-8"), before)

    def test_dry_run_writes_nothing(self):
        before = self.note.read_text(encoding="utf-8")
        r = refresh_ledger.refresh_note(self.note, "2026-09-14", dry_run=True, remote=lambda repo: "1111111", local=lambda n, root="skills-src": None)
        self.assertIsNone(r["error"])
        self.assertFalse(r["written"])
        self.assertEqual(self.note.read_text(encoding="utf-8"), before)

    def test_no_github_source_is_skipped(self):
        p = write(self.root, "y.md", "---\nsource: written here\nupstream_ref: n/a\nchecked: 2026-01-01\n---\n")
        r = refresh_ledger.refresh_note(p, "2026-09-14", remote=lambda repo: "1111111", local=lambda n, root="skills-src": None)
        self.assertEqual(r["error"], "no github source")

    def test_plugin_key_reads_installed_sha(self):
        p = write(self.root, "p.md", "---\nsource: https://github.com/o/p\nlocation: user plugin (p@mkt marketplace)\ninstalled_ref: 1.0.0\nupstream_ref: aaaaaaa\nchecked: 2026-01-01\n---\n")
        seen = []
        plugin = lambda key: seen.append(key) or "9999999"  # noqa: E731
        r = refresh_ledger.refresh_note(p, "2026-09-14", remote=lambda repo: "1111111", local=lambda n, root="skills-src": None, plugin=plugin)
        self.assertEqual(seen, ["p@mkt"])
        self.assertIn("installed_ref: 9999999\n", p.read_text(encoding="utf-8"))

    def test_plugin_sha_reads_json(self):
        j = write(self.root, "ip.json", '{"plugins": {"p@mkt": [{"gitCommitSha": "0123456789abcdef"}]}}')
        self.assertEqual(refresh_ledger.plugin_sha("p@mkt", j), "0123456")
        self.assertIsNone(refresh_ledger.plugin_sha("q@mkt", j))
        self.assertIsNone(refresh_ledger.plugin_sha("p@mkt", self.root / "missing.json"))

    def test_rejected_is_skipped(self):
        p = write(self.root, "r.md", "---\nsource: https://github.com/o/x\nadoption: rejected\nupstream_ref: a\nchecked: 2026-01-01\n---\n")
        before = p.read_text(encoding="utf-8")
        r = refresh_ledger.refresh_note(p, "2026-09-14", remote=lambda repo: "1111111", local=lambda n, root="skills-src": None)
        self.assertEqual(r["error"], "adoption: rejected")
        self.assertEqual(p.read_text(encoding="utf-8"), before)

    def test_github_regex_strips_tree_paths(self):
        found = refresh_ledger.GITHUB_RE.findall("https://github.com/anthropics/claude-code/tree/main/plugins/plugin-dev")
        self.assertEqual(found, ["anthropics/claude-code"])


TRACKER_HEADER = "date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,cv_file,cover_letter_file,source,deadline\n"


class JobsPanel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = pathlib.Path(self.tmp.name) / "tracker.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def panel(self, *rows: str) -> dict:
        self.csv.write_text(TRACKER_HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
        return vault.jobs_panel(self.csv, TODAY)

    def card(self, p: dict, company: str) -> dict:
        return next(c for col in p["columns"] for c in col["cards"] if c["company"] == company)

    def test_quiet_applied_row_is_due(self):
        p = self.panel("2026-09-01,Acme,,Analyst,,portal,applied,,70,sent,,,https://x.test/1,")
        self.assertEqual([c["company"] for c in p["due"]], ["Acme"])
        self.assertEqual(p["due"][0]["quiet"], 13)

    def test_dated_note_resets_the_quiet_clock(self):
        p = self.panel("2026-09-01,Acme,,Analyst,,portal,applied,,70,recruiter replied 2026-09-10,,,,")
        self.assertEqual(self.card(p, "Acme")["quiet"], 4)
        self.assertEqual(p["due"], [])

    def test_future_date_in_notes_is_not_activity(self):
        p = self.panel("2026-09-01,Acme,,Analyst,,portal,applied,,70,closes 2026-12-01,,,,")
        self.assertEqual(self.card(p, "Acme")["quiet"], 13)

    def test_two_followups_stop_the_nudge(self):
        p = self.panel("2026-08-01,Acme,,Analyst,,portal,applied,,70,followed up 2026-08-12 - followed up 2026-08-25,,,,")
        self.assertEqual(self.card(p, "Acme")["followups"], 2)
        self.assertEqual(p["due"], [])

    def test_drafted_and_final_rows_are_never_due(self):
        p = self.panel(
            "2026-08-01,Draft Co,,Analyst,,portal,drafted,,70,,,,,",
            "2026-08-01,Gone Co,,Analyst,,portal,no response,,70,,,,,",
        )
        self.assertEqual(p["due"], [])
        gone = self.card(p, "Gone Co")
        self.assertEqual((gone["status"], gone["column"]), ("no_response", "closed"))

    def test_columns_follow_the_status_vocabulary(self):
        p = self.panel(
            "2026-09-10,A,,r,,portal,interview,,,,,,,",
            "2026-09-10,B,,r,,portal,hired,,,,,,,",
            "2026-09-10,C,,r,,portal,mystery,,,,,,,",
        )
        cols = {col["key"]: [c["company"] for c in col["cards"]] for col in p["columns"]}
        self.assertEqual((cols["interview"], cols["offer"]), (["A"], ["B"]))
        # Unrecognised is open per /outcome, so it sits with the open applications.
        self.assertEqual(cols["applied"], ["C"])

    def test_empty_status_is_open_and_can_be_due(self):
        p = self.panel("2026-09-01,Blank,,r,,portal,,,,,,,,")
        c = self.card(p, "Blank")
        self.assertEqual((c["column"], c["due"]), ("applied", True))

    def test_legacy_offer_declined_spelling_is_final(self):
        p = self.panel("2026-08-01,Declined Co,,r,,portal,offer declined,,,,,,,")
        c = self.card(p, "Declined Co")
        self.assertEqual((c["status"], c["column"], c["due"]), ("offer_declined", "closed", False))

    def test_byte_order_mark_does_not_hide_dates(self):
        self.csv.write_text("﻿" + TRACKER_HEADER + "2026-09-01,Acme,,r,,portal,applied,,,,,,,\n", encoding="utf-8")
        p = vault.jobs_panel(self.csv, TODAY)
        self.assertEqual(p["undated"], [])
        self.assertEqual([c["company"] for c in p["due"]], ["Acme"])

    def test_surplus_fields_mark_the_row_shifted(self):
        p = self.panel("2026-09-10,Keeper,,r,,portal,applied,,59,notes,cv.pdf,cl.pdf,https://x.test/2,documents/x,2026-09-30")
        self.assertTrue(self.card(p, "Keeper")["shifted"])
        self.assertEqual([c["company"] for c in p["shifted"]], ["Keeper"])

    def test_legacy_thirteen_field_row_reads_clean(self):
        p = self.panel("2026-09-10,Old,,r,,portal,applied,,Strong,n,,,https://x.test/3")
        c = self.card(p, "Old")
        self.assertFalse(c["shifted"])
        self.assertIsNone(c["deadline"])
        self.assertEqual(c["url"], "https://x.test/3")

    def test_only_http_sources_become_links(self):
        p = self.panel("2026-09-10,Evil,,r,,portal,applied,,,,,,javascript:alert(1),")
        self.assertEqual(self.card(p, "Evil")["url"], "")

    def test_weekly_counts_skip_drafts(self):
        p = self.panel(
            "2026-09-14,A,,r,,portal,applied,,,,,,,",
            "2026-09-08,B,,r,,portal,rejected,,,,,,,",
            "2026-09-14,C,,r,,portal,drafted,,,,,,,",
        )
        self.assertEqual([w["n"] for w in p["weeks"]][-2:], [1, 1])
        self.assertEqual(p["sent"], 2)

    def test_missing_tracker_is_reported_not_raised(self):
        self.assertFalse(vault.jobs_panel(pathlib.Path(self.tmp.name) / "nope.csv", TODAY)["found"])


if __name__ == "__main__":
    unittest.main()
