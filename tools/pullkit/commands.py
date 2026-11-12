"""The pull's steps: fetch, plan, one card's packet, done, skip, headline, needs and finish."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import atl_client
import atl_store
import atl_updates
import json
import re
import subprocess
import sys
from pullkit.brief import auto_closed, load_brief, print_brief
from pullkit.grouping import grouped, month_digest, new_sources, passes, unmapped
from pullkit.state import BRIEF, CAP_ITEM, CAP_PACKET, INBOX, K, PACKETS, ROOT, cards, inbox_files, say, state


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
