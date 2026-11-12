/* widgets-features.js: the widgets on Features (the list) and on a feature's page, and both screens. layout.json decides where each one sits. */
UI.widget("features.tabs", (c) => `<div class="fbar"><div class="seg" id="fseg">${["Following", "Topics", "Archived"].map((v) => `<button data-fv="${v}" aria-pressed="${v === c.view}">${v}<span class="m">${c.lists[v].length}</span></button>`).join("")}</div><label class="fsearch">${UI.icon("find")}<input type="search" id="fq" class="field" placeholder="Find a feature" aria-label="Find a feature" value="${esc(c.q)}" autocomplete="off"></label></div>`);
const rowsHtml = (c) => `<div class="fl"><div class="frow fhead"><span>${c.view === "Topics" ? "Topic" : "Feature"}</span><span>Needs you</span><span>Stage</span><span class="r">Sources</span><span></span></div>${c.body || UI.empty(c.q ? `No feature matches "${esc(c.q)}".` : c.view === "Archived" ? "Nothing archived." : "Nothing here.")}</div>`;
UI.widget("features.rows", rowsHtml);
document.addEventListener("input", (e) => {   // typing narrows the list in place; the box keeps its focus
  if (e.target.id !== "fq") return;
  ST.fq = e.target.value; const fl = $(".fl"); if (fl) fl.outerHTML = rowsHtml(featuresView());
});

S.features = () => {
  const c = featuresView();
  return `<div class="screen">${UI.head("Features", { sub: c.sub })}${UI.place("features", c)}</div>`;
};

/* a feature's page: Overview, Epic and stories, Pages */
UI.widget("feature.stage", ({ F }) => `<div class="stagebox"><b>${STAGES[F.stage]}</b><i class="trk wide"><i style="width:${Math.round((F.stage + 1) / 3 * 100)}%"></i></i><small>Step ${F.stage + 1} of 3 · ${F.sources} sources</small></div>
    <div class="facts">${F.priority ? `<div><b>${F.priority}</b><span>priority</span></div>` : ""}${F.estimate ? `<div><b>${esc(F.estimate.split(",")[1] ? F.estimate.split(",")[1].trim() : F.estimate)}</b><span>effort</span></div>` : ""}${F.jira ? `<div><b>${esc(F.jira)}</b><span>Jira epic</span></div>` : ""}<div><b>${F.stories.length}</b><span>stories</span></div></div>`);
UI.widget("feature.needs", ({ F, tasks, qs }) => UI.cardHead("Needs you")
  + `<ul class="rows"><li><span class="t">${tasks} ${tasks === 1 ? "task" : "tasks"} in your plan</span><a class="link" href="#today">Open</a></li><li><span class="t">${qs} open ${qs === 1 ? "question" : "questions"}</span><button class="link" data-qfeat="${esc(featShort(F.title))}">Open</button></li></ul>`);
UI.widget("feature.card", ({ F }) => UI.cardHead("The card", { action: `<a class="link" href="features/${esc(F.slug)}.html">Open the full card</a>` }) + `<p class="muted u-measure">${esc(F.summary)}</p>`);
UI.widget("feature.people", ({ people }) => UI.cardHead("People")
  + (people.length ? `<ul class="rows">${people.map((n) => `<li><span class="t">${esc(n)}<small>Waiting on them</small></span></li>`).join("")}</ul>` : UI.empty("Nobody is waiting on this card.")));

UI.widget("feature.items", ({ items }) => `<ul class="rows mlist">${items.map((x, i) => `<li><button class="mi" data-st="${i}" aria-pressed="${i === ST.st}"><span class="chip ${i === 0 ? "hot" : ""}">${esc(x.key || "Epic")}</span><span class="t clamp">${esc(x.title)}</span></button></li>`).join("")}</ul>`);
UI.widget("feature.reader", ({ o }) => readerHtml(o));
UI.widget("feature.pagelist", ({ F }) => `<ul class="rows mlist"><li><div class="mi" aria-current="true"><span class="chip">Confluence</span><span class="t clamp">${esc(F.title)}</span></div></li></ul>`);
UI.widget("feature.pagebody", ({ F, text }) => `<div class="rd-top"><span class="chip">Confluence</span></div><h2 class="rd-t">${esc(F.title)}</h2><div class="rd-a"><button class="btn2" data-copy="${esc(text)}">Copy all</button><span class="hint">Copies the page text as shown, ${text.split("\n").length} lines.</span></div><div class="md">${md(UJ)}</div>`);

function ftabHtml() {
  const F = curFeat(), items = FITEMS();
  if (ST.ft === "Epic and stories") return UI.place("features.reader", { items, o: items[Math.min(ST.st, items.length - 1)] });
  if (ST.ft === "Pages") return UJ ? UI.place("features.pages", { F, text: UJ.replace(/^---[\s\S]*?\n---\n?/, "") }) : UI.card(UI.empty("No Confluence page is written for this feature yet."), { i: 0 });
  const tasks = REAL.tasks.filter((t) => LV.gcard[t.g] === F.slug).length, qs = QALL.filter((q) => q.feat === featShort(F.title)).length;
  const people = Object.entries(((window.__LIVE.extra || {}).followups) || {}).filter(([, v]) => (v.items || []).some((i) => i.card === F.slug && i.status === "open")).map(([n]) => n);
  return UI.place("features.overview", { F, tasks, qs, people });
}
S.promotions = () => {
  const F = curFeat(); setFeatData(F);
  const eps = F.stories.length + 1, tabs = [["Overview", ""], ["Epic and stories", eps], ["Pages", F.page ? 1 : ""]];
  const c = LV.cards.find((x) => x.slug === F.slug);
  const follow = c ? `<button type="button" class="pick nochev ${c.following ? "set" : ""}" data-follow="${c.following ? "unfollow" : "follow"}" data-slug="${esc(F.slug)}">${c.following ? "Following" : "Follow"}</button>` : "";
  return `<div class="screen"><a class="crumb" href="#features">← Features</a>${UI.head(esc(featShort(F.title)), { sub: esc(F.summary), action: follow, flush: true, titleClass: "vt-ftitle" })}
  <div class="seg" id="ftabs">${tabs.map(([n, c]) => `<button data-ft="${n}" aria-pressed="${ST.ft === n}">${n}${c ? `<span class="m">${c}</span>` : ""}</button>`).join("")}</div><div id="fbody">${ftabHtml()}</div></div>`;
};
