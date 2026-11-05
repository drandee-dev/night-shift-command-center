---
title: Night Shift
date: 2026-11-02
tags: [meta]
status: seed
cssclasses:
  - night-shift
---

```dataviewjs
// Night Shift dashboard (projects/night-shift.md). Scene: Blender, scripts/night_shift_looks.py (look d) and
// scripts/night_shift_spots.py (hotspot masks and boxes). Read-only over the vault.
const root = dv.container.createDiv({ cls: "ns" })
// Style tags are global in Obsidian: one stylesheet by id, replaced on every render.
document.getElementById("ns-style")?.remove()
document.head.createEl("style", { attr: { id: "ns-style" } }).textContent = `
@import url('https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;600&family=Atkinson+Hyperlegible:wght@400;700&family=Atkinson+Hyperlegible+Next:wght@400;600;700&family=Silkscreen&display=swap');
.night-shift { --file-line-width: 100%; }
.night-shift .metadata-container, .night-shift .inline-title { display: none !important; }
/* panel visual pass (projects/night-shift-control-room.md, 2026-11-05): --edge-strong is 3.1:1 on --panel, the floor for a
   control's edge (WCAG 1.4.11); --edge stays for decorative dividers. Titles Pixelify Sans, numbers Silkscreen. */
.ns { --night:#0e0a18; --panel:#1d1830; --raised:#262043; --edge:#2b2946; --edge-strong:#67648f; --ink:#c9d2bf; --dim:#7f9cab;
  --cyan:#5ff4ff; --pink:#ff4fb4; --amber:#ffb85c; --green:#6dff8a; --num: "Silkscreen", "Pixelify Sans", monospace;
  container: ns / inline-size; color: var(--ink); background: var(--night);
  font: 15px/1.45 "Atkinson Hyperlegible Next", "Atkinson Hyperlegible", system-ui, sans-serif; }
.ns-stage { position: relative; }
.ns-scene { position: relative; }
.ns-scene img { display: block; width: 100%; height: auto; max-width: none; margin: 0; border-radius: 0; }
/* hover highlight: the scene brightened through the object's own mask; the glow sits on an outer
   element because CSS applies filter before mask on the same element */
