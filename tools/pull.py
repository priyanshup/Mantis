"""Pull: what changed in Jira, Confluence and the inbox since the last pull, digested card by card (MANTIS-IMP-094).

The owner starts a pull ("pull" in chat, or the site's button). Code does steps 1 to 3 and 6. The AI does
only step 4, once per card, reading the changes alone (docs/rules/workflow/pull.md).

    python tools/pull.py                        1-3: fetch the active filters, set noise aside, print the plan
    python tools/pull.py plan [--rebuild]       the plan again without fetching (--rebuild first: after inbox digests)
    python tools/pull.py packet SLUG            4: one card's changes, compact, saved for citing ("none": items with no card)
    python tools/pull.py done SLUG [ID ...]     clear what the card pass digested (all the card's items, or the IDs given)
    python tools/pull.py skip ID [ID ...]       clear items that need no digest (unrelated to any card)
    python tools/pull.py headline SLUG "text"   the card's line for the brief, plain words (" | " between two lines)
    python tools/pull.py needs "text"           a line for "Needs you" in the brief
    python tools/pull.py finish                 6: rebuild once and write the Since-last-pull brief
    python tools/pull.py brief                  the last brief
    python tools/pull.py filters                the filters: label, type, value, active, last run, what it found
    python tools/pull.py filter add jira|confluence "Label" "value" [--off]
    python tools/pull.py filter set ID [--label X] [--value V] [--on | --off]
    python tools/pull.py filter remove ID
    python tools/pull.py filter test ID         how many items the filter selects now (one call, nothing saved)

Noise is set aside by code and never reaches the AI: a ticket whose only changes are its status,
parent or attachments, and a page edit that changed formatting only. The brief still counts them.
"""
import json, re, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import atl_client, atl_store, atl_updates, frontmatter, textcache

K = ROOT / "mantis" / "knowledge"
INBOX = ROOT / "mantis" / "00_inbox"
BRIEF = ROOT / "mantis" / "tasks" / "pull-brief.json"
PACKETS = "packets"            # under mantis/mirror/
CAP_ITEM, CAP_PACKET = 6000, 24000   # characters of diff per item and per packet; the rest is pointed to
NEW_ROW = re.compile(r"(?m)^\| (MANTIS-DOC-\d{4}) \| [^|]*\(new\) \| ([^|]*) \| ([^|]*) \|")


def say(msg=""):
    print(msg, flush=True)


def state():
    s = atl_updates.load_state()
    run = s.setdefault("run", {})
    for k, v in (("noise", {"jira": {}, "confluence": {}}), ("done", {}), ("headlines", {}), ("needs", []), ("skipped", [])):
        run.setdefault(k, v)
    return s


# ------------------------------------------------------------------ cards
def cards():
    """{slug: {"title", "path", "match", "followed"}}, followed cards first in the owner's order."""
    focus = json.loads((K / "focus.json").read_text(encoding="utf-8")) if (K / "focus.json").exists() else {}
    order = focus.get("following", [])
    out = {}
    for folder in ("features", "topics"):
        for p in sorted((K / folder).glob("*.md")):
            if p.name == "README.md" or p.stem in focus.get("archived", []):
                continue
            fm = frontmatter.parse(textcache.read(p))
            out[p.stem] = {"title": fm.get("title") or p.stem, "path": p, "match": set(fm.get("match_topics", [])),
                           "followed": p.stem in order}
    rank = {s: i for i, s in enumerate(order)}
    return dict(sorted(out.items(), key=lambda kv: (rank.get(kv[0], 999), kv[0])))


def new_sources(card):
    """[(doc, title, one-liner)] the card lists as new: linked, not yet in its summary."""
    return [(m.group(1), m.group(2).strip(), m.group(3).strip()) for m in NEW_ROW.finditer(textcache.read(card["path"]))]


