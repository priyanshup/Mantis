"""The changes page."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from pagebuild.frame import shell
from pagebuild.labels import EV_FOLD, EV_GROUPS, EV_KINDS, EV_ORDER
from pagebuild.registry import CHANGES
from pagebuild.text import esc, n_


def page_changes(built):
    """What's new (MANTIS-IMP-043) and cards to refresh (MANTIS-IMP-044)."""
    from datetime import date as _d, timedelta as _td
    today = _d.fromisoformat(CHANGES["today"]) if CHANGES.get("today") else _d.today()
    since = (today - _td(days=30)).isoformat()
    evs = [e for e in CHANGES["events"] if e["date"] >= since]
    # The feed, grouped by day
    days = {}
    for e in evs:
        days.setdefault(e["date"], []).append(e)

    def day_label(d):
        dd = _d.fromisoformat(d)
        n = (today - dd).days
        return ("Today" if n == 0 else "Yesterday" if n == 1 else dd.strftime("%A")) + f'<span class="muted"> · {dd.strftime("%d %b").lstrip("0")}</span>' if n < 7 \
            else dd.strftime("%A %d %B").replace(" 0", " ")

    def row(e):
        label, group, cls = EV_KINDS.get(e["kind"], (e["kind"].capitalize(), "cards", "ev-card"))
        if e["kind"] == "page" and e.get("what"):
            label = f'{e["what"]} updated'
        card = (f'<a class="ev-card muted small" href="{esc(e["card_href"])}">{esc(e["card"])}</a>'
                if e.get("card") and e["card"] != e["title"] and e.get("card_href") else "")
        title = f'<a href="{esc(e["href"])}">{esc(e["title"])}</a>' if e.get("href") else esc(e["title"])
        detail = f'<span class="ev-d muted small">{esc(e["detail"])}</span>' if e.get("detail") else ""
        return (f'<li class="ev" data-kind="{esc(e["kind"])}" data-group="{group}" data-date="{e["date"]}">'
                f'<span class="ev-k {cls}"><span class="ev-ico" aria-hidden="true"></span>{esc(label)}</span>'
                f'<span class="ev-main"><span class="ev-t">{title}</span>{detail}</span>{card}</li>')

    def day_rows(es):
        """What needs a decision first. Five or more of one routine kind on a day fold into one row."""
        es = sorted(es, key=lambda e: EV_ORDER.index(e["kind"]) if e["kind"] in EV_ORDER else 99)
        out, done = [], set()
        for e in es:
            k = e["kind"]
            same = [x for x in es if x["kind"] == k]
            if k in EV_FOLD and len(same) >= 5:
                if k in done:
                    continue
                done.add(k)
                label, group, cls = EV_KINDS[k]
                out.append(f'<li class="ev ev-fold" data-kind="{k}" data-group="{group}" data-date="{e["date"]}" data-n="{len(same)}"><details>'
                           f'<summary><span class="ev-k {cls}"><span class="ev-ico" aria-hidden="true"></span>{esc(label)}</span>'
                           f'<span class="ev-main"><span class="ev-t">{esc(EV_FOLD[k].format(n=len(same)))}</span>'
                           f'<span class="ev-d muted small">Show them</span></span></summary>'
                           f'<ol class="ev-sub">{"".join(row(x) for x in same)}</ol></details></li>')
            else:
                out.append(row(e))
        return "".join(out)

    feed = "".join(f'<section class="ev-day" data-date="{d}"><h3><span>{day_label(d)}</span><span class="muted ev-n">{n_(len(es), "change")}</span></h3>'
                   f'<ol class="ev-list">{day_rows(es)}</ol></section>' for d, es in days.items())
    present = {EV_KINDS.get(e["kind"], ("", "cards", ""))[1] for e in evs}
    chips = '<button data-v="all" class="on">All</button>' + "".join(f'<button data-v="{g}">{esc(l)}</button>' for g, l in EV_GROUPS if g in present)
    body = f"""<div class="page-h"><div><h1>What's new</h1><p class="lead">Everything that changed in Mantis, newest first: sources, questions and answers, decisions, stage moves, and pages or Jira items updated.</p></div></div>
<div class="toolbar ev-bar nocopy"><div class="seg" id="ev-range" aria-label="Period"><button data-v="visit">Since your last visit</button><button data-v="7" class="on">7 days</button><button data-v="30">30 days</button></div>
<div class="chips" id="ev-kind" aria-label="Kind of change">{chips}</div></div>
<p class="muted small ev-sum" id="ev-sum" aria-live="polite"></p>
<div class="ev-feed" id="ev-feed" data-today="{today.isoformat()}">{feed or '<p class="empty">Nothing changed in the last 30 days.</p>'}</div>
<p class="empty" id="ev-none" hidden>Nothing of this kind in this period.</p>"""
    return shell("What's new", body, active="sources", built=built, kind="changes")
