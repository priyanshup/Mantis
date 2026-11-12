/* drawer: the People and Library side panel. */
Mantis.define("drawer", ["core", "jobs", "people-data", "drafts"], (m_core, m_jobs, m_peopleData, m_drafts) => {
  const { $, $$, esc, toast, bus } = m_core;
  const { jBase } = m_jobs;
  const { xOn, X, loadX, dShort, fuRow, stepRow, briefLinks } = m_peopleData;
  const { draftData } = m_drafts;
  // ---- The owner's day (MANTIS-IMP-094): Today's pull brief and meetings, the Meetings page, Sources, the People & library panel ----
  // Live data from tools/serve.py; uses X, loadX, xPost, fuRow, stepRow, briefLinks, dShort and draftData from the parts before.
  const when = (s) => s ? new Date(s).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";

  // ---- People & library: one side panel from any page. A name anywhere opens that person ----
  const dr = $("#drawer");
  let lastFocus = null, peopleCache = null, libCache = null, view = "people";
  const getJson = async (name, cache) => cache || (await (await fetch(jBase + name, { cache: "no-store" })).json());
  function openDrawer(v, person) {
    if (!dr) return;
    if (dr.hidden) lastFocus = document.activeElement;
    view = v; dr.hidden = false; document.body.classList.add("drawer-open");
    if (!$(".dr-h", dr)) {
      dr.innerHTML = `<div class="dr-h"><h2 class="dr-title">People</h2>` +
        `<button type="button" class="mini icon dr-x" aria-label="Close the panel" title="Close (Esc)">✕</button></div><div class="dr-b" tabindex="-1"></div>`;
    }
    $$("[data-dv]", dr).forEach((b) => { b.classList.toggle("on", b.dataset.dv === v); b.setAttribute("aria-selected", String(b.dataset.dv === v)); });
    if (xOn && !X.d) loadX();
    (person ? showPerson(person) : v === "people" ? showPeople() : showLibrary()).then(() => { const f = $(".dr-b input, .dr-b button, .dr-b a", dr); (f || $(".dr-b", dr)).focus(); });
  }
  function closeDrawer() {
    if (!dr || dr.hidden) return;
    dr.hidden = true; delete dr.dataset.person; document.body.classList.remove("drawer-open");
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  async function showPeople(q = "") {
    peopleCache = await getJson("people.json", peopleCache).catch(() => []);
    delete dr.dataset.person;
    const row = (p) => `<button type="button" class="row dr-row" data-person="${esc(p.name)}"><span class="row-t">${esc(p.name)}<span class="muted small">${esc(p.role)}</span></span>` +
      `${p.can.length ? `<span class="pill w-jira plain">${p.can.length} to ask</span>` : ""}</button>`;
    $(".dr-b", dr).innerHTML = `<input type="search" class="dr-q" placeholder="Filter people…" aria-label="Filter people" value="${esc(q)}"><div class="dr-list">${peopleCache.map(row).join("")}</div>` +
      `<a class="small dr-more" href="${jBase}people.html">Open everyone on one page</a>`;
    const inp = $(".dr-q", dr);
    inp.addEventListener("input", () => { const s = inp.value.toLowerCase(); $$(".dr-row", dr).forEach((r) => (r.hidden = s && !r.textContent.toLowerCase().includes(s))); });
  }
  async function showPerson(name) {
    peopleCache = await getJson("people.json", peopleCache).catch(() => []);
    const p = peopleCache.find((x) => x.name === name || (x.aliases || []).includes(name)) || peopleCache.find((x) => x.name.split(" ")[0] === name.split(" ")[0]);
    if (!p) { toast(`${name} is not in the people file yet.`); return showPeople(); }
    dr.dataset.person = p.name;
    if (p.draft) draftData[p.name] = p.draft;
    const field = (label, v, key) => v ? `<div class="pp-f"><span class="muted small">${label}</span><span>${(p.proposed || []).includes(key) ? '<span class="tag">Proposed</span> ' : ""}${esc(v)}</span></div>` : "";
    const g = ((X.d || {}).followups || {})[p.name] || { items: [], steps: [] };
    const meets = ((X.d || {}).meetings || []).filter((m) => (m.attendees || []).some((a) => a === p.name || a === p.name.split(" ")[0]));
    $(".dr-b", dr).innerHTML = `<button type="button" class="linkish small dr-back" data-dv-back>← All people</button><h2 class="dr-name">${esc(p.name)}</h2>` +
      field("Role", p.role, "role") + field("Team", p.team, "team") + field("Channel", p.channel, "channel") + field("How to brief them", p.briefing, "briefing") + field("Notes", p.notes, "notes") +
      (meets.length ? `<p class="lt-h">Meets you</p><ul class="dr-ul">${meets.map((m) => `<li><a href="${jBase}meetings.html#m-${esc(m.key)}">${esc(m.name)}</a> <span class="muted small">${esc(m.day)}${m.next ? ", next " + dShort(m.next) : ""}</span></li>`).join("")}</ul>` : "") +
      (p.can.length ? `<p class="lt-h">Can answer</p><ul class="dr-ul">${p.can.map((c) => `<li><a href="${jBase}questions.html#k=${c.k}">${esc(c.q)}</a>${c.named ? "" : ' <span class="muted small">(maybe)</span>'}</li>`).join("")}</ul>` : "") +
      (g.items.length + g.steps.length ? `<p class="lt-h">Open with them</p><ul class="fu-list">${g.items.map(fuRow).join("")}${g.steps.map(stepRow).join("")}</ul>` : "") +
      (X.d && briefLinks(p.name) ? `<div class="chips sc-chips">${briefLinks(p.name)}</div>` : "") +
      `<div class="tile-acts nocopy">${`<button type="button" class="act job ai" data-job="meeting-brief" data-arg="${esc(p.name)}" title="Uses Claude, on your normal quota">Brief me</button>`}` +
      (p.draft ? `<button type="button" class="act" data-draft="${esc(p.name)}">Draft a message</button>` : "") + `<button type="button" class="act pp-add" data-person="${esc(p.name)}">+ Follow-up</button></div>`;
  }
  async function showLibrary() {
    libCache = await getJson("library.json", libCache).catch(() => []);
    delete dr.dataset.person;
    const kinds = [...new Set(libCache.map((i) => i.kind))];
    $(".dr-b", dr).innerHTML = `<input type="search" class="dr-q" placeholder="Filter the library…" aria-label="Filter the library">` +
      kinds.map((k) => `<p class="lt-h">${esc(k)}s</p><div class="dr-list">${libCache.filter((i) => i.kind === k).map((i) => `<a class="row dr-row" href="${jBase}${i.href}"><span class="row-t">${esc(i.title)}<span class="muted small">${esc(i.where)}</span></span></a>`).join("")}</div>`).join("") +
      `<p class="lt-h">Also</p><div class="dr-list"><a class="row dr-row" href="${jBase}library.html#diagrams"><span class="row-t">Diagrams</span></a><a class="row dr-row" href="${jBase}library.html#decisions"><span class="row-t">Decisions</span></a></div>` +
      `<a class="small dr-more" href="${jBase}library.html">Open the full library</a>`;
    const inp = $(".dr-q", dr);
    inp.addEventListener("input", () => { const s = inp.value.toLowerCase(); $$(".dr-row", dr).forEach((r) => (r.hidden = s && !r.textContent.toLowerCase().includes(s))); });
  }
  if (dr) {
    dr.addEventListener("click", (e) => {
      if (e.target.closest(".dr-x")) closeDrawer();
      const t = e.target.closest("[data-dv]"); if (t) openDrawer(t.dataset.dv);
      if (e.target.closest("[data-dv-back]")) openDrawer("people");
    });
    document.addEventListener("click", (e) => {   // any name with data-person opens that person (search results included)
      const p = e.target.closest("[data-person]:not(.pp-add):not(#drawer)");   // the panel itself carries data-person while it shows someone
      if (!p || e.target.closest(".tile-acts")) return;
      e.preventDefault(); e.stopPropagation();
      bus.emit("palette:close");
      openDrawer("people", p.dataset.person);
    }, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !dr.hidden && !document.querySelector(".modal-wrap")) closeDrawer(); });
    document.addEventListener("click", (e) => {   // a click anywhere outside the panel closes it (a name elsewhere opens that person instead)
      if (!dr.hidden && !e.composedPath().includes(dr) && !e.target.closest("[data-person], [data-dopen], .modal-wrap, #palette, #toast")) closeDrawer();
    });
  }
  bus.on("drawer:open", (view, person) => openDrawer(view, person));
});
