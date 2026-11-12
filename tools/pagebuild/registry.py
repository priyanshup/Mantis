"""The containers the build fills once (the graph, open items, topics, focus, drafts, changes, assets). build_site.py fills them in place, so every module that imports one sees the same object."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from pathlib import Path


GRAPH = {}  # filled by build() from map/entities.json


OPEN = []  # filled by build() from map/open-items.json


TOPICS = []  # filled by build() from map/topics.json


FOCUS = {"following": [], "on_roadmap": [], "off_roadmap": [], "archived": []}  # the owner's choices, mantis/knowledge/focus.json


def archived(slug):
    """An archived card is hidden from focus, roadmap, lists and filters; its page, sources and search stay."""
    return slug in FOCUS.get("archived", [])


def on_roadmap(c, is_feature):
    if archived(c["slug"]):
        return False
    return (c["slug"] not in FOCUS["off_roadmap"]) if is_feature else (c["slug"] in FOCUS["on_roadmap"])


DRAFTS = {}


CHANGES = {"events": [], "refresh": [], "today": ""}   # map/changes.json (tools/changes.py)


READY = {"states": {}, "features": [], "attention": []}   # map/readiness.json (tools/readiness.py, MANTIS-IMP-074 to 076)


ASSETS = []   # registered knowledge assets, from map/assets.json (MANTIS-IMP-008)


def asset_src(aid):
    a = next((x for x in ASSETS if x["id"] == aid), None)
    return f"/diagrams/{Path(a['file']).name}" if a and a.get("file") else ""