def page_card(pid, row, cs):
    """The one card a page's changes go to: its digest's tags, else the relevance check's best card."""
    if row.get("doc"):
        p = ROOT / "mantis" / "02_digests" / f"{row['doc']}.md"
        tags = set(frontmatter.parse(textcache.read(p)).get("topics", [])) if p.exists() else set()
        best = max(cs, key=lambda s: (len(cs[s]["match"] & tags), cs[s]["followed"]), default=None)   # most shared tags, followed first
        if best and cs[best]["match"] & tags:
            return best
    return next((c for c in row.get("cards", []) if c in cs), "none")


def grouped(s, cs):
    """{slug: {"jira": [(key, row)], "confluence": [(pid, row)]}} for what waits, in card order, 'none' last.
    A ticket's card comes from the live mapping, so mapping it on Sources moves it at once."""
    out = {}
    idx, conf = atl_store.load_index("jira"), atl_client.load_config()
    for key, row in sorted(s["pending"]["jira"].items()):
        card = atl_updates.card_of(key, idx, conf)
        out.setdefault(card if card in cs else "none", {"jira": [], "confluence": []})["jira"].append((key, row))
    for pid, row in s["pending"]["confluence"].items():
        out.setdefault(page_card(pid, row, cs), {"jira": [], "confluence": []})["confluence"].append((pid, row))
    order = list(cs) + ["none"]
    return dict(sorted(out.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order)))


def passes(s, cs):
    """The cards with a pass this pull, in order: something waits for them, or they list new sources."""
    g = grouped(s, cs)
    return [slug for slug in cs if slug in g or new_sources(cs[slug])]


def month_digest(slug, month):
    """The card's pull digest for this month, if there is one: pulls add to it instead of making a document each time."""
    for p in sorted((ROOT / "mantis" / "02_digests").glob("MANTIS-DOC-*.md"), reverse=True):
        head = textcache.read(p)[:1500]
        if f"pull_card: {slug}" in head and f"pull_month: {month}" in head:
            return p.stem
    return ""


# ------------------------------------------------------------------ tickets no card owns: the owner maps or skips them
def top(key, idx):
    seen = set()
    while idx.get(key, {}).get("parent") and key not in seen:
        seen.add(key)
        key = idx[key]["parent"]
    return key


def unmapped():
    """Waiting tickets no card owns, grouped under their top Jira item: [{"root", "summary", "type", "keys"}]."""
    s, cs = state(), cards()
    idx = atl_store.load_index("jira")
    rows = {}
    for key, _ in grouped(s, cs).get("none", {}).get("jira", []):
        r = top(key, idx)
        e = rows.setdefault(r, {"root": r, "summary": idx.get(r, {}).get("summary", ""), "type": idx.get(r, {}).get("type", ""), "keys": []})
        e["keys"].append(key)
    return sorted(rows.values(), key=lambda e: -len(e["keys"]))


def map_ticket(root, card):
    """Map a Jira item (and everything under it) to a card, or skip it ("skip": never queued again)."""
    conf = atl_client.load_config()
    entry = next((e for e in unmapped() if e["root"] == root), None)
    if not entry:
        raise ValueError(f"{root} is not waiting for a card")
    if card == "skip":
        conf.setdefault("jira_skip", [])
        if root not in conf["jira_skip"]:
            conf["jira_skip"].append(root)
        atl_client.save_config(conf)
        cmd_skip(entry["keys"])
        return unmapped()
    if card not in cards():
        raise ValueError(f"no card '{card}'")
    m = conf.setdefault("card_jira", {}).setdefault(card, {"feature": None, "items": []})
    if root not in m.setdefault("items", []):
        m["items"].append(root)
    atl_client.save_config(conf)
    return unmapped()


