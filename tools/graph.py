"""Query the Mantis entity graph (built by build_map.py into map/entities.json).

    python tools/graph.py <name>            one entity: type, aliases, features, relations, links, documents
    python tools/graph.py path <A> <B>      shortest chain of links between two entities
    python tools/graph.py top [type] [N]    most-cited entities, optionally of one type
    python tools/graph.py candidates        possible duplicate names to confirm

Names match case-insensitively on the canonical name or any alias; a unique partial match works too.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # names like Domański print on any console
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "mantis" / "knowledge" / "map"
G = json.loads((MAP / "entities.json").read_text(encoding="utf-8"))
E = {e["name"]: e for e in G["entities"]}
TITLES = {}
for line in (MAP / "MAP.md").read_text(encoding="utf-8").splitlines():
    parts = [p.strip() for p in line.split("|")]
    if len(parts) > 2 and re.fullmatch(r"D\d{4}", parts[0]):
        TITLES[parts[0]] = parts[1]


def key(s):
    return re.sub(r"[^0-9a-z]", "", s.lower())


def find(q):
    k = key(q)
    exact = [e for e in G["entities"] if k in [key(e["name"])] + [key(a) for a in e["aliases"]]]
    if exact:
        return exact[0]
    part = [e for e in G["entities"] if k in key(e["name"]) or any(k in key(a) for a in e["aliases"])]
    if len(part) == 1:
        return part[0]
    if part:
        sys.exit(f"'{q}' matches several: " + ", ".join(e["name"] for e in part[:12]))
    sys.exit(f"No entity matches '{q}'.")


def show(e):
    d = lambda i: i.replace("MANTIS-DOC-", "D")
    print(f"{e['name']} [{e['type']}]" + (f"  aka {', '.join(e['aliases'])}" if e["aliases"] else ""))
    if e["features"]:
        print("features: " + ", ".join(f"{f['slug']} ({f['docs']})" for f in e["features"]))
    for r in e["relations"]:
        print(f"relation: {r['rel']} {r['to']}" if r["dir"] == "out" else f"relation: {r['to']} {r['rel']} it", f"[{r['source']}]")
    if e["neighbours"]:
        print("linked: " + ", ".join(f"{n} ({w})" for n, w in e["neighbours"]))
    print(f"documents ({len(e['docs'])}):")
    for i in e["docs"][:15]:
        print(f"  {d(i)} {TITLES.get(d(i), '')}")
    if len(e["docs"]) > 15:
        print(f"  … and {len(e['docs']) - 15} more")


def links(e):
    out = {n for n, _ in e["neighbours"]} | {r["to"] for r in e["relations"]}
    return [n for n in out if n in E]


def path(a, b):
    start, goal = find(a)["name"], find(b)["name"]
    prev, q = {start: None}, deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            chain = []
            while cur:
                chain.append(cur)
                cur = prev[cur]
            chain.reverse()
            for x, y in zip(chain, chain[1:]):
                w = dict(E[x]["neighbours"]).get(y)
                rel = next((r["rel"] for r in E[x]["relations"] if r["to"] == y), None)
                print(f"{x} -> {y}: " + (rel or f"{w} shared documents"))
            return
        for n in links(E[cur]):
            if n not in prev:
                prev[n] = cur
                q.append(n)
    print(f"No chain between {start} and {goal}.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "path" and len(a) == 3:
        path(a[1], a[2])
    elif a[0] == "top":
        typ = a[1] if len(a) > 1 and not a[1].isdigit() else None
        n = int(a[-1]) if a[-1].isdigit() else 20
        for e in [e for e in G["entities"] if not typ or e["type"] == typ][:n]:
            print(f"{len(e['docs']):3} {e['name']} [{e['type']}]")
    elif a[0] == "candidates":
        print("\n".join(f"{c['a']} / {c['b']}" for c in G["candidates"]) or "None.")
    else:
        show(find(" ".join(a)))
