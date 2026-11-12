/* feature.js (2026-11-11): a feature's page, from the mock's screens, filled from static.json (the card, its epic, stories and page). */
LV.gcard = {};
((window.__LIVE.tasks || {}).groups || []).forEach((g) => (LV.gcard[g.name] = g.card));
const featShort = (t) => String(t || "").replace(/\s*\([^)]*\)\s*$/, "").split(":")[0];
function curFeat() {
  const all = (window.__LIVE.stat || {}).features || [], slug = ST.curF || (FEATS[0] || {}).slug;
  return all.find((f) => f.slug === slug) || { slug: "", title: "Feature", stories: [], epics: [], page: "", summary: "", stage: 0, priority: "", estimate: "", jira: "", sources: 0 };
}
function setFeatData(F) {
  STORIES.length = 0;
  STORIES.push(...F.stories.map((s) => ({ key: s.key, title: s.title, asa: s.story, bg: s.bg, ac: s.ac, edge: s.edge, oos: s.oos, oq: s.oq })));
  const e = F.epics[0];
  EPIC.key = (e ? e.key : F.jira) || "Epic"; EPIC.title = e ? e.title : F.title; EPIC.type = "Epic";
  EPIC.sections = e ? [["Job", "text", e.story], ["Why", "text", e.bg], ["Acceptance criteria", "list", e.ac], ["Out of scope", "list", e.oos]] : [["Summary", "text", F.summary]];
  UJ = F.page || "";
}
/* a click on a feature opens that feature's page */
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest(".frow[data-f]"); if (!b || e.target.closest("[data-follow],[data-arch]")) return;
  if (b.dataset.kind === "topic") { location.href = "features/" + b.dataset.slug + ".html"; return; }
  const f = LV.cards.find((x) => x.slug === b.dataset.slug); if (!f) return;
  ST.curF = f.slug; ST.ft = "Overview"; ST.st = 0; location.hash = "promotions";
}, true);

