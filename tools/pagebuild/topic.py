"""The topic card page."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
from pagebuild.feature import card_tasks, confluence_pages, feature_questions, overview, questions_html, side_people, sources_tab
from pagebuild.frame import job_btn, shell
from pagebuild.registry import archived
from pagebuild.text import esc, n_


def page_topic(t, topics, built):
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is t else ""}>{esc(x["title"])}</option>' for x in topics if x is t or not archived(x["slug"]))
    qs = feature_questions(t["slug"])
    nnew = len(t.get("new_docs", []))
    meta = ["Topic", "Archived" if archived(t["slug"]) else "",
            f'<a href="#sources"{" class=\"warn-text\"" if nnew else ""}>{n_(len(t["docs"]), "source")}{f", {nnew} new" if nnew else ""}</a>', f'updated {esc(t["updated"])}']
    tabs = (f'<a href="#overview" data-match="overview">Overview</a>'
            + (f'<a href="#questions" data-match="questions">Questions <span class="n">{len(qs)}</span></a>' if qs else "")
            + f'<a href="#sources" data-match="sources">Sources <span class="n">{len(t["docs"])}</span></a>')
    body = f"""
<p class="crumbs"><a href="../features.html#all">Features</a></p>
<div class="page-h feat-h"><div><h1>{esc(t["title"])}</h1><p class="meta-line">{" · ".join(m for m in meta if m)}</p></div>
<div class="ph-acts nocopy"><details class="pop pop-r"><summary class="btn-line" aria-label="More">⋯</summary><div class="pop-b">
{job_btn("refresh-card", "Refresh summary", arg=t["slug"], cls="btn-line")}<select id="switch" class="sel sel-sm" aria-label="Go to another topic">{switch}</select></div></details>
<button type="button" class="btn copy-ov">Copy summary</button></div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs" aria-label="This topic">{tabs}</nav>
<div class="tab-panel" id="p-overview">{overview(t["card_md"], t["slug"])}</div>
<div class="tab-panel" id="p-questions" hidden>{questions_html(qs, "../")}</div>
<div class="tab-panel" id="p-sources" hidden>{sources_tab(t["card_md"])}</div></div>
<aside class="side rail">{card_tasks(t["slug"])}{confluence_pages(t["docs"], t["title"])}{side_people(t["slug"], "topic") or '<p class="empty">No people or systems named yet.</p>'}</aside>
</div>"""
    return shell(t["title"], body, base="../", active="features", built=built, kind="topic")