.ns-glow { position: absolute; inset: 0; pointer-events: none; opacity: 0; filter: drop-shadow(0 0 2px var(--gc, var(--cyan))) drop-shadow(0 0 7px var(--gc, var(--cyan))); }
.ns-glow.on, .ns-glow[data-st] { opacity: 1; }
/* run state from the dashboard server: cyan pulse running, pink failed, green for a few seconds after success */
.ns-glow[data-st="running"] { --gc: var(--cyan); }
.ns-glow[data-st="failed"] { --gc: var(--pink); }
.ns-glow[data-st="ok"] { --gc: #6dff8a; }
@media (prefers-reduced-motion: no-preference) { .ns-glow[data-st="running"] { animation: ns-pulse 1.4s ease-in-out infinite; } }
@keyframes ns-pulse { 50% { opacity: .35; } }
.ns-glow > div { position: absolute; inset: 0; background-size: 100% 100%; mask-size: 100% 100%; -webkit-mask-size: 100% 100%; filter: brightness(1.35) saturate(1.25); }
.ns-drawer, .ns-toast { z-index: 20; }
.ns-scene video.ns-rain, .ns-scene video.ns-loop { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; margin: 0; }
.ns-scene video.ns-rain { image-rendering: pixelated; mix-blend-mode: screen; }
.ns-scene video.ns-rain[hidden], .ns-scene video.ns-loop[hidden] { display: none; }
.ns button.ns-rain-toggle { position: absolute; left: 8px; bottom: 8px; z-index: 20; padding: 3px 10px; font-size: 13px;
  background: #0e0a18cc; color: var(--ink); border: 1px solid var(--edge-strong); }
.ns-corner { position: absolute; left: 8px; bottom: 8px; z-index: 20; display: flex; gap: 6px; }
.ns-corner[hidden] { display: none; }
.ns .ns-corner button.ns-rain-toggle { position: static; }
.ns button.ns-rain-toggle:hover, .ns button.ns-rain-toggle:focus-visible { border-color: var(--cyan); outline: none; }
/* .ns button.x beats Obsidian's button:not(.clickable-icon) */
.ns button { font: inherit; border-radius: 0; box-shadow: none; height: auto; cursor: pointer; }
.ns button.ns-spot { position: absolute; padding: 0; background: transparent; border: 1px dashed transparent; }
/* a click area of at least 24 x 24 px around small objects (WCAG 2.5.8); the drawn highlight keeps the object's own size */
.ns button.ns-spot::before { content: ""; position: absolute; left: 50%; top: 50%; width: max(100%, 24px); height: max(100%, 24px); transform: translate(-50%, -50%); }
.ns.show-all .ns-tag { opacity: 1; }
.ns.show-all button.ns-spot { border-color: #5ff4ff88; }
.ns.show-all .ns-tag[data-key]::before { content: attr(data-key) " "; color: var(--night); opacity: .7; }
.ns button.ns-spot:hover, .ns button.ns-spot[aria-expanded="true"] { outline: none; }
.ns button.ns-spot:focus-visible { border-color: var(--cyan); outline: none; }
.ns-tag { position: absolute; left: 50%; bottom: calc(100% + 4px); transform: translateX(-50%); white-space: nowrap; pointer-events: none;
  font: 600 13px/1.2 "Pixelify Sans", sans-serif; color: var(--night); background: var(--cyan); padding: 1px 6px; opacity: 0; }
.ns-spot:hover .ns-tag, .ns-spot:focus-visible .ns-tag { opacity: 1; }
.ns-dot { position: absolute; top: -4px; right: -4px; width: 7px; height: 7px; background: var(--pink); box-shadow: 0 0 6px var(--pink); }
/* solid, sized to its contents up to 94% of the scene, clipped top-left and bottom-right corners with cyan corner marks */
.ns-drawer { position: absolute; top: 3%; right: 2%; max-height: 94%; width: min(34%, 340px); overflow-y: auto; padding: 12px 14px;
  border: 1px solid var(--edge-strong); clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px);
  background: linear-gradient(135deg, transparent 9px, var(--cyan) 9px 11px, transparent 11px) top left / 20px 20px no-repeat,
    linear-gradient(-45deg, transparent 9px, var(--cyan) 9px 11px, transparent 11px) bottom right / 20px 20px no-repeat, var(--panel); }
.ns-drawer[hidden] { display: none; }
@media (prefers-reduced-motion: no-preference) {
  .ns-drawer:not([hidden]) { animation: ns-in .14s cubic-bezier(.2, .7, .2, 1); }
  .ns-drawer.closing { animation: ns-out .09s ease-in forwards; }
}
@keyframes ns-in { from { opacity: 0; transform: translateX(16px); } }
@keyframes ns-out { to { opacity: 0; transform: translateX(16px); } }
.ns-drawer h3 { font: 600 20px/1.2 "Pixelify Sans", sans-serif; color: var(--cyan); margin: 0; }
.ns-ttl { display: flex; align-items: center; gap: 8px; margin: 0 34px 2px 0; }
.ns-ttl svg { width: 22px; height: 22px; flex: none; }
.ns button.ns-close { position: absolute; top: 8px; right: 8px; width: 26px; padding: 0; background: var(--night); color: var(--ink); border: 1px solid var(--edge-strong); }
.ns button.ns-close:hover, .ns button.ns-close:focus-visible { border-color: var(--cyan); outline: none; }
.ns-sub { color: var(--dim); font-size: 13px; margin-bottom: 10px; }
.ns-row { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; padding: 2px 0; border-bottom: 1px solid #ffffff0d; }
.ns-row .v { font: 15px "Silkscreen", "Pixelify Sans", monospace; color: var(--amber); font-variant-numeric: tabular-nums; white-space: nowrap; }
.ns-row.warn .v { color: var(--pink); }
/* Obsidian indents list items in rendered notes; these lists sit flush */
.ns ul.ns-list { list-style: none; padding: 0; margin: 8px 0 0; font-size: 14px; }
.ns ul.ns-list > li { margin-inline-start: 0; padding: 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ns ul.ns-list > li::marker { content: none; }
.ns-list .age { color: var(--dim); margin-left: 6px; font-size: 12px; }
.ns-sec { font-size: 12.5px; color: var(--dim); margin: 14px 0 4px; padding-bottom: 3px; border-bottom: 1px solid var(--edge); }
.ns ul.ns-sess > li { display: grid; grid-template-columns: 3.6em minmax(0, 1fr); gap: 8px; white-space: normal; padding: 3px 2px; overflow: visible; }
.ns ul.ns-sess > li:focus-visible { outline: 1px solid var(--cyan); outline-offset: -1px; }
.ns-sess time { font: 13px var(--num); color: var(--amber); padding-top: 2px; }
.ns-sess .t { min-width: 0; }
.ns-sess .d { display: block; color: var(--dim); font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ns a.internal-link { color: var(--cyan); text-decoration: underline; text-decoration-color: #5ff4ff66; text-underline-offset: 3px; }
.ns a.internal-link:hover, .ns a.internal-link:focus-visible { text-decoration-color: var(--cyan); }
.ns-links { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 14px; margin-top: 10px; }
/* flyer wall: each pin is a button that opens its actions; Dusty shelf: name, age, brief, Try it */
.ns ul.ns-pins > li, .ns ul.ns-dusty > li { white-space: normal; overflow: visible; padding: 3px 0; border-bottom: 1px solid #ffffff0d; }
.ns button.ns-pin { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; width: 100%; text-align: left;
  padding: 4px 6px; background: transparent; color: var(--ink); border: 1px solid transparent; font-size: 13.5px; line-height: 1.35; white-space: normal; }
.ns button.ns-pin:hover, .ns button.ns-pin:focus-visible { border-color: var(--edge-strong); outline: none; }
.ns button.ns-pin[aria-expanded="true"] { display: block; border-color: var(--cyan); background: var(--raised); }
.ns ul.ns-pins .ns-acts { margin: 6px 0 4px; }
/* list view: the picture swapped for a list; the drawer sits beside it, or below in a narrow pane */
.ns.list-mode .ns-stage { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 340px); gap: 12px; align-items: start; padding: 12px; }
.ns.list-mode .ns-drawer { position: static; width: auto; max-height: none; }
@container ns (max-width: 700px) { .ns.list-mode .ns-stage { grid-template-columns: minmax(0, 1fr); } }
.ns-listview h2.ns-lv-h { font: 600 22px/1.2 "Pixelify Sans", sans-serif; color: var(--cyan); margin: 0 0 10px; }
.ns ul.ns-lv { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.ns ul.ns-lv > li { margin-inline-start: 0; }
.ns ul.ns-lv > li::marker { content: none; }
.ns button.ns-lv-row { width: 100%; display: flex; align-items: center; gap: 10px; padding: 6px 10px; text-align: left; white-space: normal;
  background: var(--panel); color: var(--ink); border: 1px solid var(--edge-strong); }
.ns button.ns-lv-row:hover, .ns button.ns-lv-row:focus-visible { border-color: var(--cyan); outline: none; }
.ns button.ns-lv-row[aria-expanded="true"] { border-color: var(--cyan); background: var(--raised); }
.ns button.ns-lv-row.warn { border-color: var(--pink); box-shadow: inset 3px 0 0 var(--pink); }
.ns-lv-row svg { width: 22px; height: 22px; flex: none; }
.ns-lv-row .nm { flex: 1; font-weight: 700; }
.ns-lv-row .v { font: 15px var(--num); color: var(--amber); font-variant-numeric: tabular-nums; }
.ns-lv-row.warn .v { color: var(--pink); }
.ns-lv-row .u { color: var(--dim); font-size: 13px; }
.ns-lv-row .look { font-size: 12px; color: var(--pink); }
.ns button.ns-view { margin-left: auto; }
.ns-dusty .top { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.ns-dusty .nm { font-weight: 700; }
.ns-dusty .d { color: var(--dim); font-size: 12.5px; margin: 1px 0 4px; }
.ns-strip { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px; background: var(--panel); border-top: 1px solid var(--edge); }
.ns button.ns-count { display: flex; align-items: baseline; gap: 6px; padding: 4px 10px; background: var(--night); color: var(--ink); border: 1px solid var(--edge-strong); }
.ns-count b { font: 15px var(--num); color: var(--amber); font-variant-numeric: tabular-nums; }
.ns-count.warn b { color: var(--pink); }
/* trouble is shown by more than colour (WCAG 1.4.1): a pink edge and words, and these counts come first */
.ns button.ns-count.warn { border-color: var(--pink); box-shadow: inset 3px 0 0 var(--pink); }
.ns-count .look { font-size: 12px; color: var(--pink); }
.ns button.ns-count:hover, .ns button.ns-count:focus-visible { border-color: var(--cyan); outline: none; }
.ns-acts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.ns button.ns-act { padding: 4px 10px; background: var(--night); color: var(--ink); border: 1px solid var(--edge-strong);
  clip-path: polygon(7px 0, 100% 0, 100% calc(100% - 7px), calc(100% - 7px) 100%, 0 100%, 0 7px); }
.ns button.ns-act:hover, .ns button.ns-act:focus-visible { border-color: var(--cyan); outline: none; }
.ns button.ns-act:focus-visible { background: var(--raised); }
/* one filled main button per panel */
.ns button.ns-act.pri { background: var(--cyan); color: var(--night); border-color: var(--cyan); font-weight: 700; }
.ns button.ns-act.pri:hover, .ns button.ns-act.pri:focus-visible { background: #a6f9ff; }
.ns button.ns-act.busy { color: var(--cyan); border-color: var(--cyan); }
.ns button.ns-act.done { color: var(--green); border-color: var(--green); }
.ns button.ns-act.bad { color: var(--pink); border-color: var(--pink); }
.ns button.ns-act:disabled { opacity: .7; cursor: default; }
.ns.offline button.ns-act { opacity: .45; }
.ns-tip { position: absolute; z-index: 40; max-width: 260px; padding: 4px 8px; font-size: 13px; line-height: 1.3;
  background: var(--panel); color: var(--ink); border: 1px solid var(--cyan); box-shadow: 0 2px 8px #000a; }
.ns-field-label { display: block; font-size: 13px; color: var(--ink); margin-top: 10px; }
.ns-field { position: relative; margin-top: 4px; }
.ns-field::before { content: "\\203A"; position: absolute; left: 10px; top: 50%; transform: translateY(-52%); color: var(--cyan); font: 600 16px "Pixelify Sans", sans-serif; pointer-events: none; }
.ns input.ns-text { width: 100%; margin: 0; padding: 6px 10px 6px 26px; background: var(--night); color: var(--ink); border: 1px solid var(--edge-strong); border-radius: 0; box-sizing: border-box; }
.ns input.ns-text:focus-visible, .ns input.ns-text:focus { border-color: var(--cyan); outline: none; box-shadow: 0 0 0 1px var(--cyan), 0 0 10px #5ff4ff55; }
.ns-help { display: flex; justify-content: space-between; gap: 8px; font-size: 12.5px; color: var(--dim); margin-top: 4px; }
.ns-help .cnt { font-family: var(--num); font-size: 11px; }
.ns-help .cnt.over { color: var(--pink); }
/* finish notes and the server chip, bottom right of the scene */
.ns-notes { position: absolute; right: 2%; bottom: 8px; z-index: 25; display: grid; gap: 6px; justify-items: end; max-width: 60%; }
.ns-note { display: flex; gap: 10px; align-items: center; padding: 6px 10px; font-size: 13.5px; background: #0e0a18f2; border: 1px solid var(--green); }
.ns-note.fail { border-color: var(--pink); }
.ns-note button { padding: 1px 7px; font-size: 12.5px; background: var(--night); color: var(--ink); border: 1px solid var(--edge-strong); }
.ns-note pre { margin: 0; max-height: 140px; overflow: auto; font: 12px/1.3 ui-monospace, monospace; white-space: pre-wrap; }
.ns-chip { padding: 2px 8px; font-size: 12.5px; background: #0e0a18e6; color: var(--pink); border: 1px solid var(--pink); }
.ns-log { max-height: 160px; overflow: auto; margin: 8px 0 0; padding: 6px; font: 12px/1.3 ui-monospace, monospace; white-space: pre-wrap; background: var(--night); border: 1px solid var(--edge); }
.ns-toast { position: absolute; left: 2%; top: 3%; max-width: 40%; padding: 6px 10px; font-size: 13px; background: #0e0a18e6; border: 1px solid var(--pink); }
.ns-alarm { color: var(--pink); border: 1px solid var(--pink); padding: 6px 10px; margin: 8px; }
@container ns (max-width: 700px) { .ns-drawer { position: static; width: auto; max-height: none; } .ns-toast, .ns-notes { max-width: 90%; } }
@media (prefers-reduced-motion: no-preference) { .ns-tag, .ns-glow { transition: opacity .12s; } }
`

// --- helpers ----------------------------------------------------------------------------
const el = (parent, tag, cls, text) => parent.createEl(tag, { cls, text })
const missing = []
const src = (path) => {
  const f = app.vault.getAbstractFileByPath(path)
  if (!f) { missing.push(path); return "" }
  return app.vault.getResourcePath(f)
}
// for the videos: the file's current time and size from disk, because the vault's cached time can lag a render that was
// still being written, and the player then keeps a cut-off copy under the old URL
const srcFresh = async (path) => {
  const base = src(path)
  const st = base && await app.vault.adapter.stat(path)
  return st ? `${base.split("?")[0]}?${st.mtime}-${st.size}` : base
}
const link = (parent, page, text) => el(parent, "a", "internal-link", text ?? page.file.name)
  .setAttrs({ "data-href": page.file.path, href: page.file.path })
const row = (parent, label, value, warn) => {
  const r = el(parent, "div", "ns-row" + (warn ? " warn" : ""))
  el(r, "span", "k", label); el(r, "span", "v", String(value))
}
const list = (parent, pages, fmt) => {
  if (!pages.length) return
  const ul = el(parent, "ul", "ns-list")
  for (const p of pages) { const li = el(ul, "li"); link(li, p); if (fmt) el(li, "span", "age", fmt(p)) }
}
// localStorage can throw or be empty (private mode, cleared data); the page must work without it.
const load = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d } catch { return d } }
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)) } catch {} }
const now = dv.date("now")
const ageDays = (d) => Math.max(0, Math.floor(now.diff(d, "days").days))
const str = (v) => v == null ? "" : (v.toISODate ? v.toISODate() : String(v))

// --- vault data (rules carried over from the Omnissiah Terminal) ---------------------------
const projects = dv.pages('"projects"').where(p => p.file.folder === "projects" && p.file.tags.includes("#project"))
const byStatus = (s) => projects.where(p => p.status === s).length
const inbox = dv.pages('"_inbox"').sort(p => p.file.ctime, "asc")

// Same rule as _tooling.base "Drift" and "Stale".
const tracked = dv.pages('"areas/tooling"').where(p => !["proposed", "rejected"].includes(p.adoption)
  && p.upstream_ref != null && !["", "n/a", "unchecked"].includes(str(p.upstream_ref)))
const drift = tracked.where(p => str(p.upstream_ref) !== str(p.installed_ref))
const stale = tracked.where(p => p.checked && ageDays(p.checked) > 30)

// pins.md: one task per line, written by Claude Code sessions when he says "pin this" (a standing rule in its memory)
const pinsNote = dv.page("pins")
const pins = pinsNote ? pinsNote.file.tasks.where(t => !t.completed).array() : []

const orphans = dv.pages().where(p => p.status && !/^(_archive|templates|daily)\//.test(p.file.path)
  && p.file.path !== dv.current().file.path && p.file.inlinks.length === 0)

const dailies = dv.pages('"daily"').where(p => /^\d{4}-\d{2}-\d{2}$/.test(p.file.name)).sort(p => p.file.name, "desc")
const keptDays = new Set(dailies.file.name.array().slice(0, 14))
let kept = 0
for (let i = 0; i < 7; i++) if (keptDays.has(now.minus({ days: i }).toISODate())) kept++
const review = dv.pages('"daily"').where(p => /-W\d+-review$/.test(p.file.name)).sort(p => p.file.name, "desc").first()

// Session headings from the newest daily note that has any.
let sessions = [], sessionDay = null
for (const d of dailies.array().slice(0, 5)) {
  const lines = (await dv.io.load(d.file.path)).split("\n")
  lines.forEach((line, i) => {
    const m = line.match(/^### (\d\d:\d\d) · (.+?)\s*(<!--.*)?$/)
    if (!m) return
    const next = lines.slice(i + 1, i + 6)
    const q = next.find(l => l.startsWith("> "))?.slice(2) ?? ""
    // Prompts that open with injected <system> text say nothing; show the touched files instead.
    const what = q && !q.startsWith("<") ? q : (next.find(l => l.startsWith("Touched:")) ?? "").replace(/`/g, "")
    sessions.push({ t: m[1], where: m[2], what })
  })
  if (sessions.length) { sessionDay = d; break }
}

// Job search: counts only, never company names. Follow-up rule mirrors
// _dashboard/vault.py jobs_panel (/outcome Step 2b); change them together.
let jobs = null
try {
  const FINAL = ["hired", "rejected", "no_response", "offer_declined", "withdrawn"]
  const rows = (await dv.io.csv("projects/ai-job-search/job_search_tracker.csv")).array()
  const today = now.toISODate()
  jobs = { sent: 0, open: 0, due: 0, interview: 0 }
  for (const r of rows) {
    const status = str(r.status).trim().toLowerCase().replace(/ /g, "_")
    if (status === "drafted") continue
    jobs.sent++
    if (status === "interview") jobs.interview++
    if (FINAL.includes(status)) continue
    jobs.open++
    const notes = str(r.notes)
    const dates = [str(r.date).slice(0, 10), ...(notes.match(/\b\d{4}-\d{2}-\d{2}\b/g) ?? [])].filter(d => d && d <= today).sort()
    const followups = (notes.match(/followed up \d{4}-\d{2}-\d{2}/gi) ?? []).length
    const last = dates.length && str(r.date) ? dates[dates.length - 1] : null
    if (last && ageDays(dv.date(last)) >= 10 && followups < 2) jobs.due++
  }
} catch (e) { jobs = null }

// --- notifications: diff against the last snapshot ----------------------------------------
// Dataview re-runs this block on vault changes, so a changed number since the last render is news.
const snap = { inbox: inbox.length, drift: drift.length, stale: stale.length, orphans: orphans.length,
  projects: projects.length, sessions: sessions.length, interview: jobs?.interview ?? null, due: jobs?.due ?? null }
const NAMES = { inbox: "Inbox notes", drift: "Tools to update", stale: "Tools unchecked 30+ days", orphans: "Orphan notes",
  projects: "Projects", sessions: "Sessions logged", interview: "Interviews", due: "Job follow-ups due" }
const LOUD = ["inbox", "drift", "interview", "due"] // these also raise an Obsidian notice when they go up
const prev = load("night-shift:snapshot", null)
const news = prev ? Object.keys(snap).filter(k => snap[k] != null && prev[k] != null && snap[k] !== prev[k]) : []
const log = load("night-shift:log", [])
for (const k of news) {
  const text = `${NAMES[k]}: ${prev[k]} to ${snap[k]}`
  log.unshift({ t: now.toFormat("MM-dd HH:mm"), text })
  if (LOUD.includes(k) && snap[k] > prev[k]) new Notice("Night Shift: " + text)
}
log.length = Math.min(log.length, 30)
save("night-shift:log", log)
save("night-shift:snapshot", snap)

// --- drawers: one per hotspot -----------------------------------------------------------
// box = [left, top, width, height] in % of the scene. The Blender spots file overrides it with each
// object's measured box and adds its mask; the boxes here are only the fallback.
// To add a panel, add an entry whose id matches a scene object's poi tag in scripts/night_shift_corner.py. Tagged and
// waiting for a panel: "email" (the street mailbox, far right) and "fleet" (the satellite dish, panel comes with the fleet status pull).
// tooltips: what a button does, shown on hover and read by screen readers as its description. Every button gets one via tip().
// Keep each one short (one line). A button with no tip still gets one: the hover handler near the bottom falls back to its label.
const S = " (opens VS Code, press Enter)"
const TIPS = {
  "ledger-refresh": "Re-check every tool in the ledger for updates.",
  triage: "Sort the inbox notes" + S,
  scrape: "Run the job scrape" + S,
  "sort-orphans": "Propose a home for each orphan note" + S,
  "fleet-pull": "Read the Oracle box's spend and status, read-only.",
  readlog: "Show this task's latest log lines.",
  ask: "Ask Claude why this task failed" + S,
  "lib-research": "Research the text in the box" + S,
  "lib-sweep": "Wider research sweep by Ephraim" + S,
  "lib-clip": "Save the link in the box as a note" + S,
  "lib-capture": "Save the text to the inbox as typed" + S,
  "lib-ask": "Search the vault for what you already know" + S,
  "deck-audit": "Re-audit a deck against new cards" + S,
  "deck-wizard": "Build or tune a deck" + S,
  "deck-strat": "Write a strategy guide for a deck" + S,
  "pin-resume": "Pick up this pin" + S,
  "pin-fool": "Stress-test what this pin proposes" + S,
  "pin-jury": "A panel of agents reaches a verdict on it" + S,
  "pin-scope": "Mustang breaks it into ordered jobs" + S,
  "pin-open": "Open pins.md at this pin.",
  "pin-done": "Tick this pin as done in pins.md.",
  "skill-try": "Learn what this skill does and a task to try it on" + S,
  rain: "Turn the rain animation on or off.",
  close: "Close this panel.",
}
// shown by the delegated hover handler one second after hover or focus; aria-description lets screen readers read it at once
const tip = (b, text) => { if (text) { b.dataset.tip = text; b.setAttr("aria-description", text) } }
const sec = (parent, text) => el(parent, "div", "ns-sec", text)
// 11 x 11 pixel icons beside each panel title, one row per string: a amber, c cyan, p pink, g green, i ink, d dim, k night
const PIX = { a: "#ffb85c", c: "#5ff4ff", p: "#ff4fb4", g: "#6dff8a", i: "#c9d2bf", d: "#7f9cab", k: "#0e0a18" }
const ICONS = {
  projects: ["....g......", "..g.g.g....", "...ggg.....", ".g..g..g...", "..ggggg....", "....g......", "..aaaaaaa..", "..aaaaaaa..", "...aaaaa...", "...aaaaa...", "..........."].map(r => r.slice(0, 11)),
  tooling: [".......ii..", "......i..i.", "......i..i.", ".......iii.", "......ii...", ".....ii....", "....ii.....", "...ii......", "..aa.......", ".aa........", "..........."],
  daily: ["...........", ".caaaaaaa..", "..akkkkka..", ".cakiiika..", "..akkkkka..", ".cakiiika..", "..akkkkka..", ".cakiikka..", "..akkkkka..", "..aaaaaaa..", "..........."],
  inbox: ["...........", "...........", ".ccccccccc.", ".cc.....cc.", ".c.c...c.c.", ".c..c.c..c.", ".c...c...c.", ".c.......c.", ".ccccccccc.", "...........", "..........."],
  jobs: ["...........", ".ccccccccc.", ".ckkkkkkkc.", ".ckgkkkkkc.", ".ckkgkkkkc.", ".ckgkkiikc.", ".ckkkkkkkc.", ".ccccccccc.", "....ddd....", "...ddddd...", "..........."],
  orphans: ["...........", "...........", "..aaaaaaa..", "..a.....a..", "..a.ppp.a..", "..a...p.a..", "..a..pp.a..", "..a.....a..", "..a..p..a..", "..aaaaaaa..", "..........."],
  games: ["...........", "..ppppppp..", "..piiiiip..", "..pic.iip..", "..piiiiip..", "..pii.cip..", "..piiiiip..", "..pi.ciip..", "..piiiiip..", "..ppppppp..", "..........."],
  fleet: [".........c.", "........c..", "..ii...c...", ".i..i.c....", ".i...ic....", ".i....i....", "..i....i...", "...iiiiii..", ".....dd....", "....dddd...", "..........."],
  library: ["...........", "...........", ".aaaa.aaaa.", ".aiia.aiia.", ".aiia.aiia.", ".aiia.aiia.", ".aiia.aiia.", ".aaaacaaaa.", ".....c.....", "...........", "..........."],
  mart: ["...........", ".ppppppppp.", ".pkkkkkkkp.", ".pkaakkakp.", ".pkkakkakp.", ".pkakkaaap.", ".pkaakkkap.", ".pkkkkkkkp.", ".ppppppppp.", "....d.d....", "....d.d...."],
  pins: ["...........", "....ppp....", "...ppppp...", "...ppppp...", "....ppp....", "...ppppp...", ".....i.....", ".....i.....", ".....i.....", "...........", "..........."],
  news: ["...........", ".ccccccccc.", ".ckkkkkkkc.", ".ckckkckkc.", ".ckkckckkc.", ".ckkkckkkc.", ".ckkkkkkkc.", ".ccccccccc.", ".....d.....", "...ddddd...", "..........."],
}
const icon = (parent, id) => {
  const rows = ICONS[id]
  if (!rows) return
  const rects = rows.flatMap((r, y) => [...r].map((ch, x) => PIX[ch] ? `<rect x="${x}" y="${y}" width="1" height="1" fill="${PIX[ch]}"/>` : "")).join("")
  parent.insertAdjacentHTML("afterbegin", `<svg viewBox="0 0 11 11" aria-hidden="true" shape-rendering="crispEdges">${rects}</svg>`)
}
let RENDERED = {}
try { RENDERED = JSON.parse(await app.vault.adapter.read("_attachments/scenes/night-shift-3d-spots.json")) } catch { missing.push("_attachments/scenes/night-shift-3d-spots.json") }
const SPOTS = [
  { id: "projects", label: "Projects", box: [62.55, 37.87, 19.43, 30.37], warn: false, fill(d) {
    el(d, "div", "ns-sub", "In the hydroponics florist and its balcony, by growth stage")
    row(d, "Seed", byStatus("seed")); row(d, "Growing", byStatus("growing")); row(d, "Evergreen", byStatus("evergreen"))
    list(d, projects.sort(p => p.file.mtime, "desc").limit(6).array(), p => `${ageDays(p.file.mtime)}d ago`)
    el(d, "div", "ns-sub", "Resume opens a new Claude session in VS Code with the prompt ready: wait about 5 s and don't click another window, then press Enter")
    acts(d, ["mtg-web", "recipe-box", "agentic-fleet", "ai-job-search", "mtg-deck-builder"].map(r => [r, "resume-" + r, `Continue ${r} where it left off` + S]))
  } },
  { id: "tooling", label: "Tooling", box: [25.3, 54.3, 8.7, 18.2], warn: drift.length > 0, fill(d) {
    el(d, "div", "ns-sub", "At the repair shop: tools in the ledger that need attention")
    row(d, "Update available", drift.length, drift.length > 0)
    row(d, "Unchecked 30+ days", stale.length, stale.length > 0)
    row(d, "Up to date", tracked.length - drift.length)
    list(d, drift.limit(6).array())
    acts(d, [["Refresh the ledger", "ledger-refresh"]])
  } },
  { id: "daily", label: "Daily log", box: [41, 72.7, 10.1, 23.1], warn: kept < 4, fill(d) {
    el(d, "div", "ns-sub", sessionDay ? `Sessions logged on ${sessionDay.file.name}` : "No sessions logged in the last five daily notes")
    sec(d, "This week")
    row(d, "Days logged, last 7", `${kept}/7`, kept < 4)
    if (review) row(d, "Days since weekly review", ageDays(review.file.ctime), ageDays(review.file.ctime) > 8)
    const today = sessionDay?.file.name === now.toISODate()
    if (sessions.length) {
      sec(d, today ? "Sessions today" : `Sessions on ${sessionDay.file.name}`)
      const ul = el(d, "ul", "ns-list ns-sess")
      for (const s of sessions.slice(-8).reverse()) {
        const li = el(ul, "li"); el(li, "time", null, s.t)
        const t = el(li, "span", "t", s.where)
        if (s.what) { el(t, "span", "d", s.what); tip(li, s.what); li.tabIndex = 0 } // full text on hover or focus
      }
    }
    if (sessionDay || review) {
      sec(d, "Notes")
      const ln = el(d, "div", "ns-links")
      if (sessionDay) link(ln, sessionDay, today ? "Today's daily note" : `Daily note ${sessionDay.file.name}`)
      if (review) link(ln, review, review.file.name.replace(/^\d{4}-W(\d+)-review$/, "Weekly review W$1"))
    }
  } },
  { id: "inbox", label: "Inbox", box: [46.4, 59.9, 3.4, 12.4], warn: inbox.length > 10, fill(d) {
    el(d, "div", "ns-sub", "Messages on the side-wall screen: notes in _inbox to triage")
    row(d, "Waiting", inbox.length, inbox.length > 10)
    if (inbox.length) row(d, "Oldest (days)", ageDays(inbox.first().file.ctime), ageDays(inbox.first().file.ctime) > 14)
    list(d, inbox.limit(6).array(), p => `${ageDays(p.file.ctime)}d`)
    if (!inbox.length) el(d, "div", "ns-sub", "Inbox is empty.")
    acts(d, [["Triage the inbox", "triage"]])
  } },
  { id: "jobs", label: "Job search", box: [33.4, 61, 17.2, 22.9], warn: (jobs?.due ?? 0) > 0, fill(d) {
    el(d, "div", "ns-sub", "At the net café on the corner: counts from the job tracker, no company names")
    if (!jobs) return el(d, "div", "ns-sub", "Can't read projects/ai-job-search/job_search_tracker.csv.")
    row(d, "Applications sent", jobs.sent); row(d, "Waiting on a reply", jobs.open)
    row(d, "Interviews", jobs.interview); row(d, "Follow-ups due", jobs.due, jobs.due > 0)
    acts(d, [["Run /scrape", "scrape"]])
  } },
  { id: "orphans", label: "Orphan notes", box: [86.2, 38.8, 3.7, 9.5], warn: orphans.length > 20, fill(d) {
    el(d, "div", "ns-sub", "Notes with a status that nothing links to")
    row(d, "Orphans", orphans.length, orphans.length > 20)
    list(d, orphans.sort(p => p.file.mtime, "desc").limit(6).array())
    acts(d, [["Sort orphans", "sort-orphans"]])
  } },
  { id: "games", label: "Game hub", box: [51.04, 56.76, 12.29, 20.56], warn: false, fill(d) {
    el(d, "div", "ns-sub", "In the game hub on the ground floor: your card games and deck work")
    const homes = ["areas/cyberpunk-tcg", "projects/mtg-deck-builder", "projects/mtg-web"].map(p => dv.page(p)).filter(Boolean)
    list(d, homes, p => `${ageDays(p.file.mtime)}d ago`)
    // catalogue-cards is switched off at the vault root (.claude/settings.local.json), so it has no button here
    acts(d, [["Audit a deck", "deck-audit"], ["Deck wizard", "deck-wizard"], ["Strategy guide", "deck-strat"]])
  } },
  // the satellite dish: the Oracle box as of the last manual pull (fleet_pull.py, no schedule; pinned in pins.md)
  { id: "fleet", label: "Fleet uplink", box: null, warn: false, fill(d) {
    el(d, "div", "ns-sub", "On the satellite dish: the Oracle box, as of the last pull (a button pulls it, nothing runs on a timer)")
    const body = el(d, "div")
    const ago = (iso) => { const m = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000)); return m < 90 ? `${m} min ago` : m < 2880 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago` }
    const draw = async () => {
      body.empty()
      let f
      try { f = (await requestUrl({ url: API + "/api/night-shift/fleet", headers: HDR })).json } catch { return body.setText("Dashboard server is not reachable on 127.0.0.1:8790.") }
      if (!f.present) el(body, "div", "ns-sub", "No pull yet. Use the button below.")
      else {
        const status = el(body, "div", "ns-row" + (f.ok ? "" : " warn"))
        el(status, "span", "k", f.ok ? "Pulled" : "Last pull failed"); el(status, "span", "v", f.ok ? ago(f.pulled_at) : (f.last_ok ? "data from " + ago(f.last_ok) : "no data"))
        if (!f.ok) el(body, "div", "ns-sub", f.error)
        for (const [k, msg] of Object.entries(f.data ?? {})) if (k.endsWith("_error")) row(body, k.replace("_error", ""), "unreadable: " + msg, true)
        const s = f.data?.spend
        if (s) {
          const pct = f.cap_usd ? s.total_usd / f.cap_usd : 0
          row(body, `Spend ${s.month}`, f.cap_usd ? `$${s.total_usd.toFixed(2)} of $${f.cap_usd.toFixed(0)}` : `$${s.total_usd.toFixed(2)}`, pct > 0.8)
          const ul = el(body, "ul", "ns-list")
          for (const [a, v] of Object.entries(s.by_agent).sort((x, y) => y[1] - x[1])) el(ul, "li", null, `${a} $${v.toFixed(2)}`)
          if (s.last_call_utc) el(body, "div", "ns-sub", `Last model call ${ago(s.last_call_utc.endsWith("Z") || /[+-]\d\d:\d\d$/.test(s.last_call_utc) ? s.last_call_utc : s.last_call_utc + "Z")}`)
        }
        for (const [name, status] of Object.entries(f.data?.containers ?? {})) row(body, name.replace("fleet-", ""), status, !status.startsWith("Up"))
        const jobs = Object.entries(f.data?.jobs ?? {}).sort((x, y) => y[1].localeCompare(x[1]))
        if (jobs.length) {
          el(body, "div", "ns-sub", "Last job runs (the fleet's own clock)")
          const ul = el(body, "ul", "ns-list")
          for (const [name, t] of jobs) el(ul, "li", null, `${name}`).createSpan({ cls: "age", text: t.replace("T", " ").slice(0, 16) })
        }
      }
    }
    const box = el(d, "div", "ns-acts"), b = el(box, "button", "ns-act pri", "Pull fleet status now")
    b.type = "button"; tip(b, TIPS["fleet-pull"])
    b.onclick = async () => {
      body.setText("Pulling from the box...")
      if (await runAction("fleet-pull", undefined, b)) await finished("fleet-pull") // the button shows its own progress
      if (body.isConnected) draw()
    }
    draw()
  } },
  { id: "library", label: "Library", box: null, warn: false, fill(d) {
    el(d, "div", "ns-sub", "On the ground floor past the florist: research and reference notes in resources/")
    const res = dv.pages('"resources"').sort(p => p.file.mtime, "desc")
    row(d, "Notes in resources/", res.length)
    list(d, res.limit(6).array(), p => `${ageDays(p.file.mtime)}d ago`)
    // visible label, prompt mark, live count; Enter runs the read-only "What do I know?"; a link lights up Clip; the draft is kept
    const lab = el(d, "label", "ns-field-label", "Topic, link or thought"); lab.htmlFor = "ns-lib-in"
    const field = el(d, "div", "ns-field")
    const inp = el(field, "input", "ns-text")
    inp.setAttrs({ id: "ns-lib-in", type: "text", maxlength: "150", placeholder: "e.g. commander staples", "aria-describedby": "ns-lib-help" })
    const help = el(d, "div", "ns-help"); help.id = "ns-lib-help"
    el(help, "span", null, "Opens a Claude session in VS Code; press Enter there")
    const cnt = el(help, "span", "cnt")
    const box = el(d, "div", "ns-acts"), btns = {}
    for (const [label, id] of [["Research it", "lib-research"], ["Research sweep", "lib-sweep"], ["Clip this link", "lib-clip"], ["Capture it", "lib-capture"], ["What do I know?", "lib-ask"]]) {
      const b = btns[id] = el(box, "button", "ns-act", label); b.type = "button"; tip(b, TIPS[id])
      b.onclick = () => inp.value.trim() ? runAction(id, inp.value, b) : (new Notice("Type something in the box first."), inp.focus())
    }
    const sync = () => {
      const v = inp.value, link = /^https?:\/\//i.test(v.trim())
      cnt.setText(`${v.length} / 150`); cnt.toggleClass("over", v.length >= 140)
      btns["lib-clip"].toggleClass("pri", link); btns["lib-ask"].toggleClass("pri", !link)
      save("night-shift:lib-draft", v)
    }
    inp.value = load("night-shift:lib-draft", "")
    inp.addEventListener("input", sync)
    inp.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); btns["lib-ask"].click() } })
    sync()
    // Dusty shelf: skills loadable here and unused for 30+ days (from the transcripts, refreshed every 10 min by the server)
    sec(d, "Dusty shelf")
    const shelf = el(d, "div")
    shelf.setText("Counting skill use…")
    requestUrl({ url: API + "/api/night-shift/dusty", headers: HDR }).then(({ json }) => {
      shelf.empty()
      if (!json.skills) return el(shelf, "div", "ns-sub", "Still counting skill use. Reopen this panel in a few seconds.")
      if (!json.skills.length) return el(shelf, "div", "ns-sub", `Every skill here was used in the last ${json.days} days.`)
      el(shelf, "div", "ns-sub", `Skills not used in ${json.days}+ days`)
      const ul = el(shelf, "ul", "ns-list ns-dusty")
      for (const s of json.skills) {
        const li = el(ul, "li"), top = el(li, "div", "top")
        el(top, "span", "nm", s.name); el(top, "span", "age", s.last_used ? `last ${s.last_used}` : "never used")
        el(li, "div", "d", s.brief)
        const b = el(li, "button", "ns-act", "Try it"); b.type = "button"; tip(b, TIPS["skill-try"])
        b.onclick = () => runAction("skill-try", s.name, b)
      }
      if (root.hasClass("offline")) setOffline(true)
    }).catch(() => shelf.setText("Dashboard server is not reachable on 127.0.0.1:8790."))
  } },
  // no fallback box: the spots file has the mart's; local schedules only, the fleet's come with the dish (job 5, box side)
  { id: "mart", label: "24H Mart", box: null, warn: false, fill(d) {
    el(d, "div", "ns-sub", "In the 24H Mart: this PC's scheduled tasks, read from Windows Task Scheduler")
    const body = el(d, "div"), logBox = el(d, "pre", "ns-log"); logBox.hidden = true
    const when = (s) => s ? s.replace("T", " ").slice(0, 16) : "none"
    const show = async (url, fn) => { try { fn((await requestUrl({ url: API + url, headers: HDR })).json) } catch { body.setText("Dashboard server is not reachable on 127.0.0.1:8790.") } }
    show("/api/night-shift/schedules", (rows) => {
      if (!rows.length) return body.setText("No data yet: reopen this in a few seconds.")
      for (const r of rows) {
        row(body, r.name.replace("SecondBrain-", ""), r.ok ? r.state : `failed (${r.result})`, !r.ok)
        el(body, "div", "ns-sub", `last ${when(r.last)}, next ${when(r.next)}`)
        if (!r.log) continue
        const items = [["Read log", null], ["Ask Claude", "ask-" + r.log]]
        const box = el(body, "div", "ns-acts")
        for (const [label, id] of items) {
          const b = el(box, "button", "ns-act", label); b.type = "button"; tip(b, id ? TIPS.ask : TIPS.readlog)
          b.onclick = id ? () => runAction(id, undefined, b) : () => show("/api/night-shift/log/" + r.log, (j) => { logBox.hidden = false; logBox.setText(j.text || "(empty)") })
        }
      }
    })
  } },
  // no box: the flyer wall is not in the scene yet, so this opens from the strip below; once the scene tags it `pins` and
  // night_shift_spots.py writes its box, the object gets a button with no change here
  { id: "pins", label: "Pins", box: null, warn: false, fill(d) {
    el(d, "div", "ns-sub", "On the flyer wall: things you asked a session to pin")
    row(d, "Open", pins.length)
    if (!pins.length) el(d, "div", "ns-sub", "Nothing pinned. Say \"pin this\" in a session.")
    // each pin is a disclosure: its text opens its actions (2 to 4 main, the rest under More, per the button rule)
    const ul = el(d, "ul", "ns-list ns-pins")
    for (const t of pins.slice(0, 12)) {
      const li = el(ul, "li")
      const head = el(li, "button", "ns-pin", t.text); head.type = "button"; head.setAttr("aria-expanded", "false")
      tip(head, "Show what you can do with this pin.")
      const row = el(li, "div", "ns-acts"); row.hidden = true
      const key = [...t.text].slice(0, 140).join("").trim() // whole characters (never half an emoji); the session finds the whole pin from its start
      const act = (label, id, cls = "") => { const b = el(row, "button", "ns-act" + cls, label); b.type = "button"; tip(b, TIPS[id]); b.onclick = () => runAction(id, key, b); return b }
      act("Resume", "pin-resume", " pri")
      const openB = el(row, "button", "ns-act", "Open"); openB.type = "button"; tip(openB, TIPS["pin-open"])
      openB.onclick = () => { const f = app.vault.getAbstractFileByPath(t.path); if (f) app.workspace.getLeaf("tab").openFile(f, { eState: { line: t.line } }) }
      const doneB = el(row, "button", "ns-act", "Done"); doneB.type = "button"; tip(doneB, TIPS["pin-done"])
      doneB.onclick = async () => {
        const f = app.vault.getAbstractFileByPath(t.path)
        let ticked = false
        // ticks only this line, and only if it is still this open pin; Dataview then redraws the list
        if (f) await app.vault.process(f, (data) => {
          const lines = data.split("\n"), l = lines[t.line] ?? ""
          if (/^\s*- \[ \] /.test(l) && l.includes(t.text.slice(0, 40))) { lines[t.line] = l.replace("- [ ] ", "- [x] "); ticked = true }
          return lines.join("\n")
        })
        new Notice(ticked ? "Pin ticked in pins.md." : "pins.md changed since this list was drawn: open it to tick the pin.")
      }
      const more = el(row, "button", "ns-act", "More"); more.type = "button"; more.setAttr("aria-expanded", "false")
      tip(more, "Stress-test, verdict or scope this pin.")
      const extra = el(li, "div", "ns-acts"); extra.hidden = true
      for (const [label, id] of [["Stress-test", "pin-fool"], ["Verdict", "pin-jury"], ["Scope", "pin-scope"]]) {
        const b = el(extra, "button", "ns-act", label); b.type = "button"; tip(b, TIPS[id]); b.onclick = () => runAction(id, key, b)
      }
      more.onclick = () => { extra.hidden = !extra.hidden; more.setAttr("aria-expanded", String(!extra.hidden)) }
      head.onclick = () => {
        const opening = row.hidden
        for (const other of ul.querySelectorAll("li")) { // one pin open at a time
          other.querySelector(".ns-pin").setAttr("aria-expanded", "false")
          for (const r of other.querySelectorAll(".ns-acts")) r.hidden = true
        }
        if (opening) { row.hidden = false; head.setAttr("aria-expanded", "true"); more.setAttr("aria-expanded", "false") }
      }
    }
    if (pinsNote) link(el(d, "div", "ns-links"), pinsNote, "Open pins.md")
  } },
  { id: "news", label: "Notifications", box: [38, 23.8, 8, 32.9], warn: news.length > 0, fill(d) {
    el(d, "div", "ns-sub", "On the big rooftop screen: changes seen since this dashboard last rendered")
    if (!log.length) return el(d, "div", "ns-sub", "Nothing has changed yet. Changes show up here as the vault moves.")
    const ul = el(d, "ul", "ns-list")
    for (const n of log) { const li = el(ul, "li", null, n.text); el(li, "span", "age", n.t) }
  } },
]

// --- render ------------------------------------------------------------------------------
const stage = el(root, "div", "ns-stage")
const scene = el(stage, "div", "ns-scene")
const sceneSrc = src("_attachments/scenes/night-shift-3d.png")
// list view: a plain list of every panel in place of the picture, by his switch or when the picture cannot load.
// `let` and set later, because the image can fail while this block still awaits file reads below.
let listView = null, viewBtn = null, sceneFailed = !sceneSrc, listOn = load("night-shift:list", false), syncView = () => {}
scene.createEl("img", { attr: { src: sceneSrc, draggable: "false",
  alt: "An isometric voxel street corner at night in violet fog and rain: a ramen stand on the corner, a net café in the corner building, a repair shop, a 24h mart, a hydroponics florist with a plant-filled balcony and outdoor stairs, tall neon banners, rooftop screens, a water tank, people on the street and a hex-windowed tower" } })
  .onerror = () => { sceneFailed = true; syncView() }
// motion: an 8 s loop of the whole scene (flickering signs, swaying palms, walkers) over the still, then a
// 2 s rain and steam loop over that, H.264 on black and laid with mix-blend-mode: screen (the alpha VP9 version
// decoded in software at about 35% of a core; this one and the loop decode on the GPU, about 7% together). Both
// pause out of view. On/off is remembered; the first visit follows the OS
// reduced-motion setting, and the still shows whenever motion is off. Hover masks come from the still.
const loop = scene.createEl("video", { cls: "ns-loop", attr: { src: await srcFresh("_attachments/scenes/night-shift-3d-loop.webm"), poster: sceneSrc, "aria-hidden": "true" } })
const rain = scene.createEl("video", { cls: "ns-rain", attr: { src: await srcFresh("_attachments/scenes/night-shift-3d-rain.mp4"), "aria-hidden": "true" } })
for (const v of [loop, rain]) { v.muted = true; v.loop = true; v.playsInline = true }
let rainOn = load("night-shift:rain", !matchMedia("(prefers-reduced-motion: reduce)").matches), inView = false
const corner = el(stage, "div", "ns-corner")
const rainBtn = el(corner, "button", "ns-rain-toggle")
rainBtn.type = "button"; tip(rainBtn, TIPS.rain)
// every object's name at once: hold Alt for a look, or this switch for mouse use (remembered)
const labelsBtn = el(corner, "button", "ns-rain-toggle")
labelsBtn.type = "button"; tip(labelsBtn, "Show the name of every object at once (or hold Alt).")
let labelsOn = load("night-shift:labels", false)
const syncLabels = (peek) => {
  root.toggleClass("show-all", labelsOn || !!peek)
  labelsBtn.setText(labelsOn ? "Labels: on" : "Labels: off"); labelsBtn.setAttr("aria-pressed", String(labelsOn))
}
labelsBtn.onclick = () => { labelsOn = !labelsOn; save("night-shift:labels", labelsOn); syncLabels() }
syncLabels()
const syncRain = () => {
  for (const v of [loop, rain]) { v.hidden = !rainOn; rainOn && inView ? v.play().catch(() => {}) : v.pause() }
  rainBtn.setText(rainOn ? "Motion: on" : "Motion: off"); rainBtn.setAttr("aria-pressed", String(rainOn))
}
rainBtn.onclick = () => { rainOn = !rainOn; save("night-shift:rain", rainOn); syncRain() }
new IntersectionObserver(([e]) => { inView = e.isIntersecting; syncRain() }).observe(scene)
syncRain()

const drawer = el(stage, "aside", "ns-drawer")
drawer.hidden = true
const buttons = {}, glows = {}
// an object stays lit while hovered, focused or while its drawer is open
const lit = (id, on) => glows[id]?.toggleClass("on", on || buttons[id]?.getAttr("aria-expanded") === "true")
// One order for the number keys, the arrows and the drawer's previous/next: the strip's objects first, then the rest.
const NAV = ["projects", "inbox", "tooling", "daily", "jobs", "orphans", "pins", "games", "fleet", "library", "mart", "news"].filter(id => SPOTS.some(s => s.id === id))
let openId = null, closing = null
const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches
// every way of closing (x, Escape, a click outside) puts focus back on the object that opened the drawer, or the strip
const close = (refocus = true) => {
  if (!openId) return
  const was = openId; openId = null; save("night-shift:open", null)
  for (const [k, b] of Object.entries(buttons)) { b.setAttr("aria-expanded", "false"); lit(k, false) }
  for (const r of listView?.querySelectorAll(".ns-lv-row") ?? []) r.setAttr("aria-expanded", "false")
  hideTip()
  const done = () => { drawer.hidden = true; drawer.removeClass("closing"); closing = null }
  if (reduced()) done(); else { drawer.addClass("closing"); closing = setTimeout(done, 90) }
  // in list mode the scene's buttons are hidden, so focus goes back to the list row
  const back = root.hasClass("list-mode") ? listView?.querySelector(`.ns-lv-row[data-id="${was}"]`) : buttons[was]
  if (refocus) (back ?? strip.querySelector(`[data-id="${was}"]`))?.focus({ preventScroll: true })
}
const open = (id, focus) => {
  const spot = SPOTS.find(s => s.id === id)
  if (!spot) return close(false)
  clearTimeout(closing); drawer.removeClass("closing")
  openId = id
  drawer.empty(); drawer.hidden = false; save("night-shift:open", id)
  for (const [k, b] of Object.entries(buttons)) { b.setAttr("aria-expanded", String(k === id)); lit(k, false) }
  for (const r of listView?.querySelectorAll(".ns-lv-row") ?? []) r.setAttr("aria-expanded", String(r.dataset.id === id))
  const ttl = el(drawer, "div", "ns-ttl"); el(ttl, "h3", null, spot.label); icon(ttl, id)
  const x = el(drawer, "button", "ns-close", "×")
  x.setAttrs({ "aria-label": "Close " + spot.label, type: "button" }); tip(x, TIPS.close)
  x.onclick = () => close()
  spot.fill(drawer)
  const i = NAV.indexOf(id)
  if (i >= 0 && NAV.length > 1) {
    const prev = SPOTS.find(s => s.id === NAV[(i + NAV.length - 1) % NAV.length]), next = SPOTS.find(s => s.id === NAV[(i + 1) % NAV.length])
    const nav = el(drawer, "div", "ns-acts ns-nav") // ns-nav: local, so the offline state leaves these alone
    nav.style.justifyContent = "space-between"
    for (const [s, text, side] of [[prev, `← ${prev.label}`, 0], [next, `${next.label} →`, 1]]) {
      const b = el(nav, "button", "ns-act", text); b.type = "button"; tip(b, `Go to the ${s.label} panel.`)
      b.onclick = () => { open(s.id, false); drawer.querySelectorAll(".ns-nav button")[side]?.focus() } // focus stays on the same side
    }
  }
  if (root.hasClass("offline")) setOffline(true)
  lit(id, true)
  if (focus) x.focus()
}
// a click in the dashboard outside the drawer closes it; another object or a strip count switches instead
root.addEventListener("pointerdown", (e) => {
  if (!openId || drawer.contains(e.target) || e.target.closest(".ns-spot, .ns-count, .ns-lv-row, .ns-tip, .ns-notes, .ns-corner")) return
  close()
})
const step = (d) => { const i = NAV.indexOf(openId); open(NAV[(i + d + NAV.length) % NAV.length], false); drawer.querySelector(".ns-close")?.focus() }
// In Live Preview this block sits inside the note's editor: a key handled here must stop, or the editor takes focus back.
const handled = (e) => { e.preventDefault(); e.stopPropagation() }
root.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { if (tipBox) { handled(e); return hideTip() } if (openId) { handled(e); close() } return } // a tooltip first
  if (e.key === "Alt") { handled(e); syncLabels(true); return }
  if (e.ctrlKey || e.metaKey || e.altKey || e.target.closest("input, textarea")) return // typing is never caught
  const n = Number(e.key)
  if (Number.isInteger(n) && n >= 1 && n <= Math.min(9, NAV.length)) { handled(e); open(NAV[n - 1], true); return }
  if (openId && (e.key === "ArrowRight" || e.key === "ArrowLeft")) { handled(e); step(e.key === "ArrowRight" ? 1 : -1) }
})
root.addEventListener("keyup", (e) => { if (e.key === "Alt") { handled(e); syncLabels() } }) // Electron opens its menu on a lone Alt release
window.removeEventListener("blur", window.nsBlur ?? (() => {})) // Dataview re-runs this block: one listener only
window.nsBlur = () => syncLabels()
window.addEventListener("blur", window.nsBlur)
scene.tabIndex = -1 // a click on the picture keeps the keys working
scene.style.outline = "none"

// masks first, under every button; smaller boxes stack above larger ones where they overlap
const placed = SPOTS.filter(s => RENDERED[s.id]?.box ?? s.box)
const area = (s) => (RENDERED[s.id]?.box ?? s.box)[2] * (RENDERED[s.id]?.box ?? s.box)[3]
for (const s of SPOTS) {
  const mask = RENDERED[s.id]?.mask && src(RENDERED[s.id].mask)
  if (!mask) continue
  const g = el(scene, "div", "ns-glow"), inner = g.createDiv()
  inner.style.backgroundImage = `url("${sceneSrc}")`
  inner.style.maskImage = inner.style.webkitMaskImage = `url("${mask}")`
  glows[s.id] = g
}
[...placed].sort((a, b) => area(b) - area(a)).forEach((s, i) => {
  const b = el(scene, "button", "ns-spot")
  const [l, t, w, h] = RENDERED[s.id]?.box ?? s.box
  b.style.cssText = `left:${l}%;top:${t}%;width:${w}%;height:${h}%;z-index:${i + 1}`
  b.setAttrs({ type: "button", "aria-label": s.label, "aria-expanded": "false", "aria-controls": "ns-drawer" })
  const tag = el(b, "span", "ns-tag", s.label); tip(b, `Opens the ${s.label} panel.`)
  const k = NAV.indexOf(s.id) + 1
  if (k >= 1 && k <= 9) { tag.dataset.key = String(k); b.setAttr("aria-keyshortcuts", String(k)) }
  if (s.warn) el(b, "span", "ns-dot")
  b.onclick = () => openId !== s.id ? open(s.id, true) : close()
  b.onmouseenter = b.onfocus = () => lit(s.id, true)
  b.onmouseleave = b.onblur = () => lit(s.id, false)
  buttons[s.id] = b
})
drawer.id = "ns-drawer"

// the list: every panel in the keys' order, with its count and the same "needs a look" mark as the strip
const SUMMARY = { projects: [projects.length, "projects"], inbox: [inbox.length, "waiting"], tooling: [drift.length, "to update"],
  daily: [`${kept}/7`, "days logged"], jobs: jobs ? [jobs.due, "follow-ups due"] : null, orphans: [orphans.length, "orphans"],
  pins: [pins.length, "open"], library: [dv.pages('"resources"').length, "notes"], news: [news.length, "new changes"] }
listView = createDiv({ cls: "ns-listview" })
stage.insertBefore(listView, drawer)
el(listView, "h2", "ns-lv-h", "Night Shift")
const lvList = el(listView, "ul", "ns-lv")
for (const id of [...NAV, ...SPOTS.map(s => s.id).filter(i => !NAV.includes(i))]) {
  const s = SPOTS.find(x => x.id === id), sm = SUMMARY[id]
  const b = el(el(lvList, "li"), "button", "ns-lv-row" + (s.warn ? " warn" : ""))
  b.type = "button"; b.dataset.id = id; b.setAttrs({ "aria-expanded": "false", "aria-controls": "ns-drawer" })
  icon(b, id); el(b, "span", "nm", s.label)
  if (sm) { el(b, "span", "v", String(sm[0])); el(b, "span", "u", sm[1]) }
  if (s.warn) el(b, "span", "look", "needs a look")
  tip(b, `Opens the ${s.label} panel.`)
  b.onclick = () => openId !== id ? open(id, true) : close()
}
syncView = () => {
  const on = listOn || sceneFailed
  root.toggleClass("list-mode", on); listView.hidden = !on; scene.hidden = on; corner.hidden = on
  if (viewBtn) {
    viewBtn.setText(sceneFailed ? "Scene unavailable" : on ? "Scene view" : "List view"); viewBtn.disabled = sceneFailed
    sceneFailed ? viewBtn.removeAttribute("aria-pressed") : viewBtn.setAttr("aria-pressed", String(on))
  }
}

// --- live state: poll the dashboard server (_dashboard/actions.py, nightshift.py) while the scene is on screen ----
// Live state is polled and never written into the vault (Dataview re-runs on vault changes; Syncthing would churn).
const { requestUrl } = require("obsidian")
const API = "http://127.0.0.1:8790", HDR = { "X-Night-Shift": "1" }
const applyStates = (objs) => {
  for (const [id, g] of Object.entries(glows)) {
    const o = objs[id]
    const fresh = o?.state === "ok" && o.finished && Date.now() - Date.parse(o.finished) < 8000
    const st = o && (o.state === "running" || o.state === "failed" || fresh) ? o.state : null
    st ? g.setAttr("data-st", st) : g.removeAttribute("data-st")
  }
}
// bottom right of the scene: a "server offline" chip, and a note when an action started here finishes
const notes = el(stage, "div", "ns-notes")
notes.setAttrs({ role: "status", "aria-live": "polite" })
let chip = null, lastAnswer = null
const OFFLINE_TIP = "The dashboard server on 127.0.0.1:8790 is not answering. Start it with the SecondBrain-Dashboard task."
function setOffline(off) {
  root.toggleClass("offline", off)
  if (off && !chip) chip = el(notes, "div", "ns-chip")
  const text = lastAnswer ? `Server offline · last answer ${Math.max(1, Math.round((Date.now() - lastAnswer) / 60000))} min ago` : "Server offline"
  if (chip && chip.textContent !== text) chip.setText(text) // only on change: the chip sits in a live region
  if (!off) { chip?.remove(); chip = null }
  for (const b of root.querySelectorAll("button.ns-act")) {
    if (b.closest(".ns-nav")) continue
    if (off && b.dataset.tipOn === undefined) { b.dataset.tipOn = b.dataset.tip ?? ""; b.dataset.tip = OFFLINE_TIP; b.disabled = true }
    if (!off && b.dataset.tipOn !== undefined) { b.dataset.tip = b.dataset.tipOn; delete b.dataset.tipOn; if (!b.hasClass("busy")) b.disabled = false }
  }
}
const poll = async () => {
  if ((!inView && !root.hasClass("list-mode")) || !root.isConnected) return // the hidden scene is never "in view" in list mode
  try {
    applyStates((await requestUrl({ url: API + "/api/night-shift", headers: HDR })).json.objects)
    lastAnswer = Date.now(); setOffline(false)
  } catch { setOffline(true) } // server down: keep the last glow
}
const actionState = async (id) => { try { return (await requestUrl({ url: `${API}/actions/${id}`, headers: HDR })).json } catch { return null } }
// waits for a started action to stop running (2 s steps, up to 4 min; a few failed reads are a blip, not a result).
// Returns its last state, or null when it is unknown (the server stopped answering, or it is still running).
async function finished(id) {
  let misses = 0
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const s = await actionState(id)
    if (!s) { if (++misses >= 5) return null; continue }
    misses = 0
    if (s.status !== "running") return s
  }
  return null
}
function note(text, fail, logId) {
  const n = el(notes, "div", "ns-note" + (fail ? " fail" : ""))
  el(n, "span", null, text)
  if (fail && logId) {
    const rb = el(n, "button", null, "Read log"); rb.type = "button"; tip(rb, TIPS.readlog)
    rb.onclick = async () => {
      let t = "(no log)"
      try { t = (await requestUrl({ url: `${API}/api/night-shift/log/${logId}`, headers: HDR })).json.text || "(empty)" } catch {}
      const pre = createEl("pre", { text: t.split("\n").slice(-12).join("\n") }); pre.tabIndex = -1
      rb.replaceWith(pre); pre.focus() // keyboard focus moves to the log, not lost with the button
    }
  }
  const x = el(n, "button", null, "×"); x.type = "button"; x.setAttr("aria-label", "Dismiss"); tip(x, "Dismiss this note.")
  x.onclick = () => n.remove()
  if (!fail) setTimeout(() => n.remove(), 8000) // a failure stays until dismissed
}
// starts an action; with its button, the button shows Starting..., then the result for 4 s. Returns true once started.
async function runAction(id, text, btn) {
  const label = btn?.textContent
  const set = (cls, t) => { if (!btn) return; btn.removeClass("busy", "done", "bad"); if (cls) btn.addClass(cls); btn.setText(t) }
  if (btn) { btn.disabled = true; set("busy", "Starting…") }
  let started = false
  try {
    const r = await requestUrl({ url: `${API}/actions/${id}`, method: "POST", throw: false,
      headers: text === undefined ? HDR : { ...HDR, "content-type": "application/json" },
      body: text === undefined ? undefined : JSON.stringify({ text }) })
    started = r.status === 202
    if (!started) new Notice(r.status === 409 ? "Already running." : r.status === 422 ? `That text is not accepted (${(text ?? "").trim().length} characters sent; it must be 1 to 150, and a clip link must start with http).` : `Could not start (${r.status}).`)
  } catch { new Notice("Dashboard server is not reachable on 127.0.0.1:8790."); setOffline(true) }
  poll()
  if (!btn) return started
  if (!started) { set(null, label); btn.disabled = root.hasClass("offline"); return false }
  ;(async () => {
    const s = await finished(id)
    if (!s) { set(null, label); btn.disabled = root.hasClass("offline"); note(`${label}: no result yet. Its glow on the scene shows when it ends.`, false, null); return }
    const ok = s.status === "ok", session = s.kind === "session"
    set(ok ? "done" : "bad", ok ? (session ? "Opened in VS Code ✓" : "Done ✓") : s.status === "timeout" ? "Timed out" : "Failed")
    if (!session) note(`${label} ${ok ? "finished" : s.status === "timeout" ? "timed out" : "failed"}.`, !ok, id)
    else if (!ok) note(`${label} could not open VS Code.`, true, null)
    setTimeout(() => { if (btn.isConnected) { set(null, label); btn.disabled = root.hasClass("offline") } }, 4000)
  })()
  return true
}
// a panel's only action is its main (filled) button
function acts(parent, items) {
  const box = el(parent, "div", "ns-acts")
  for (const [label, id, hint] of items) {
    const b = el(box, "button", "ns-act" + (items.length === 1 ? " pri" : ""), label)
    b.type = "button"; tip(b, hint ?? TIPS[id]); b.onclick = () => runAction(id, undefined, b)
  }
}
// One delegated tooltip for every button (and anything with data-tip) in this note, present and future: shown 1 s after
// hover or keyboard focus. WCAG 1.4.13: it stays while the pointer is on the button or on the tooltip itself, and Escape
// dismisses it without moving anything (the root keydown handler). Text: data-tip, else aria-label, else the label.
let tipBox = null, tipTimer = null, tipHide = null
// a hover tooltip shows while focus sits elsewhere (usually the note editor), so Escape is caught on the document while one is up
const tipEsc = (e) => { if (e.key === "Escape" && tipBox) { e.preventDefault(); e.stopPropagation(); hideTip() } }
const hideTip = () => { clearTimeout(tipTimer); clearTimeout(tipHide); tipBox?.remove(); tipBox = null; document.removeEventListener("keydown", tipEsc, true) }
const showTip = (b) => {
  const text = b.dataset.tip || b.getAttr("aria-label") || b.textContent.trim()
  if (!text || !b.isConnected) return
  hideTip()
  tipBox = el(root, "div", "ns-tip", text); tipBox.setAttr("role", "tooltip")
  tipBox.onpointerenter = () => clearTimeout(tipHide)
  tipBox.onpointerleave = () => { tipHide = setTimeout(hideTip, 150) }
  document.addEventListener("keydown", tipEsc, true)
  const r = root.getBoundingClientRect(), t = b.getBoundingClientRect(), w = tipBox.offsetWidth, h = tipBox.offsetHeight
  const below = t.bottom - r.top + 6
  tipBox.style.left = Math.max(8, Math.min(t.left - r.left, r.width - w - 8)) + "px"
  tipBox.style.top = (below + h > r.height ? t.top - r.top - h - 6 : below) + "px"
}
let tipFor = null
const armTip = (e) => {
  if (tipBox?.contains(e.target)) return
  const b = e.target.closest?.("button, [data-tip]"); if (!b || !root.contains(b)) return
  clearTimeout(tipHide)
  if (b === tipFor && tipBox) return // moving between a button's own children
  hideTip(); tipFor = b; tipTimer = setTimeout(() => showTip(b), 1000)
}
root.addEventListener("pointerover", armTip)
root.addEventListener("focusin", armTip)
root.addEventListener("pointerout", (e) => {
  const b = e.target.closest?.("button, [data-tip]")
  if (!b || b.contains(e.relatedTarget) || tipBox?.contains(e.relatedTarget)) return
  clearTimeout(tipTimer); tipHide = setTimeout(hideTip, 150) // a moment to move onto the tooltip
})
root.addEventListener("focusout", (e) => { if (!tipBox?.contains(e.relatedTarget)) hideTip() })
for (const ev of ["pointerdown", "wheel"]) root.addEventListener(ev, (e) => { if (!tipBox?.contains(e.target)) hideTip() }, { passive: true })
clearInterval(window.nsPoll) // Dataview re-runs this block: one poller only
window.nsPoll = setInterval(poll, 5000)
poll()

if (news.length) {
  const toast = el(stage, "div", "ns-toast", news.map(k => `${NAMES[k]}: ${prev[k]} to ${snap[k]}`).join(". "))
  toast.setAttr("role", "status")
  setTimeout(() => toast.remove(), 8000)
}

const strip = el(root, "div", "ns-strip")
// counts that need a look come first and say so in words, not only in pink (WCAG 1.4.1)
const counts = [
  ["projects", projects.length, "projects", false],
  ["inbox", inbox.length, "in the inbox", inbox.length > 10],
  ["tooling", drift.length, "tools to update", drift.length > 0],
  ["daily", `${kept}/7`, "days logged", kept < 4],
  ...(jobs ? [["jobs", jobs.due, "follow-ups due", jobs.due > 0]] : []),
  ["orphans", orphans.length, "orphan notes", orphans.length > 20],
  ["pins", pins.length, "pins open", false],
]
for (const [id, n, label, warn] of [...counts.filter(c => c[3]), ...counts.filter(c => !c[3])]) {
  const b = el(strip, "button", "ns-count" + (warn ? " warn" : ""))
  b.type = "button"; b.dataset.id = id
  el(b, "b", null, String(n)); b.appendText(" " + label)
  if (warn) el(b, "span", "look", "needs a look")
  tip(b, `Opens the ${SPOTS.find(s => s.id === id)?.label ?? id} panel.`)
  b.onclick = () => open(id, true)
}
// the list switch sits in the strip so it is always on screen, in either view
viewBtn = el(strip, "button", "ns-count ns-view")
viewBtn.type = "button"; tip(viewBtn, "Swap the picture for a plain list of every panel, or back.")
viewBtn.onclick = () => { listOn = !listOn; save("night-shift:list", listOn); syncView(); if (openId) open(openId, false) }
syncView()

if (missing.length) root.insertBefore(createDiv({ cls: "ns-alarm", text: `Missing art: ${missing.join(", ")}. Rebuild with scripts/night_shift_looks.py -- d and scripts/night_shift_spots.py (see projects/night-shift.md).` }), stage)

const last = load("night-shift:open", null)
if (last) open(last, false)
// Dataview can start a second run, in a container of its own, while this one awaits file reads (the vault changed
// mid-render): the run that finishes last removes the other copy in the same pane, so one dashboard shows
const pane = root.closest(".workspace-leaf")
for (const n of pane?.querySelectorAll(".ns") ?? []) if (n !== root) n.remove()
```

## Related

- [[projects/night-shift|Night Shift project note]]**
