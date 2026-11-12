"""The Jira keys and Confluence page IDs each card stands on (IMP-113): a generated map, never hand-kept.

    python tools/cardkeys.py            write mantis/knowledge/map/card-keys.json (build_map.py does this on every build)
    python tools/cardkeys.py <card>     print one card's keys

Per card slug: `jira` (its Feature), `items` (the Jira items listed in the card's `jira_items`) and `pages` (Confluence page IDs carried by its digests as
`confluence_page_id` or `confluence_pages`). The card's own front matter stays the owner's; this map reads it and the digests and adds nothing to either,
so a key or page ID is found in one lookup instead of a search. context.py prints a one-line summary from it.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MAP = M / "knowledge" / "map"
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
KEY = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


def _head(path):
    try:
        m = FRONT.match(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return ""
    return m.group(1) if m else ""


def _list(head, key):
    m = re.search(rf"(?m)^{key}:\s*\[(.*?)\]\s*$", head)
    return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()] if m else []


def pages_of(digest_head):
    """Page IDs a digest carries: `confluence_page_id: 123` and `confluence_pages: [1, 2]` or a block of '- 1' lines."""
    ids = re.findall(r"(?m)^confluence_page_id:\s*\"?(\d+)", digest_head)
    m = re.search(r"(?ms)^confluence_pages:\s*(.*?)(?=^\S|\Z)", digest_head)
    if m:
        ids += re.findall(r"\b(\d{6,})\b", m.group(1))
    return ids


def build(map_dir=MAP, mantis=M):
    mantis = Path(mantis)
    cards = []
    for name in ("features.json", "topics.json"):
        try:
            cards += json.loads((Path(map_dir) / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    heads = {}
    out = {}
    for c in cards:
        head = _head(mantis / c.get("card", ""))
        jira = (re.search(r"(?m)^jira:\s*(\S+)", head) or [None, ""])[1].strip("\"'")
        items = sorted({k for k in _list(head, "jira_items") if KEY.fullmatch(k)})
        pages = []
        for d in c.get("docs", []):
            h = heads.get(d)
            if h is None:
                h = heads[d] = _head(mantis / "02_digests" / f"{d}.md")
            pages += pages_of(h)
        out[c["slug"]] = {"jira": jira if KEY.fullmatch(jira) else "", "items": items, "pages": sorted(set(pages), key=int)}
    return out


def write(map_dir=MAP, mantis=M):
    import textcache
    return textcache.write(Path(map_dir) / "card-keys.json", json.dumps(build(map_dir, mantis), indent=1, ensure_ascii=False))


def summary(entry):
    """'Jira CUD-1 (+3 items); Confluence pages 4' for context.py, '' when the card has neither."""
    if not entry:
        return ""
    parts = []
    if entry.get("jira") or entry.get("items"):
        parts.append("Jira " + (entry.get("jira") or "no Feature") + (f" (+{len(entry['items'])} items)" if entry.get("items") else ""))
    if entry.get("pages"):
        parts.append(f"Confluence pages {len(entry['pages'])}")
    return "; ".join(parts)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        e = build().get(sys.argv[1])
        print(json.dumps(e, indent=1) if e else f"no card '{sys.argv[1]}'")
    else:
        print("card-keys.json written" if write() else "card-keys.json unchanged")
