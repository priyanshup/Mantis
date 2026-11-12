"""The decisions page."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from pagebuild.paths import M
from pagebuild.text import esc


def page_decisions(built, embed=True):
    """Every logged decision (MANTIS-IMP-027): what was chosen, why, and what else was considered."""
    rows = []
    for f in sorted((M / "knowledge" / "registers" / "decisions").glob("MANTIS-DEC-*.md"), reverse=True):
        t = f.read_text(encoding="utf-8")
        field = lambda k: re.sub(r"\s+", " ", (re.search(rf"\*\*{k}:\*\*\s*(.+?)(?=\n- \*\*|\Z)", t, re.S) or [None, ""])[1]).strip()
        clean = lambda v: re.sub(r"\s*\(?MANTIS-[A-Z]+-\d+\)?[;,]?", "", v).replace("()", "").strip()
        when, what = field("Date"), clean(field("Decision"))
        if not what:
            continue
        rows.append(f'<article class="tile dec"><p class="muted small">{esc(when)}</p><h3>{esc(what)}</h3>'
                    + "".join(f'<div class="pp-f"><span class="muted small">{lab}</span><span>{esc(clean(field(k)))}</span></div>'
                              for k, lab in (("Reasoning", "Why"), ("Alternatives considered", "Not chosen"), ("Consequences", "What it means")) if field(k))
                    + "</article>")
    body = f"""<div class="page-h"><div><h1>Decisions</h1><p class="lead">Choices made along the way, newest first: what was decided, why, and what else was on the table. Facts live on the cards; decisions live here, so a new source never silently rewrites why something was done.</p></div></div>
<div class="dec-list">{"".join(rows) or '<p class="empty">No decisions logged yet.</p>'}</div>"""
    return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)   # shown inside the Library page (MANTIS-IMP-068): no page header
