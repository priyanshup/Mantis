"""The diagrams page."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from pagebuild.registry import ASSETS, GRAPH, asset_src
from pagebuild.text import esc


def page_diagrams(built, embed=True):
    """Registered knowledge assets (MANTIS-IMP-008): diagrams worth reusing, with what each shows."""
    clean = lambda v: re.sub(r"\s*(?:Source: )?\(?MANTIS-[A-Z]+-\d+(?:, (?:page|slide) \d+)?\)?[.;,]?", "", v).strip()
    tiles = []
    for a in sorted(ASSETS, key=lambda x: (x["type"], x["title"].lower())):
        if a["status"] == "Superseded" or not asset_src(a["id"]):
            continue
        src = asset_src(a["id"])
        where = ", ".join(esc(GRAPH.get("titles", {}).get(d, "")) for d in a["docs"] if GRAPH.get("titles", {}).get(d))
        used = len(a.get("referenced_by", []))
        meta = (f'<p class="muted small">From: {where}</p>' if where else "") + (f'<p class="muted small">Used on {used} page{"s" if used != 1 else ""}.</p>' if used else "")
        tiles.append(f'<article class="tile dia" data-type="{esc(a["type"])}"><a class="dia-img" href="{esc(src)}" target="_blank" rel="noopener" title="Open full size">'
                     f'<img src="{esc(src)}" alt="{esc(a["title"])}" loading="lazy"></a>'
                     f'<div class="dia-body"><span class="tag">{esc(a["type"].replace("-", " ").capitalize() or "Diagram")}</span><h3>{esc(a["title"])}</h3>'
                     f'<p>{esc(clean(a["description"]))}</p>'
                     f'{meta}</div></article>')
    types = sorted({a["type"] for a in ASSETS if a["type"]})
    chips = "".join(f'<button data-v="{esc(t)}">{esc(t.replace("-", " ").capitalize())}</button>' for t in types)
    body = f"""<div class="page-h"><div><h1>Diagrams</h1><p class="lead">Diagrams and other visuals from the sources that are worth reusing, each with what it shows. Pages reuse one of these before anyone draws a new diagram.</p></div></div>
{f'<div class="toolbar"><div class="chips" id="f-dia"><button data-v="all" class="on">All</button>{chips}</div></div>' if len(types) > 1 else ""}
<div class="dia-grid">{"".join(tiles) or '<p class="empty">No diagrams registered yet.</p>'}</div>"""
    return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)   # shown inside the Library page (MANTIS-IMP-068): no page header