# ------------------------------------------------------------------ 1-3: fetch, set noise aside, plan
def cmd_fetch():
    conf = atl_client.load_config()
    active = [f for f in atl_updates.filters(conf) if f.get("active")]
    s = state()
    s["run"].setdefault("started", atl_updates.now())
    atl_updates.save_state(s)
    say(f"Fetching {len(active)} active filter(s): " + ", ".join(f"{f['label']} ({f['type']})" for f in active))
    atl_updates.check(conf, log=say)
    s = state()
    noise = s["run"]["noise"]
    for key, row in list(s["pending"]["jira"].items()):
        if row.get("kinds") and set(row["kinds"]) <= atl_updates.NOISE:
            noise["jira"][key] = s["pending"]["jira"].pop(key)
    for pid, row in list(s["pending"]["confluence"].items()):
        if row.get("note") == "formatting only":
            s["base"][pid] = row["version"]
            noise["confluence"][pid] = s["pending"]["confluence"].pop(pid)
    atl_updates.save_state(s)
    for f in atl_updates.filters(atl_client.load_config()):
        if f.get("active"):
            n = f.get("last_counts", {})
            say(f"  {f['label']}: {n.get('new', 0)} new, {n.get('changed', 0)} changed")
    cmd_plan()


def inbox_files():
    if not INBOX.exists():
        return []
    return sorted(p.name for p in INBOX.iterdir() if p.is_file() and not p.name.startswith(("answers-", "edit-", ".")))


def cmd_plan(rebuild=False):
    if rebuild:
        build()
    s, cs = state(), cards()
    g = grouped(s, cs)
    news = {slug: new_sources(c) for slug, c in cs.items()}
    noise = s["run"]["noise"]
    say(f"\nPull plan, {atl_updates.now().replace('T', ' ')}")
    say(f"Set aside by code (no AI): {len(noise['jira'])} ticket(s) with status, parent or attachment changes only, "
        f"{len(noise['confluence'])} page(s) with formatting-only edits.")
    sent = [p.name for p in INBOX.glob("answers-*.md")] + [p.name for p in INBOX.glob("edit-*.md")] if INBOX.exists() else []
    if sent:
        say(f"From the site first: {', '.join(sent)} (pull.md, section 0).")
    files = inbox_files()
    if files:
        say(f"Inbox: {len(files)} file(s) to digest next (workflow/ingest.md, 'For each document'), then "
            f"`python tools/pull.py plan --rebuild`: {', '.join(files[:12])}")
    loose = unmapped()
    if loose:
        say(f"No card owns {sum(len(e['keys']) for e in loose)} ticket(s) under {len(loose)} Jira item(s): they wait on Sources "
            "for the owner to map or skip. Do not digest them.")
    todo = passes(s, cs)
    if not todo:
        say("Nothing to digest. Run `python tools/pull.py finish` for the brief.")
        return
    say("Card passes, followed cards first (python tools/pull.py packet <card>):")
    for slug in todo:
        jr, pg = g.get(slug, {}).get("jira", []), g.get(slug, {}).get("confluence", [])
        parts = []
        if jr:
            parts.append(f"{len(jr)} Jira (" + "; ".join(f"{k} {', '.join(r['changes'])[:60]}" for k, r in jr[:4]) + ("; ..." if len(jr) > 4 else "") + ")")
        if pg:
            parts.append(f"{sum(1 for _, r in pg if r['kind'] == 'changed')} page(s) changed, {sum(1 for _, r in pg if r['kind'] == 'new')} new")
        if news.get(slug):
            parts.append(f"{len(news[slug])} new source(s): {', '.join(d for d, _, _ in news[slug])}")
        say(f"  {slug}: " + ", ".join(parts))


# ------------------------------------------------------------------ 4: the packet for one card pass
def comments_tail(md, n):
    """The last n comments of a mirrored issue, as written there."""
    sec = re.search(r"(?ms)^## Comments.*?$(.*?)(?=^## |\Z)", md)
    if not sec or n <= 0:
        return ""
    parts = re.split(r"(?m)^(?=\*\*[^*\n]+, \d{4}-\d{2}-\d{2}:\*\*)", sec.group(1).strip())
    return "\n\n".join(p.strip()[:1500] for p in [x for x in parts if x.strip()][-n:])


