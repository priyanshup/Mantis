"""Reading the knowledge files into the pages' data: features, work, topics, library items, who can answer what."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib
import json
import re
from urllib.parse import quote
from pagebuild.labels import STATUS, work_pill
from pagebuild.markup import clean, first_sentence, plain, read
from pagebuild.paths import M
from pagebuild.registry import OPEN, TOPICS
from pagebuild.text import ID, esc, front_matter


def load():
    mp = M / "knowledge" / "map"
    features = json.loads((mp / "features.json").read_text(encoding="utf-8"))
    work = json.loads((mp / "work.json").read_text(encoding="utf-8"))
    titles = {f["slug"]: f["title"] for f in features}
    epics = {e["id"]: e for e in work["epics"]}
    for x in work["epics"] + work["stories"]:
        x["md"] = read(x["file"])[1]
        x["feature_title"] = titles.get(x["feature"], "")
        x["epic_title"] = epics[x["epic"]]["title"] if x.get("epic") in epics else ""
        x["href"] = (f"features/{x['feature']}.html#{'epic' if x['kind'] == 'epic' else 'story'}-{x['anchor']}"
                     if x["feature"] != "none" else f"pages/work-{x['id']}.html")
    for f in features:
        card = read(f["card"])[1]
        f["card_md"], f["summary"] = card, first_sentence(card)
        f["page_md"], f["page_status"] = None, ""
        f["preps"] = []   # meeting prep notes for this feature: mantis/outputs/prep/*.md with "feature: <slug>"
        for pp in sorted((M / "outputs" / "prep").glob("*.md")):
            pfm, pmd = front_matter(pp.read_text(encoding="utf-8"))
            if pfm.get("feature") == f["slug"]:
                f["preps"].append({"title": pfm.get("title", pp.stem), "updated": pfm.get("updated", ""), "md": re.sub(r"(?s)<!--.*?-->\s*", "", pmd).strip()})
        if f["page"]:
            fm, f["page_md"] = read(f["page"])
            f["page_status"] = fm.get("status", "")
        mine = {x["id"]: x for x in work["epics"] + work["stories"] if x["feature"] == f["slug"]}
        f["epics"] = [mine[e["id"]] for e in f["epics"]]
        f["stories"] = [mine[s["id"]] for s in f["stories"]]
        f["updated"] = max([f["updated"]] + [x["updated"] for x in mine.values() if x["updated"]])
        f["open"] = len(f["open_gaps"])
        f["status"] = f["status"] if f["status"] in STATUS else "discovery"
    later = []
    readme = (M / "knowledge" / "features" / "README.md").read_text(encoding="utf-8")
    m = re.search(r"(?ms)^## Roadmap items with no card yet.*?\n(\|.+?)(?:\n\n|\Z)", readme)
    if m:
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in m.group(1).strip().split("\n")[2:]]
        later = [{"title": r[0], "note": re.sub(r"\s+", " ", clean(r[1])).strip()} for r in rows if r and r[0]]
    return features, later, work["epics"] + work["stories"], epics


def load_topics():
    p = M / "knowledge" / "map" / "topics.json"
    topics = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    for t in topics:
        t["card_md"] = read(t["card"])[1]
        t["summary"] = first_sentence(t["card_md"], 220)
        t["open"] = sum(1 for o in OPEN if o["kind"] in ("gap", "assumption", "conflict") and {d["id"] for d in o["docs"]} & set(t["docs"]))
    return topics


def library_items(features, work):
    items = []
    pages = {f["page"]: f for f in features if f["page"]}
    for x in work:
        items.append({"kind": "Epic" if x["kind"] == "epic" else "Story", "title": x["title"], "href": x["href"],
                      "status": x["status"], "updated": x["updated"], "where": x["feature_title"] or "No feature"})
    for p in sorted((M / "outputs").rglob("*.md")):
        rel = p.relative_to(M).as_posix()
        if rel.startswith(("outputs/epics/", "outputs/user-stories/")):
            continue
        fm, body = front_matter(p.read_text(encoding="utf-8"))
        kind = "Confluence page" if "/confluence/" in rel else "Knowledge doc"
        h = re.search(r"(?m)^#\s+(.+)$", body)
        title = fm.get("title") or (h.group(1).strip() if h else p.stem.replace("-", " ").capitalize())
        f = pages.get(rel)
        items.append({"kind": kind, "title": re.sub(ID, "", title).strip(), "status": fm.get("status", ""),
                      "updated": fm.get("updated", ""), "where": f["title"] if f else "",
                      "href": f"features/{f['slug']}.html#page" if f else f"pages/{p.stem}.html", "md": None if f else body,
                      "file": rel})
    return items


def story_list(stories, epics_by_id, base_href=""):
    """Stories grouped by epic, for the side panel."""
    groups = {}
    for s in stories:
        groups.setdefault(s["epic"] if s["epic"] in epics_by_id else "", []).append(s)
    out = []
    for key in sorted(groups, key=lambda k: (k == "", epics_by_id[k]["title"] if k else "")):
        name = f'Epic: {epics_by_id[key]["title"]}' if key else "Not in an epic"
        out.append(f'<p class="grp">{esc(name)}</p>')
        out += [f'<a class="story" href="{base_href}#story-{s["anchor"]}" data-anchor="story-{s["anchor"]}"><span><span class="k-ico k-story">▤</span>{esc(s["title"])}</span>{work_pill(s["status"])}</a>' for s in groups[key]]
    return "".join(out)


def draft_data():
    """Per person, the open questions they can answer, phrased for a message (MANTIS-IMP-048)."""
    import people as people_mod
    chan = {p["name"]: p["channel"] for p in people_mod.load()}
    titles = {f["slug"]: f["title"] for f in json.loads((M / "knowledge" / "map" / "features.json").read_text(encoding="utf-8"))} \
        if (M / "knowledge" / "map" / "features.json").exists() else {}
    titles.update({t["slug"]: t["title"] for t in TOPICS})
    strip = lambda s: re.sub(r"\s*No inference has been made\.?", "", re.sub(r"\s*\(?MANTIS-[A-Z]+-\d+[^)]*\)?", "", s or "")).strip()
    out = {}
    for o in OPEN:
        a = o.get("ask")
        if not a or o["kind"] in ("name", "term"):
            continue
        main = next((v for k, v in o.get("detail", []) if k.split(" (")[0] in ("What's missing", "Statement", "Statement A", "Claim")), "")
        ctx = re.split(r"(?<=[.!?])\s", strip(main))[0] if main else ""
        out.setdefault(a["name"], {"first": a["name"].split()[0], "channel": chan.get(a["name"], ""), "questions": []})["questions"].append(
            {"q": strip(o["topic"]), "ctx": ctx if len(ctx) <= 200 else ctx[:199].rsplit(" ", 1)[0].rstrip(",;:") + "…", "card": titles.get((o.get("features") or [""])[0], ""), "named": a["how"] == "named"})
    for v in out.values():
        v["questions"].sort(key=lambda q: not q["named"])
    return out


def draft_button(name, cls="act"):
    return f'<button type="button" class="{cls} nocopy" data-draft="{esc(name)}">Draft a message</button>'


def can_answer(name):
    """Open questions this person can answer (MANTIS-IMP-046): named ones and suggestions in separate groups."""
    k = lambda o: hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]
    mine = [o for o in OPEN if (o.get("ask") or {}).get("name") == name]
    out = ""
    for label, group in (("Can answer", [o for o in mine if o["ask"]["how"] == "named"]),
                         ("Might answer", [o for o in mine if o["ask"]["how"] != "named"])):
        if not group:
            continue
        rows = "".join(f'<li><a href="questions.html#k={k(o)}">{esc(plain(re.sub(r" ?[(]MANTIS-[^)]*[)]", "", o["topic"]), 100))}</a></li>' for o in group[:3])
        more = f'<a class="small" href="questions.html#who={quote(name)}">All {len(mine)} on Open items →</a>' if len(group) > 3 else ""
        tip = "" if label == "Can answer" else ' title="Suggested from the sources: not confirmed"'
        out += f'<div class="pp-f pp-ask"><span class="muted small"{tip}>{label}</span><div><ul class="pp-q">{rows}</ul>{more}</div></div>'
    return out


def jira_site():
    env = M / "config" / ".env"
    m = re.search(r"(?m)^JIRA_URL\s*=\s*(\S+)", env.read_text(encoding="utf-8")) if env.exists() else None
    return m.group(1).rstrip("/") if m else ""
