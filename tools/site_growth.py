"""The Growth tab: the owner's opportunities to step up, what came of them, learnings and recognition, toward the
next role. Drawn by app.js from GET /api/growth (tools/growth.py); this file builds only the frame."""
import json
from site_common import *   # noqa: F401,F403  (shared state and helpers)


def page_growth(features, built):
    """One add line (the page's main action), what Mantis proposes, what is in progress and what is done; a quiet
    side column with the strengths the role asks for, recognition and learnings; the appraisal record folded."""
    followed = set(FOCUS.get("following", []))
    cards = sorted(([c["slug"], c["title"], int(c["slug"] in followed)] for c in features + TOPICS if not archived(c["slug"])),
                   key=lambda x: (-x[2], x[1].lower()))
    body = f"""<div class="page-h"><div><p class="eyebrow" id="g-goal"></p><h1>Growth</h1><p class="lead" id="g-lead"></p></div></div>
<p class="empty" id="g-offline" hidden>Your growth record is saved by the Mantis site server. Open the site at http://localhost:8000.</p>
<div class="today-grid"><div class="today-main">
<form id="g-add" class="t-add g-add nocopy" autocomplete="off" data-cards='{esc(json.dumps(cards))}'><span class="pm" aria-hidden="true">+</span>
<input id="g-title" type="text" placeholder="What did you spot, do or learn?" aria-label="New growth entry" maxlength="300">
<div class="t-add-more"><button type="button" class="pick" data-gpick="kind" data-value="contribution">Contribution</button>
<button type="button" class="pick" data-gpick="area" data-value="">Strength</button>
<button type="button" class="pick" data-gpick="card" data-value="">Feature</button>
<input id="g-said" class="pick-in" type="text" placeholder="Who said it" maxlength="80" aria-label="Who said it" hidden>
<button class="key-sm t-go" type="submit">Note it</button></div></form>
<section class="blk" id="g-wait" aria-labelledby="g-wait-h" hidden><div class="blk-h"><h2 id="g-wait-h">From Mantis</h2><button type="button" class="linkish" id="g-wait-more" hidden></button></div>
<p class="muted small g-note">Nothing here counts until you take it or confirm it.</p><div id="g-wait-b" class="rows"></div></section>
<section class="blk" aria-labelledby="g-doing-h"><div class="blk-h"><h2 id="g-doing-h">Doing</h2><button type="button" class="linkish" id="g-doing-more" hidden></button></div>
<div id="g-doing-b" class="rows">{SKEL}</div></section>
<section class="blk" aria-labelledby="g-done-h"><div class="blk-h"><h2 id="g-done-h">Done</h2><button type="button" class="linkish" id="g-done-more" hidden></button></div>
<div id="g-done-b" class="rows"></div></section>
<details class="fold g-record" id="g-record"><summary><h2>Appraisal record</h2></summary><div class="sec" id="g-record-b"></div></details>
</div>
<aside class="today-side rail" aria-label="Strengths, recognition and learnings">
<section class="rail-blk" id="g-cov"><h2>Strengths</h2><p class="muted small" id="g-cov-n"></p><div id="g-cov-b"></div></section>
<section class="rail-blk" id="g-rec" hidden><h2>Recognition</h2><div id="g-rec-b"></div></section>
<section class="rail-blk" id="g-learn" hidden><h2>Learnings</h2><div id="g-learn-b"></div></section>
</aside></div>"""
    return shell("Growth", body, active="growth", built=built)
