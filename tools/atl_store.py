"""The local mirror of Jira and Confluence: one Markdown file per item plus an index (MANTIS-IMP-087). Stdlib only.

    mantis/mirror/confluence/index.json      page id -> title, path, version, kind, hash ...
    mantis/mirror/confluence/pages/<id>.md   the page as Markdown (header, body, comments)
    mantis/mirror/jira/index.json            issue key -> summary, type, status, parent, updated, hash ...
    mantis/mirror/jira/issues/<KEY>.md
    mantis/mirror/diffs/<id>.md              what changed in a page since Mantis took its copy
    mantis/mirror/reports/<date>-*.md        the reports a run writes

The mirror is kept by code and costs no AI tokens. It is not a Mantis source: nothing in it is
cited until it is ingested. It stays on this machine (mantis/ is never committed).
"""
import hashlib, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "mantis" / "mirror"


def path(*parts):
    p = MIRROR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_index(kind):
    try:
        return json.loads(path(kind, "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_index(kind, index):
    path(kind, "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def digest(text):
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def write(rel, text):
    p = path(*rel.split("/"))
    p.write_text(text, encoding="utf-8")
    return p


def read(rel):
    p = MIRROR.joinpath(*rel.split("/"))
    return p.read_text(encoding="utf-8") if p.exists() else ""
