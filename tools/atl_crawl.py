"""A bounded crawl of Confluence pages that mirrored Jira tickets point to but the mirror does not hold (IMP-113). Read-only.

    python tools/atl.py frontier             list the pages tickets link to that are not mirrored, most linked first (no network)
    python tools/atl.py crawl [--max N]      mirror up to N of them (default 10), once each; the result of every try is kept in mirror/frontier.json

Bounds: only pages a mirrored ticket links to are followed (one hop; the pages' own links name titles, not IDs, so they are not followed), at most N per run, and a page
is tried once: a failure (no access, deleted) is recorded and not retried unless the entry is removed from frontier.json. Out-of-scope spaces keep only a title,
as `atl.py page` does.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json
from collections import Counter

TRIED = "frontier.json"


def frontier(jira_index, conf_index, tried=()):
    """[(page id, number of tickets linking it)] for page IDs a ticket links that the mirror lacks and no earlier run tried, most linked first."""
    refs = Counter(str(p) for v in jira_index.values() for p in v.get("pages", []))
    todo = [(p, n) for p, n in refs.items() if p.isdigit() and p not in conf_index and p not in set(map(str, tried))]
    return sorted(todo, key=lambda t: (-t[1], int(t[0])))


def load_tried(store):
    try:
        return json.loads(store.read(TRIED) or "{}")
    except ValueError:
        return {}


def crawl(todo, fetch, store, limit=10, log=print):
    """Fetch up to `limit` of the pages in `todo` with fetch(page id) -> entry dict, record each try, return {page id: 'ok' or the error}."""
    tried = load_tried(store)
    done = {}
    for pid, n in todo[:max(0, limit)]:
        try:
            e = fetch(pid)
            done[pid] = tried[pid] = "ok" if e.get("kind") != "out of scope" else "out of scope"
            log(f"{pid}: {e.get('title', '')} ({e.get('kind', '')})")
        except Exception as exc:   # a page that cannot be read is recorded and skipped; the crawl goes on (network, permission or deleted page)
            done[pid] = tried[pid] = f"failed: {str(exc)[:120]}"
            log(f"{pid}: {done[pid]}")
    store.write(TRIED, json.dumps(tried, indent=1, sort_keys=True))
    return done