def section(md, head, cap):
    m = re.search(r"(?ms)^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(head), md or "")
    t = m.group(1).strip() if m else ""
    return t[:cap] + ("\n[cut: the rest is in the mirror]" if len(t) > cap else "")


def jira_block(key, r):
    md = atl_store.read(f"jira/issues/{key}.md") or ""
    L = [f"### {key} [{r.get('type', '')}, {r.get('status', '')}]: {r.get('summary', '')}",
         f"Changes: {'; '.join(r['changes'])}. Updated {r.get('updated', '')}."]
    kinds = set(r.get("kinds") or [])
    if "new" in kinds or not kinds:   # a new issue, or a row queued before kinds were recorded: show it whole
        L += ["", "Description:", section(md, "Description", 2500) or "(none)"]
        tail = comments_tail(md, 3)
        if tail:
            L += ["", "Latest comments:", tail]
    else:
        if "description" in kinds:
            L += ["", "Description diff:", (atl_store.read(f"diffs/{key}.md") or "")[:CAP_ITEM]]
        if "comments" in kinds:
            L += ["", "New comments:", comments_tail(md, r.get("new_comments") or 1)]
        if "summary" in kinds:
            L += ["", "Summary is now: " + r.get("summary", "")]
    return "\n".join(L)


def page_block(pid, r):
    if r["kind"] == "changed":
        diff = atl_store.read(f"diffs/{pid}.md") or ""
        body = diff.split("\n", 3)[-1] if diff else ""
        cut = len(body) > CAP_ITEM
        return "\n".join([f"### {r['title']} (Confluence page {pid}): version {r.get('held') or '?'} to {r['version']}, "
                          f"{r['when']}, {r['by']}" + (f"; digest {r['doc']}" if r.get("doc") else ""),
                          f"{r['added']} line(s) added, {r['removed']} removed. Sections: {', '.join(r.get('sections', [])[:8]) or '-'}.",
                          "", body[:CAP_ITEM] + (f"\n[cut: full diff in mantis/mirror/diffs/{pid}.md]" if cut else "")])
    text = atl_store.read(f"confluence/pages/{pid}.md") or ""
    return "\n".join([f"### NEW PAGE: {r['title']} (Confluence page {pid}), {r['when']}, {r['by']}",
                      f"Not in Mantis yet; it needs its own digest. Full text ({len(text)} characters): "
                      f"mantis/mirror/confluence/pages/{pid}.md", "", text.split("\n---\n", 2)[-1][:2000].strip()])


def cmd_packet(slug):
    s, cs = state(), cards()
    g = grouped(s, cs).get(slug, {"jira": [], "confluence": []})
    card = cs.get(slug)
    title = card["title"] if card else "Items with no card"
    day = atl_updates.now()[:10]
    L = [f"# Jira and Confluence changes: {title}, {day}", "",
         "Made by code (tools/pull.py packet) from Jira and Confluence, showing only what changed since the last pull.", ""]
    if card:
        L += [f"Card: {card['path'].relative_to(ROOT).as_posix()}"]
        md = month_digest(slug, day[:7])
        L += [f"This month's pull digest: {md}. Add a dated section to it (pull.md, 3.2); no new DOC ID." if md else
              f"No pull digest for this card this month yet: a new one gets `pull_card: {slug}` and `pull_month: {day[:7]}` in its front matter."]
        try:
            items = json.loads((K / "map" / "open-items.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            items = []
        # A question on several cards is judged once: in the pass of its first card this pull (MANTIS-IMP-094)
        order = passes(s, cs)
        first = lambda o: next((c for c in order if c in o.get("features", [])), slug)
        on_card = [o for o in items if slug in o.get("features", []) and o["kind"] in ("gap", "assumption", "conflict")]
        mine, elsewhere = [o for o in on_card if first(o) == slug], [o for o in on_card if first(o) != slug]
        if mine:
            L += ["", "## Open questions on this card", ""] + [f"- {o['id']} [{o['status']}]: {o['topic'][:160]}" for o in mine]
        if elsewhere:   # short titles only: judge one here only if this card's own changes bear on it
            L += ["", "## Also touch this card (judged in their first card's pass, unless the changes below bear on one)", ""]
            L += [f"- {o['id']} ({first(o)}): {o['topic'].split(' (MANTIS-')[0][:90]}" for o in elsewhere]
        news = new_sources(card)
        if news:
            L += ["", "## New sources not yet in the card's summary (peek.py for more)", ""] + [f"- {d}: {t}. {one}" for d, t, one in news]
    budget, rest = CAP_PACKET, []
    for head, rows, fn in (("Jira", g["jira"], jira_block), ("Confluence", g["confluence"], page_block)):
        if not rows:
            continue
        L += ["", f"## {head} ({len(rows)})", ""]
        for k, r in rows:
            b = fn(k, r)
            if budget - len(b) < 0 and budget < CAP_PACKET:
                rest.append(k)
                continue
            budget -= len(b)
            L += [b, ""]
    if rest:
        L += ["## Not shown (packet full)", "", "Run `python tools/pull.py done " + slug + " <IDs shown>` after this pass, then "
              "`python tools/pull.py packet " + slug + "` again for: " + ", ".join(rest)]
    text = "\n".join(L).rstrip() + "\n"
    p = atl_store.write(f"{PACKETS}/{day}-{slug}.md", text)
    say(f"Saved: {p.relative_to(ROOT).as_posix()} (copy it as the source of this card's pull digest)\n")
    say(text)


# ------------------------------------------------------------------ clearing, headlines
def cmd_done(slug, ids):
    s, cs = state(), cards()
    g = grouped(s, cs).get(slug, {"jira": [], "confluence": []})
    mine = [k for k, _ in g["jira"]] + [p for p, _ in g["confluence"]]
    ids = ids or mine
    cleared = atl_updates.mark_digested(ids)
    s = state()
    s["run"]["done"].setdefault(slug, [])
    s["run"]["done"][slug] = sorted(set(s["run"]["done"][slug]) | set(cleared))
    atl_updates.save_state(s)
    say(f"{slug}: cleared {len(cleared)} item(s)" + (f"; not waiting: {', '.join(set(ids) - set(cleared))}" if set(ids) - set(cleared) else ""))


def cmd_skip(ids):
    cleared = atl_updates.mark_digested(ids)
    s = state()
    s["run"]["skipped"] = sorted(set(s["run"]["skipped"]) | set(cleared))
    atl_updates.save_state(s)
    say(f"Skipped {len(cleared)} item(s).")


def cmd_headline(slug, text):
    s = state()
    s["run"]["headlines"][slug] = [" ".join(t.split()) for t in text.split(" | ") if t.strip()][:2]
    atl_updates.save_state(s)
    say(f"{slug}: headline saved.")


def cmd_needs(text):
    s = state()
    s["run"]["needs"].append(" ".join(text.split()))
    atl_updates.save_state(s)
    say("Saved for Needs you.")


# ------------------------------------------------------------------ 6: finish once
def build():
    import jobs
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_map.py")], cwd=ROOT, capture_output=True, text=True, **jobs.quiet())
    say((r.stdout.strip().splitlines() or [""])[-1] if r.returncode == 0 else "Build failed:\n" + r.stderr[-1500:])


def auto_closed(since_day):
    out = []
    for p in sorted((K / "registers" / "gaps").glob("MANTIS-GAP-*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"(?m)^- \*\*Status:\*\* Closed \(auto, (\d{4}-\d{2}-\d{2})", t)
        if m and m.group(1) >= since_day:
            topic = re.search(r"(?m)^- \*\*Topic:\*\*\s*(.+)$", t)
            out.append({"id": p.stem, "topic": (topic.group(1) if topic else "")[:160]})
    return out


def load_brief():
    try:
        return json.loads(BRIEF.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last": None, "history": []}


def pending_counts():
    """What waits for the next pull right now: Jira and Confluence items, and files in the inbox (for the site)."""
    s = atl_updates.load_state()
    loose = sum(len(e["keys"]) for e in unmapped())   # tickets no card owns wait for the owner, not for a pull
    return {"jira": len(s["pending"]["jira"]) - loose, "confluence": len(s["pending"]["confluence"]), "files": len(inbox_files()),
            "last_fetch": max(s["jira"].get("last_fetch", ""), s["confluence"].get("last_fetch", ""))}


def cmd_finish():
    build()
    s, cs = state(), cards()
    run, b = s["run"], load_brief()
    noise = run["noise"]
    moves = [f"{k} {r.get('summary', '')[:70]}: {'; '.join(r['changes'])}" for k, r in sorted(noise["jira"].items())]
    left = len(s["pending"]["jira"]) + len(s["pending"]["confluence"])
    order = [k for k in cs if k in run["headlines"]] + [k for k in run["headlines"] if k not in cs]
    brief = {"at": atl_updates.now(), "since": (b.get("last") or {}).get("at", ""),
             "cards": [{"slug": k, "title": cs[k]["title"] if k in cs else "Other changes", "lines": run["headlines"][k]} for k in order],
             "status_moves": moves, "formatting": sorted(r["title"] for r in noise["confluence"].values()),
             "closed": auto_closed(run.get("started", atl_updates.now())[:10]), "needs": run["needs"], "waiting": left}
    if b.get("last"):
        b["history"] = ([b["last"]] + b.get("history", []))[:10]
    b["last"] = brief
    BRIEF.parent.mkdir(parents=True, exist_ok=True)
    BRIEF.write_text(json.dumps(b, indent=1, ensure_ascii=False), encoding="utf-8")
    s["run"] = {}
    atl_updates.save_state(s)
    print_brief(brief)


def when(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M").strftime("%d %b %H:%M").lstrip("0")
    except ValueError:
        return stamp or "the start"


def print_brief(b):
    if not b:
        say("No pull has finished yet.")
        return
    say(f"Since last pull ({when(b['since'])} to {when(b['at'])})")
    for c in b["cards"]:
        say(f"\n{c['title']}")
        for line in c["lines"]:
            say(f"- {line}")
    extra = []
    if b["status_moves"]:
        extra.append(f"{len(b['status_moves'])} ticket(s) moved status or parent only")
    if b["formatting"]:
        extra.append(f"{len(b['formatting'])} page(s) had formatting-only edits")
    if extra:
        say("\nAlso: " + "; ".join(extra) + ".")
    if b["closed"]:
        say("\nClosed automatically (undo: python tools/entry.py reopen <ID>):")
        for x in b["closed"]:
            say(f"- {x['id']}: {x['topic']}")
    if b["needs"]:
        say("\nNeeds you:")
        for n in b["needs"]:
            say(f"- {n}")
    if b["waiting"]:
        say(f"\n{b['waiting']} item(s) still wait for the next pull.")


# ------------------------------------------------------------------ filters (also used by the site)
def list_filters():
    return atl_updates.filters(atl_client.load_config())


def set_filter(action, fid="", label=None, value=None, active=None, typ=None):
    """Add, change or remove one filter. Returns the filter list. Raises ValueError on bad input."""
    conf = atl_client.load_config()
    fl = atl_updates.filters(conf)
    if action == "add":
        if typ not in ("jira", "confluence") or not (label or "").strip() or not (value or "").strip():
            raise ValueError("a filter needs a type (jira or confluence), a label and a value")
        base = atl_updates.slug(label)
        fid = base if base not in {f["id"] for f in fl} else f"{base}-{len(fl) + 1}"
        fl.append({"id": fid, "label": label.strip(), "type": typ, "value": value.strip(), "active": active is not False,
                   "last_run": "", "last_counts": {}})
    else:
        f = next((f for f in fl if f["id"] == fid), None)
        if not f:
            raise ValueError(f"no filter '{fid}'")
        if action == "remove":
            fl.remove(f)
        elif action == "set":
            if label is not None and label.strip():
                f["label"] = label.strip()
            if value is not None and value.strip() and value.strip() != f["value"]:
                f["value"], f["last_run"], f["last_counts"] = value.strip(), "", {}   # a new value starts fresh
            if active is not None:
                f["active"] = bool(active)
        else:
            raise ValueError("unknown action")
    atl_client.save_config(conf)
    return fl


def test_filter(fid="", typ=None, value=None):
    """How many items a filter selects now: {"count", "sample"}. One call; nothing saved."""
    if fid:
        f = next((f for f in list_filters() if f["id"] == fid), None)
        if not f:
            raise ValueError(f"no filter '{fid}'")
        typ, value = f["type"], f["value"]
    c = atl_client.connect(typ)
    if typ == "jira":   # the search API gives no total any more: count up to 500 (5 calls at most)
        import atl_jira
        got = atl_jira.search(c, atl_updates.without_order(atl_jira.jql_for(c, value)), ["summary"], limit=501)
        return {"count": len(got) if len(got) <= 500 else "500+",
                "sample": [f"{i['key']} {i['fields'].get('summary', '')}" for i in got[:5]]}
    d = c.get("/rest/api/search", {"cql": atl_updates.page_cql(value), "limit": 5})   # this endpoint reports the total
    return {"count": d.get("totalSize", 0), "sample": [x.get("title") or x.get("content", {}).get("title", "") for x in d.get("results", [])]}


def cmd_filters():
    for f in list_filters():
        n = f.get("last_counts", {})
        say(f"[{'on ' if f.get('active') else 'off'}] {f['id']}: {f['label']} ({f['type']})\n      {f['value']}\n"
            f"      last run {f.get('last_run') or 'never'}" + (f": {n.get('new', 0)} new, {n.get('changed', 0)} changed" if n else ""))


def opt(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def cmd_filter(args):
    a = args[0] if args else ""
    if a == "add" and len(args) >= 4:
        set_filter("add", label=args[2], value=args[3], typ=args[1], active="--off" not in args)
    elif a == "set" and len(args) >= 2:
        set_filter("set", args[1], label=opt(args, "--label"), value=opt(args, "--value"),
                   active=True if "--on" in args else False if "--off" in args else None)
    elif a == "remove" and len(args) == 2:
        set_filter("remove", args[1])
    elif a == "test" and len(args) == 2:
        r = test_filter(args[1])
        say(f"{r['count']} item(s) now. For example: " + "; ".join(r["sample"]))
        return
    else:
        sys.exit(__doc__)
    cmd_filters()


def main(a):
    sys.stdout.reconfigure(errors="replace")
    try:
        if not a:
            cmd_fetch()
        elif a[0] == "plan":
            cmd_plan(rebuild="--rebuild" in a)
        elif a[0] == "packet" and len(a) == 2:
            cmd_packet(a[1])
        elif a[0] == "done" and len(a) >= 2:
            cmd_done(a[1], a[2:])
        elif a[0] == "skip" and len(a) >= 2:
            cmd_skip(a[1:])
        elif a[0] == "headline" and len(a) == 3:
            cmd_headline(a[1], a[2])
        elif a[0] == "needs" and len(a) == 2:
            cmd_needs(a[1])
        elif a[0] == "finish":
            cmd_finish()
        elif a[0] == "brief":
            print_brief(load_brief().get("last"))
        elif a[0] == "filters":
            cmd_filters()
        elif a[0] == "filter":
            cmd_filter(a[1:])
        else:
            print(__doc__)
            return 1
    except (atl_client.AtlassianError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
