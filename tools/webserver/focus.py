"""The owner's follow, archive and roadmap choices from the Features page (knowledge/focus.json)."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import datafile
import threading
from webserver.config import FOCUS, OUTPUTS, ROOT
from webserver.watching import rebuild


FOCUS_ACTIONS = {"follow": ("following", True), "unfollow": ("following", False),
                 "roadmap": ("on_roadmap", True), "unroadmap": ("on_roadmap", False),
                 "archive": ("archived", True), "unarchive": ("archived", False)}


def card_slugs():
    k = ROOT / "mantis" / "knowledge"
    feats = {p.stem for p in (k / "features").glob("*.md") if p.name != "README.md"}
    topics = {p.stem for p in (k / "topics").glob("*.md") if p.name != "README.md"}
    return feats, topics


def set_focus(slug, action, order=None, rebuild_after=True):
    """Update the owner's focus choices (a preference file, not knowledge; written directly, no inbox)."""
    feats, topics = card_slugs()
    if action.startswith("bulk-"):   # several cards at once: bulk-follow, bulk-unfollow, bulk-roadmap, bulk-unroadmap
        f = None
        for s in [s for s in (order or []) if s in feats | topics]:
            f = set_focus(s, action[5:], rebuild_after=False)
        threading.Thread(target=rebuild, daemon=True).start()
        return f or datafile.read(FOCUS, {})
    if action in ("archive-work", "unarchive-work"):   # one epic or story, keyed by its file under mantis/ (outputs/...)
        target = (ROOT / "mantis" / slug).resolve()
        if not slug.startswith("outputs/") or not slug.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
            raise ValueError("unknown epic or story")
        f = datafile.read(FOCUS, {"following": []})
        rest = [s for s in f.get("archived_work", []) if s != slug]
        f["archived_work"] = sorted(rest + ([slug] if action == "archive-work" else []))
        datafile.write(FOCUS, f, ensure_ascii=True)
        if rebuild_after:
            threading.Thread(target=rebuild, daemon=True).start()
        return f
    if action == "order":   # the owner's ranking of followed cards, top first
        f = datafile.read(FOCUS, {"following": []})
        known = [s for s in (order or []) if s in f.get("following", [])]
        f["following"] = known + [s for s in f.get("following", []) if s not in known]
        datafile.write(FOCUS, f, ensure_ascii=True)
        threading.Thread(target=rebuild, daemon=True).start()
        return f
    if slug not in feats | topics or action not in FOCUS_ACTIONS:
        raise ValueError("unknown card or action")
    f = datafile.read(FOCUS, {"following": [], "on_roadmap": [], "off_roadmap": []})
    for k in ("following", "on_roadmap", "off_roadmap", "archived"):
        f.setdefault(k, [])
    if action == "archive":   # an archived card leaves focus and the roadmap; restoring it does not put it back
        f["following"] = [s for s in f["following"] if s != slug]
        f["on_roadmap"] = [s for s in f["on_roadmap"] if s != slug]
        if slug in feats and slug not in f["off_roadmap"]:
            f["off_roadmap"] = sorted(f["off_roadmap"] + [slug])
    key, on = FOCUS_ACTIONS[action]
    if key == "on_roadmap" and slug in feats:   # roadmap features are on the roadmap unless taken off
        key, on = "off_roadmap", not on
    if key == "following":   # keep the owner's ranking: a new follow goes to the bottom
        f[key] = [s for s in f[key] if s != slug] + ([slug] if on else [])
    else:
        lst = set(f[key])
        (lst.add if on else lst.discard)(slug)
        f[key] = sorted(lst)
    datafile.write(FOCUS, f, ensure_ascii=True)
    if rebuild_after:
        threading.Thread(target=rebuild, daemon=True).start()   # the page reloads itself when the rebuild lands
    return f
