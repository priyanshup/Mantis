"""What changed, and which card summaries are behind (MANTIS-IMP-043, MANTIS-IMP-044). Stdlib only.

Called by build_map.py; writes map/changes.json for the site's What's new page:

    events   one row per change, newest first: new sources, questions raised, answers and likely
             answers, possible conflicts, decisions, roadmap stage changes, pages and Jira items
             updated, card summaries refreshed, diagrams registered.
    refresh  cards whose curated summary has fallen behind its sources, with the reason, the cards
             the owner follows first.

Most events come from dates the knowledge base already records (a digest's generated_on, an
entry's Date raised, dated notes, a decision's Date). Changes that leave no date behind (a
stage moving from Discovery to Build, a story moving to in-jira, an entry closing) are found by
comparing with the state saved at the previous rebuild in mantis/knowledge/changelog.json and
logged with the day they were first seen. The log keeps 180 days.

    python tools/changes.py [DAYS]     print the last DAYS (default 7) of changes, for a status update
"""
import json, re, sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
K = M / "knowledge"
LOG = K / "changelog.json"
KEEP_DAYS = 180
ID_RE = re.compile(r"\s*\(?MANTIS-[A-Z]+-\d+(?:\s*[,;/]\s*MANTIS-[A-Z]+-\d+)*\)?")
DATED_NOTE = re.compile(r"(?m)^- \*\*([^*(]+?) \((\d{4}-\d{2}-\d{2})\):\*\*\s*(.*)")
STAGES = {"none": "Not started", "discovery": "Discovery", "refinement": "Refinement", "build": "Build", "live": "Live"}
WORK = {"draft": "Draft", "review": "In review", "in-jira": "In Jira", "done": "Done", "published": "Published"}


def plain(text, limit=180):
    t = " ".join(ID_RE.sub("", text or "").split())
    t = re.sub(r"\s*([,;])(\s*[,;])+", r"\1", t)   # ",;" left where an ID was
    t = re.sub(r"\s+(?:to|in|see|from|and|by|of|with)$", "", t.strip(" ;,."))   # a word that pointed at a removed ID
    t = re.sub(r"[*_`]", "", t).strip(" ;,.")
    return t if len(t) <= limit else t[:limit - 1].rsplit(" ", 1)[0] + "…"


def qkey(rid):
    """The key the Open items page knows an entry by, without exposing its ID."""
    import hashlib
    return hashlib.sha1(rid.encode("utf-8")).hexdigest()[:10]


def card_href(c):
    return f"{c['folder']}/{c['slug']}.html"


