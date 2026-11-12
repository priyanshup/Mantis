"""The file-to-topic map (IMP-109): for every feature and topic card, which files hold its knowledge and what each costs to read.

    python tools/topicmap.py                 write mantis/knowledge/map/topic-files.json (build_map.py does this on every build)
    python tools/context.py rollout --files    the files of one subject with their sizes

Per slug: the card file (total bytes and the curated part alone, which is what to read first), its digests with sizes, its outputs (page, epics, stories) with sizes, and the
number of open questions. Generated, never edited; it lets a session choose the smallest file that answers a question instead of opening them all.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MAP = M / "knowledge" / "map"
MARK = "<!-- GENERATED"


def _json(map_dir, name, default):
    try:
        return json.loads((Path(map_dir) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _size(path):
    try:
        return path.stat().st_size
    except OSError:
        return None


def build(map_dir=MAP, mantis=M):
    """{slug: {title, kind, card, card_bytes, curated_bytes, digests: [{id, bytes}], digest_bytes, outputs: [{file, bytes}], open}}"""
    mantis = Path(mantis)
    open_items = [o for o in _json(map_dir, "open-items.json", []) if str(o.get("status", "")).lower() not in ("closed", "resolved")]
    out = {}
    for c in _json(map_dir, "features.json", []) + _json(map_dir, "topics.json", []):
        card = mantis / c.get("card", "")
        total = _size(card)
        if total is None:
            continue
        text = card.read_text(encoding="utf-8", errors="replace")   # sizes are of the text (line ends count once), so the curated part is never larger than the card
        total = len(text.encode("utf-8"))
        curated = len(text.split(MARK)[0].encode("utf-8"))
        digests = [{"id": d, "bytes": s} for d in c.get("docs", []) if (s := _size(mantis / "02_digests" / f"{d}.md")) is not None]
        files = ([c["page"]] if c.get("page") else []) + [e["file"] for e in c.get("epics", [])] + [s["file"] for s in c.get("stories", [])]
        outputs = [{"file": f, "bytes": s} for f in files if (s := _size(mantis / f)) is not None]
        out[c["slug"]] = {"title": c.get("title", c["slug"]), "kind": c.get("kind", "card"), "card": c["card"], "card_bytes": total, "curated_bytes": curated,
                          "digests": digests, "digest_bytes": sum(d["bytes"] for d in digests), "outputs": outputs,
                          "open": sum(1 for o in open_items if c["slug"] in (o.get("features") or []))}
    return out


def write(map_dir=MAP, mantis=M):
    """Save the map; returns True when the file changed (an unchanged map is not rewritten, so a rebuild with no change writes nothing)."""
    import textcache
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    return textcache.write(Path(map_dir) / "topic-files.json", json.dumps(build(map_dir, mantis), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    print("topic-files.json written" if write() else "topic-files.json unchanged")