/* ---- the Features screen: Following, Topics, Archived, and follow or unfollow ---- */
const STAR = '<svg viewBox="0 0 24 24" width="18" height="18" stroke-width="1.7" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.6l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9L12 17l-5.3 2.8 1.1-5.9L3.5 9.8l5.9-.8z"/></svg>';
function refreshFeats() {
  FEATS.length = 0;
  FEATS.push(...LV.cards.filter((c) => c.kind === "feature" && c.following && !c.archived).map((c) => ({ title: c.title, stage: c.stage, priority: c.priority, sources: c.sources, slug: c.slug })));
}
(function () {
  const st = window.__LIVE.stat || {};
  LV.cards = [...(st.features || []).map((f) => ({ kind: "feature", slug: f.slug, title: featShort(f.title), stage: f.stage, priority: f.priority, sources: f.sources, following: !!f.following, archived: !!f.archived })),
    ...(st.topicsList || []).map((t) => ({ kind: "topic", slug: t.slug, title: featShort(t.title), sources: t.sources, following: !!t.following, archived: !!t.archived }))];
  refreshFeats();
})();
function featuresView() {
  const view = ST.fview || "Following", C = LV.cards;
  const lists = { Following: C.filter((c) => c.following && !c.archived), Topics: C.filter((c) => c.kind === "topic" && !c.archived), Archived: C.filter((c) => c.archived) };
  const q = (ST.fq || "").trim().toLowerCase(), hit = (c) => !q || `${c.title} ${c.priority || ""} ${STAGES[c.stage] || ""}`.toLowerCase().includes(q);   // the search box narrows the rows, not the tab counts
  const rest = view === "Following" ? C.filter((c) => !c.following && !c.archived && c.kind === "feature" && hit(c)) : [];
  const qc = {}; QALL.forEach((q) => (qc[q.feat] = (qc[q.feat] || 0) + 1));
  const tcount = (slug) => REAL.tasks.filter((t) => LV.gcard[t.g] === slug).length;
  let n = 0;
  const row = (c) => {
    const t = tcount(c.slug), q = qc[c.title] || 0, bits = [t ? `${t} ${t === 1 ? "task" : "tasks"}` : "", q ? `${q} ${q === 1 ? "question" : "questions"}` : ""].filter(Boolean).join(", ");
    const stage = c.kind === "feature" ? `<span class="fstage"><b>${STAGES[c.stage]}</b><i class="trk"><i style="width:${Math.round((c.stage + 1) / 3 * 100)}%"></i></i><small>Step ${c.stage + 1} of 3</small></span>` : '<span class="fstage"><small>Topic</small></span>';
    const act = view === "Archived" ? `<button type="button" class="link" data-arch="unarchive" data-slug="${esc(c.slug)}">Restore</button>`
      : `<button type="button" class="star" data-follow="${c.following ? "unfollow" : "follow"}" data-slug="${esc(c.slug)}" aria-pressed="${c.following}" aria-label="${c.following ? "Unfollow" : "Follow"} ${esc(c.title)}" title="${c.following ? "Following. Click to unfollow." : "Follow this"}">${STAR}</button><button type="button" class="link arch" data-arch="archive" data-slug="${esc(c.slug)}" title="Archive it out of your lists">Archive</button>`;
    return `<div class="frow rise" style="--i:${Math.min(n++, 10)}" role="link" tabindex="0" data-f="${esc(c.title)}" data-slug="${esc(c.slug)}" data-kind="${c.kind}"><span class="fn" ${ST.lastF === c.title ? 'style="view-transition-name:ftitle"' : ""}>${esc(c.title)}</span><span class="fneeds ${bits ? "" : "none"}">${bits || "Nothing waiting on you"}</span>${stage}<span class="mono fsrc">${c.sources}</span><span class="fact">${act}</span></div>`;
  };
  const byPrio = (label, list) => (list.length ? `<div class="fgroup cap muted">${label}</div>${list.map(row).join("")}` : "");
  const fl = lists.Following.filter(hit), feats = fl.filter((c) => c.kind === "feature");
  const body = view === "Following"
    ? byPrio("P1", feats.filter((c) => c.priority === "P1")) + byPrio("P2", feats.filter((c) => c.priority === "P2")) + byPrio("No priority set", feats.filter((c) => c.priority !== "P1" && c.priority !== "P2")) + byPrio("Topics", fl.filter((c) => c.kind === "topic")) + byPrio("Not following", rest)
    : lists[view].filter(hit).map(row).join("");
  const sub = { Following: `${lists.Following.length} ${lists.Following.length === 1 ? "card" : "cards"} you follow. Click the star to follow or unfollow.`, Topics: "Topic cards: the systems, teams and themes behind the features.", Archived: "Archived cards are out of your lists. Restore one to use it again." }[view];
  return { view, lists, sub, body, q };
}
document.addEventListener("click", async (e) => {
  const fv = e.target.closest("[data-fv]"); if (fv) { ST.fview = fv.dataset.fv; show("features"); return; }
  const b = e.target.closest("[data-follow],[data-arch]"); if (!b) return;
  e.stopImmediatePropagation(); e.preventDefault();
  const slug = b.dataset.slug, action = b.dataset.follow || b.dataset.arch, c = LV.cards.find((x) => x.slug === slug); if (!c) return;
  try {
    const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ slug, action }) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "That did not work.");
  } catch (er) { toast(er.message); return; }
  if (action === "follow") c.following = true; if (action === "unfollow") c.following = false;
  if (action === "archive") { c.archived = true; c.following = false; } if (action === "unarchive") c.archived = false;
  refreshFeats(); show(location.hash.slice(1) || "today");
  toast({ follow: `Following ${c.title}.`, unfollow: `Stopped following ${c.title}.`, archive: `Archived ${c.title}.`, unarchive: `Restored ${c.title}.` }[action]);
}, true);