def _load():
    try:
        return json.loads(LOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state": None, "events": []}


def build(docs, all_cards, features, regs, work, assets, focus, today=None):
    """regs: {"gap": {...}, "assumption": {...}, "conflict": {...}} from build_map.registers()."""
    import textcache
    today = today or date.today()
    iso = today.isoformat()
    events = []
    cards_of = {}
    for c in all_cards:
        for d in c["linked"]:
            cards_of.setdefault(d, []).append(c)
    first_card = lambda ds: next((c for d in ds for c in cards_of.get(d, [])), None)

    def add(day, kind, title, detail="", href="", card=None, key="", what=""):
        if not day or not re.match(r"\d{4}-\d{2}-\d{2}$", day[:10]):
            return
        events.append({"date": day[:10], "kind": kind, "title": plain(title, 160), "detail": plain(detail, 240), "href": href,
                       "card": card["title"] if card else "", "card_href": card_href(card) if card else "", "key": key, "what": what})

    # 1. New sources
    for did, fm in docs.items():
        c = first_card([did])
        add(fm.get("generated_on", ""), "source", fm.get("original_title", did), "", card_href(c) if c else "", c, did)

    # 2. Questions, answers, likely answers and conflicts, from the registers' own dates
    for kind, reg in regs.items():
        folder = {"gap": "gaps", "assumption": "assumptions", "conflict": "conflicts"}[kind]
        for rid, r in reg.items():
            c = first_card(r["docs"])
            href = f"review.html#k={qkey(rid)}"   # an opaque key: IDs never reach a page
            status = r.get("status_raw", "")
            if kind == "conflict" and status.lower().startswith("unconfirmed"):
                add(r["raised"], "possible", r["topic"], "Two sources may disagree. Confirm or dismiss it on Open items.", href, c, rid)
            else:
                add(r["raised"], "question" if kind == "gap" else kind, r["topic"], "", href, c, rid)
            m = re.match(r"Potential Resolution \((\d{4}-\d{2}-\d{2})[:;,]?\s*(.*)", status, re.I)
            if m:
                add(m.group(1), "likely", r["topic"], m.group(2), href, c, rid)
            p = M / "knowledge" / "registers" / folder / f"{rid}.md"
            if p.exists():
                for label, day, text in DATED_NOTE.findall(textcache.read(p)):
                    label = label.strip()
                    if label.lower() in ("resolution", "owner answer"):
                        text = re.sub(r"^Source:[^.]*?\d{4}-\d{2}-\d{2}\.?\s*", "", text.strip())
                        add(day, "answer", r["topic"], text, href, c, rid)

    # 3. Decisions
    for p in sorted((K / "registers" / "decisions").glob("MANTIS-DEC-*.md")):
        t = textcache.read(p)
        d = (re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", t) or [None, ""])[1]
        what = (re.search(r"\*\*Decision:\*\*\s*(.+)", t) or [None, ""])[1]
        src = (re.search(r"\*\*Sources/knowledge it was based on:\*\*\s*(.+)", t) or [None, ""])[1]
        add(d, "decision", what, "", "library.html#decisions", first_card(re.findall(r"MANTIS-DOC-\d{4}", src)), p.stem)

    # 4. Card summaries refreshed, diagrams registered, pages and Jira items updated
    for c in all_cards:
        if c["fm"].get("updated"):
            add(c["fm"]["updated"], "summary", c["title"], "", card_href(c), c, "card:" + c["slug"])
    for a in assets:
        p = K / "registers" / "assets" / f"{a['id']}.md"
        d = (re.search(r"\*\*Date registered:\*\*\s*(\d{4}-\d{2}-\d{2})", textcache.read(p)) or [None, ""])[1] if p.exists() else ""
        add(d, "diagram", a["title"], a["type"].replace("-", " "), "library.html#diagrams", first_card(a["docs"]), a["id"])
    for x in work:
        c = next((k for k in all_cards if k["slug"] == x["feature"]), None)
        label = "Epic" if x["kind"] == "epic" else "Story" if x["kind"] == "story" else "Page"
        add(x.get("updated", ""), "page", x["title"], "", x.get("href", ""), c, "work:" + x["file"], what=label)

    # 5. Changes that leave no date: compare with the last rebuild's state
    state = {"stage": {f["slug"]: f["status"] for f in features},
             "entry": {rid: r["status"].split(" ")[0] for reg in regs.values() for rid, r in reg.items()},
             "work": {x["file"]: x["status"] for x in work}}
    log = _load()
    old = log.get("state")
    logged = [e for e in log.get("events", []) if e["date"] >= (today - timedelta(days=KEEP_DAYS)).isoformat()]
    if old:
        for slug, st in state["stage"].items():
            was = old.get("stage", {}).get(slug)
            if was and was != st:
                c = next((k for k in all_cards if k["slug"] == slug), None)
                logged.append({"date": iso, "kind": "stage", "title": c["title"] if c else slug,
                               "detail": f"{STAGES.get(was, was)} → {STAGES.get(st, st)}", "href": card_href(c) if c else "",
                               "card": "", "card_href": "", "key": f"stage:{slug}:{st}"})
        for rid, st in state["entry"].items():
            was = old.get("entry", {}).get(rid)
            if was and was != st and st.lower() in ("closed", "confirmed", "corrected", "resolved", "promoted", "deferred"):
                reg = next(r for r in regs.values() if rid in r)
                c = first_card(reg[rid]["docs"])
                logged.append({"date": iso, "kind": "closed", "title": plain(reg[rid]["topic"], 160), "detail": f"{was} → {st}",
                               "href": f"review.html#k={qkey(rid)}", "card": c["title"] if c else "", "card_href": card_href(c) if c else "",
                               "key": f"closed:{rid}"})
        for f, st in state["work"].items():
            was = old.get("work", {}).get(f)
            if was and was != st:
                x = next(w for w in work if w["file"] == f)
                logged.append({"date": iso, "kind": "jira" if st == "in-jira" else "page", "title": x["title"],
                               "detail": f"{WORK.get(was, was)} → {WORK.get(st, st)}", "href": x.get("href", ""),
                               "card": "", "card_href": "", "key": f"work:{f}:{st}"})
    if old != state or len(logged) != len(log.get("events", [])):
        LOG.write_text(json.dumps({"_note": "Written by tools/changes.py on every rebuild: the last state seen and the changes that left no date behind. Safe to delete; history then restarts.",
                                   "state": state, "events": logged}, indent=1, ensure_ascii=False), encoding="utf-8")

    seen, out = set(), []
    for e in sorted(events + logged, key=lambda e: (e["date"], e["kind"]), reverse=True):
        k = (e["date"], e["kind"], e["key"] or e["title"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    out = [e for e in out if e["date"] <= iso][:600]

    # Cards whose summary is behind, with the reason (MANTIS-IMP-044)
    following, archived = focus.get("following", []), set(focus.get("archived", []))
    refresh = []
    for c in all_cards:
        if not c["new"] or c["slug"] in archived:
            continue
        added = sorted(docs[d].get("generated_on", "")[:10] for d in c["new"] if docs[d].get("generated_on"))
        oldest = (today - date.fromisoformat(added[0])).days if added else None
        upd = c["fm"].get("updated", "")
        why = f"{len(c['new'])} new source{'s' if len(c['new']) != 1 else ''} since the summary"
        why += f" was last updated on {date.fromisoformat(upd).strftime('%d %b')}" if re.match(r"\d{4}-\d{2}-\d{2}$", upd) else " was written"
        if oldest is not None:
            why += f"; the oldest has waited {oldest} day{'s' if oldest != 1 else ''}"
        refresh.append({"slug": c["slug"], "title": c["title"], "href": card_href(c), "new": len(c["new"]), "oldest_days": oldest,
                        "followed": c["slug"] in following, "rank": following.index(c["slug"]) if c["slug"] in following else 99,
                        "why": why, "titles": [plain(docs[d].get("original_title", ""), 90) for d in c["new"][:4]]})
    refresh.sort(key=lambda r: (not r["followed"], r["rank"], -(r["oldest_days"] or 0)))
    return {"today": iso, "events": out, "refresh": refresh, "timeline": timeline(docs, all_cards, features, out, focus, today),
            "behind": behind(all_cards, work, today)}


SYNC = K / "output-sync.json"


def card_sections(text):
    """{section heading: text} of a card's curated part, to name what changed."""
    parts = re.split(r"(?m)^## ", re.sub(r"(?s)\A---\n.*?\n---\n", "", text))
    out = {"(top)": parts[0].strip()}
    for p in parts[1:]:
        head, _, body = p.partition("\n")
        out[head.strip()] = " ".join(body.split())
    return out


def behind(all_cards, work, today):
    """Pages, epics and stories whose card changed after they were written (MANTIS-IMP-070).

    When an output's `updated` date changes, the card's curated text is snapshotted with it
    (knowledge/output-sync.json): the output is taken to be in step with the card at that moment.
    Later, if the card's curated text differs from the snapshot, the output is behind, and the
    card sections that changed are named so the update can be targeted. An output that copies
    someone else's text verbatim (front matter `track_card: false`) is never flagged. For outputs
    that had no snapshot before this existed, the first check compares dates and says so."""
    import hashlib, frontmatter
    try:
        sync = json.loads(SYNC.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sync = {}
    cards = {c["slug"]: c for c in all_cards}
    found, changed = [], False
    for x in work:
        c = cards.get(x.get("feature"))
        f = M / x["file"]
        if not c or not f.exists():
            continue
        fm = frontmatter.parse(f.read_text(encoding="utf-8"))
        if str(fm.get("track_card", "")).lower() == "false":
            continue
        cur = card_sections(c["curated"])
        h = hashlib.sha1(json.dumps(cur, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        out_upd, card_upd = x.get("updated", ""), c["fm"].get("updated", "")
        out_hash = hashlib.sha1(f.read_bytes()).hexdigest()[:12]
        rec = sync.get(x["file"])
        # In step from here when the output is new, its `updated` date moved, or its text was edited since the
        # snapshot (a second update on the same day leaves the date unchanged; MANTIS-IMP-091).
        edited = rec is not None and rec.get("out_hash") not in (None, out_hash)
        if rec is None or rec.get("updated") != out_upd or edited:
            if rec is None and card_upd > out_upd:   # no snapshot from before: the dates are all we know
                sync[x["file"]] = {"updated": out_upd, "card_hash": "", "sections": {}, "out_hash": out_hash}
            else:
                sync[x["file"]] = {"updated": out_upd, "card_hash": h, "sections": cur, "out_hash": out_hash}
            changed = True
            rec = sync[x["file"]]
        elif "out_hash" not in rec:
            rec["out_hash"] = out_hash
            changed = True
        if rec["card_hash"] == h:
            continue
        if rec["card_hash"]:
            names = [k for k in cur if rec["sections"].get(k) != cur[k]] + [f"{k} (removed)" for k in rec["sections"] if k not in cur]
            why = "Its card changed since it was written: " + ", ".join("opening" if n == "(top)" else n for n in names[:6])
        else:
            why = f"Its card was updated on {card_upd}, after this was last updated on {out_upd or 'an unknown date'} (what changed was not recorded before 10 Oct 2026)"
        label = {"epic": "Epic", "story": "Story"}.get(x["kind"], "Page")
        found.append({"file": x["file"], "title": x["title"], "kind": label, "href": x.get("href", ""), "card": c["title"],
                      "card_file": c["path"].relative_to(M).as_posix(), "why": why})
    if changed:
        SYNC.write_text(json.dumps({"_note": "Written by tools/changes.py: each output's card as it was when the output was last updated.",
                                    **{k: v for k, v in sync.items() if k != "_note"}}, indent=1, ensure_ascii=False), encoding="utf-8")
    return found


def timeline(docs, all_cards, features, events, focus, today, back=8, ahead=10):
    """The Timeline page (MANTIS-IMP-052): one row per roadmap feature over 8 weeks back and 10 ahead.
    Each row shows when sources and decisions arrived (activity), stage moves, and dated things ahead:
    next steps with a due date, follow-ups with a chase date, regular meetings on the card. Time away
    spans every row. Dates are only ever taken from the knowledge base, never estimated."""
    import steps as steps_mod, followups, schedule
    start = today - timedelta(days=today.weekday() + 7 * back)
    end = start + timedelta(weeks=back + ahead)
    inside = lambda d: d and start.isoformat() <= d[:10] < end.isoformat()
    archived = set(focus.get("archived", []))
    following = focus.get("following", [])
    rows = {}
    for f in features:
        if f["slug"] in archived:
            continue
        rows[f["slug"]] = {"slug": f["slug"], "title": f["title"], "status": f["status"], "href": f"features/{f['slug']}.html",
                           "followed": f["slug"] in following, "rank": following.index(f["slug"]) if f["slug"] in following else 99, "marks": []}
    card = {c["slug"]: c for c in all_cards}
    for slug, r in rows.items():
        for d in card[slug]["linked"] if slug in card else []:
            day = docs[d].get("generated_on", "")[:10]
            if inside(day):
                r["marks"].append({"date": day, "kind": "source", "label": plain(docs[d].get("original_title", ""), 90)})
    by_title = {r["title"]: r for r in rows.values()}
    for e in events:
        r = by_title.get(e.get("card")) or by_title.get(e.get("title")) if e["kind"] in ("decision", "stage", "possible", "conflict") else None
        if e["kind"] == "stage":
            r = by_title.get(e["title"])
        if r and inside(e["date"]):
            r["marks"].append({"date": e["date"], "kind": e["kind"], "label": plain(e["title"] + (": " + e["detail"] if e.get("detail") else ""), 120)})
    for s in steps_mod.load():
        if s["card"] in rows and s.get("due") and inside(s["due"]):
            rows[s["card"]]["marks"].append({"date": s["due"], "kind": "done" if s["done"] else "due", "label": plain(f"{s['step']} ({s['who']})", 120)})
    for person, g in followups.grouped().items():
        for f in g["items"]:
            if f.get("card") in rows and inside(f.get("chase", "")):
                rows[f["card"]]["marks"].append({"date": f["chase"], "kind": "chase", "label": plain(f"Chase {person}: {f['topic']}", 120)})
    for m in schedule.meetings():
        d = schedule.next_date(m, today)
        n = 0
        while d and inside(d.isoformat()) and n < 12:
            for c in m.get("cards", []):
                if c in rows:
                    rows[c]["marks"].append({"date": d.isoformat(), "kind": "meeting", "label": plain(f"{m['name']} ({m['time']})", 90)})
            d, n = d + timedelta(weeks=max(1, int(m.get("every", 1) or 1))), n + 1
    away = [{"start": a["start"], "end": a["end"], "label": "Away" + (f", cover {', '.join(a['cover'])}" if a.get("cover") else "")}
            for a in schedule.periods() if a["end"] >= start.isoformat() and a["start"] < end.isoformat()]
    ordered = sorted(rows.values(), key=lambda r: (not r["followed"], r["rank"], r["title"].lower()))
    for r in ordered:
        r["marks"].sort(key=lambda m: m["date"])
        past = [m for m in r["marks"] if m["date"] <= today.isoformat() and m["kind"] in ("source", "decision", "stage")]
        r["last"] = past[-1]["date"] if past else ""
    upcoming, seen = [], set()
    for m in sorted(([dict(m, card=r["title"], href=r["href"]) for r in ordered for m in r["marks"]
                      if m["date"] >= today.isoformat() and m["kind"] in ("due", "chase", "meeting")]), key=lambda m: m["date"]):
        if m["kind"] == "meeting":   # a regular meeting: only its next date
            if m["label"] in seen:
                continue
            seen.add(m["label"])
        upcoming.append(m)
    return {"start": start.isoformat(), "end": end.isoformat(), "today": today.isoformat(), "weeks": back + ahead,
            "rows": ordered, "away": away, "upcoming": upcoming[:30]}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # arrows and accents in titles, on a Windows console too
    if sys.argv[1:2] == ["mark"] and len(sys.argv) > 2:   # checked against the card, nothing to change (MANTIS-IMP-091)
        sync = json.loads(SYNC.read_text(encoding="utf-8")) if SYNC.exists() else {}
        for rel in sys.argv[2:]:
            rel = rel.replace("\\", "/").removeprefix("mantis/")
            if rel in sync:
                sync[rel]["card_hash"] = ""   # re-snapshot the card on the next rebuild
                sync[rel]["updated"] = "checked"
                print(f"{rel}: marked in step; the next rebuild records the card as it is now.")
            else:
                print(f"{rel}: not a tracked output.")
        SYNC.write_text(json.dumps(sync, indent=1, ensure_ascii=False), encoding="utf-8")
        sys.exit(0)
    if sys.argv[1:2] == ["behind"]:   # what to update after processing (docs/rules/workflow/answers.md, ingest.md)
        data = json.loads((K / "map" / "changes.json").read_text(encoding="utf-8"))
        rows = data.get("behind", [])
        for b in rows:
            print(f"{b['kind']} mantis/{b['file']} (card mantis/{b['card_file']}): {b['why']}.")
        print(f"{len(rows)} output(s) behind their card." if rows else "Every page, epic and story is in step with its card.")
        sys.exit(0)
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7 if len(sys.argv) > 1 else 7
    data = json.loads((K / "map" / "changes.json").read_text(encoding="utf-8"))
    since = (date.fromisoformat(data["today"]) - timedelta(days=days)).isoformat()
    for e in data["events"]:
        if e["date"] >= since:
            print(f"{e['date']} {e['kind']}: {e['title']}" + (f" ({e['detail']})" if e["detail"] else "") + (f" [{e['card']}]" if e["card"] else ""))
    for r in data["refresh"]:
        print(f"refresh {r['title']}: {r['why']}")
