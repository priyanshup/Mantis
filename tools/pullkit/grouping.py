"""Which card a ticket or page belongs to, what waits for each card, and the tickets no card owns."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import atl_client
import atl_store
import atl_updates
import frontmatter
import textcache
from pullkit.state import NEW_ROW, ROOT, cards, cmd_skip, state


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
