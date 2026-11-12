/* people-data: follow-ups, briefs, deadlines and meetings, live from the server. */
Mantis.define("people-data", ["jobs", "core"], (m_jobs, m_core) => {
  const { jobsOn, jBase, getJState } = m_jobs;
  const { $, toast, esc, plural, $$, copyHtml } = m_core;
  // ---- People, follow-ups, briefs, deadlines, meetings, away (MANTIS-IMP-020/022/037/038/041) ----
  // Live data from tools/serve.py (GET /api/extra), changed through POST /api/followups, /api/deadlines,
  // /api/schedule. Briefs and handovers are written by Claude jobs and opened here; each bullet expands.
  const X = { d: null };
  const xOn = jobsOn;   // live data is loaded where a page shows it, or when the People panel opens
  const xHere = () => $("#t-people") || $(".people-grid") || $("#mt-list");
  const dShort = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : "";
  const ago = (d) => { const n = Math.round((Date.now() - new Date(d + "T12:00").getTime()) / 864e5); return n <= 0 ? "today" : n === 1 ? "1 day" : `${n} days`; };
  const first = (n) => String(n || "").split(" ")[0];
  async function xPost(path, body, msg) {
    try {
      const r = await fetch(jBase + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json();
      if (!r.ok) { toast(j.error || "That didn't work."); return null; }
      X.d = j; paintX(); if (msg) toast(msg); return j;
    } catch (e) { toast("The Mantis server isn't running."); return null; }
  }
  async function loadX() {
    try { X.d = await (await fetch(jBase + "api/extra", { cache: "no-store" })).json(); paintX(); } catch (e) {}
  }
  const peopleList = () => `<datalist id="pp-names">${(X.d.people || []).map((p) => `<option value="${esc(p.name)}">`).join("")}</datalist>`;
  // A multi-pick box (2026-11-02): pick from the list and keep picking; the list reopens on focus, click or typing.
  // People not on the list can be typed and kept (Enter or comma); subjects come only from the list.
  const PICK = {
    attendees: { free: true, opts: () => (X.d.people || []).map((p) => ({ v: p.name, l: p.name, hint: (p.role || "").split(/[;,.(]/)[0].trim().slice(0, 48), q: [p.name, ...(p.aliases || [])].join(" ") })) },
    cards: { free: false, opts: () => (X.d.subjects || []).map((s) => ({ v: s.slug, l: s.title, q: s.title })) },
    // besides the written agenda, which always leads; none picked = only the written agenda
    draws: { free: false, opts: () => [{ v: "people", l: "Open items with the attendees", hint: "Their follow-ups and questions, any subject", q: "open items attendees people 1-1 follow-ups" },
      { v: "subjects", l: "Open items on its subjects", hint: "Questions, decisions and changes on its features", q: "open items subjects features topics" }] },
  };
  const pickBox = (name, ph, label) => `<div class="pick" data-pick="${name}"><span class="pick-chips"></span><input class="pick-in" placeholder="${esc(ph)}" aria-label="${esc(label)}" ` +
    `autocomplete="off" role="combobox" aria-expanded="false" aria-autocomplete="list"><input type="hidden" name="${name}"><ul class="pick-list" role="listbox" hidden></ul></div>`;
  const pickVals = (box) => $("input[type=hidden]", box).value.split(",").map((x) => x.trim()).filter(Boolean);
  function pickSet(box, vals) {
    const cfg = PICK[box.dataset.pick], lab = Object.fromEntries(cfg.opts().map((o) => [o.v, o.l]));
    vals = [...new Set(vals)];
    $("input[type=hidden]", box).value = vals.join(", ");
    $(".pick-chips", box).innerHTML = vals.map((v) => `<span class="pick-chip">${esc(lab[v] || v)}<button type="button" data-unpick="${esc(v)}" aria-label="Remove ${esc(lab[v] || v)}">✕</button></span>`).join("");
    const inp = $(".pick-in", box);
    if (inp.dataset.ph === undefined) inp.dataset.ph = inp.placeholder;
    inp.placeholder = vals.length ? "" : inp.dataset.ph;
  }
  function pickOpen(box) {
    const cfg = PICK[box.dataset.pick], inp = $(".pick-in", box), ul = $(".pick-list", box), have = new Set(pickVals(box));
    const q = inp.value.trim().toLowerCase();
    delete ul.dataset.nav;
    const rank = (o) => !q ? 1 : o.q.toLowerCase().split(/\s+/).some((w) => w.startsWith(q)) ? 1 : o.q.toLowerCase().includes(q) ? 2 : 0;   // word starts before mid-word
    const hits = cfg.opts().filter((o) => !have.has(o.v) && rank(o)).sort((a, b) => rank(a) - rank(b)).slice(0, 8);
    ul.innerHTML = hits.map((o, i) => `<li role="option" data-v="${esc(o.v)}"${i === 0 ? ' class="on"' : ""}><span>${esc(o.l)}</span>${o.hint ? `<small>${esc(o.hint)}</small>` : ""}</li>`).join("") ||
      (q && cfg.free ? `<li class="pick-new" data-free="1">Add “${esc(inp.value.trim())}”</li>` : `<li class="pick-none">${q ? "No match" : "All picked"}</li>`);
    ul.hidden = false; inp.setAttribute("aria-expanded", "true");
  }
  const pickClose = (box) => { $(".pick-list", box).hidden = true; $(".pick-in", box).setAttribute("aria-expanded", "false"); };
  function pickAdd(box, v) {
    const inp = $(".pick-in", box);
    if (v) pickSet(box, [...pickVals(box), v]);
    inp.value = ""; inp.focus(); pickOpen(box);   // stays open for the next pick
  }
  // The add-and-edit form for a regular meeting: settings once, then what its agenda draws on
  function fillMeetForm(f, m) {
    f.reset();
    f.elements.mid.value = m ? m.id : "";   // not "id": a control named id hides form.id, and the submit handler matches on it
    if (m) { ["name", "day", "time", "purpose"].forEach((k) => (f.elements[k].value = m[k] || "")); f.elements.every.value = String(m.every || 1); }
    pickSet($('[data-pick="attendees"]', f), m ? m.attendees || [] : []);
    pickSet($('[data-pick="cards"]', f), m ? m.set_cards || [] : []);
    pickSet($('[data-pick="draws"]', f), m ? m.draws || [] : ["people", "subjects"]);
    $("button[type=submit]", f).textContent = m ? "Save changes" : "Add meeting";
    const s = f.closest("details"); if (s) $("summary", s).textContent = m ? `Edit ${m.name}` : "Add a regular meeting";
  }
  function fuRow(f) {
    return `<li class="fu" data-fu="${f.id}"><div class="fu-t"><span class="pill ${f.kind === "wait" ? "w-review" : "w-jira"} plain">${f.kind === "wait" ? "Waiting" : "Raise"}</span><b>${esc(f.topic)}</b>` +
      `<span class="muted small">open ${ago(f.created)}${f.raised.length ? ` · raised ${f.raised.length}×, last ${dShort(f.raised[f.raised.length - 1])}` : ""}${f.chase ? ` · chase ${dShort(f.chase)}` : ""}</span></div>` +
      (f.detail ? `<p class="muted small fu-d">${esc(f.detail)}</p>` : "") +
      `<span class="fu-acts"><button type="button" class="mini" data-fa="raised" title="You brought it up today; it stays open">Raised today</button><button type="button" class="mini on" data-fa="done">Done</button><button type="button" class="mini icon" data-fa="delete" aria-label="Remove" title="Remove">✕</button></span></li>`;
  }
  const stepRow = (s) => `<li class="fu step"><div class="fu-t"><span class="pill s-none plain">Step</span><span>${esc(s.step)}</span><a class="muted small" href="${jBase}features/${s.card}.html">${esc(s.card_title)}</a><span class="muted small">${esc(s.status || "open")}${s.due ? ` · due ${dShort(s.due)}` : ""}</span></div></li>`;
  function briefLinks(forName, kind) {
    const bs = (X.d.briefs || []).filter((b) => (!forName || b.for === forName) && (!kind || b.kind === kind)).slice(0, 4);
    // the date shows once: a title that already carries it ("Weekly sync, 26 Oct") gets no second date
    const dated = (t, d) => { const x = new Date(d + "T12:00"), day = String(x.getDate()), mon = x.toLocaleDateString("en-GB", { month: "short" });
      return new RegExp(`\\b${day} ${mon}\\b|\\b${mon} ${day}\\b`, "i").test(t); };
    return bs.map((b) => { const t = b.title || b.for;
      return `<button type="button" class="chip" data-brief="${b.id}">${((k) => t.toLowerCase().startsWith(k.toLowerCase()) ? esc(t) : esc(k) + " · " + esc(t))({ handover: "Handover", status: "Status", answer: "Answer" }[b.kind] || "Brief")}${dated(t, b.date) ? "" : " · " + dShort(b.date)}</button>`; }).join("");
  }
  function paintX() {
    const d = X.d; if (!d) return;
    // Away planner
    const aw = $("#t-away");
    if (aw) {   // Time away: one line until five working days before, then what to do first and the handover
      const a = d.away;
      aw.hidden = false;
      if (a) {
        const before = d.before_away || [], cover = (a.cover || [])[0] || "";
        let wd = 0; for (let x = new Date(d.today + "T12:00"); x.toISOString().slice(0, 10) < a.start; x.setDate(x.getDate() + 1)) if (x.getDay() % 6) wd++;
        const opens = new Date(a.start + "T12:00"); for (let n = 0; n < 5;) { opens.setDate(opens.getDate() - 1); if (opens.getDay() % 6) n++; }
        const full = wd <= 5;
        aw.innerHTML = `<details class="away"${full ? " open" : ""}><summary class="ri"><span class="ri-h">Away ${dShort(a.start)} to ${dShort(a.end)}</span>` +
          `<span class="ri-s">${a.cover.length ? esc(a.cover.map(first).join(", ")) + " covers" : "Nobody covering yet"}${full ? "" : ` · handover opens ${dShort(opens.toISOString().slice(0, 10))}`}</span></summary>` +
          (before.length ? `<p class="lt-h">Before you go</p><ul class="away-list">${before.map((x) => `<li>${esc(x.title)}${x.due ? ` <span class="t-meta">due ${dShort(x.due)}</span>` : ""}</li>`).join("")}</ul>` : "") +
          `<div class="mb-row"><select id="ho-who" class="sel sel-sm" aria-label="Handover for">${(d.people || []).map((p) => `<option${p.name === cover ? " selected" : ""}>${esc(p.name)}</option>`).join("")}</select>` +
          `<button type="button" class="btn job ai" data-job="handover" data-arg-from="#ho-who" title="Uses Claude, on your normal quota">Handover</button></div>` +
          `<div class="chips sc-chips">${briefLinks("", "handover")}<button type="button" class="linkish" data-away-rm="${a.id}">Remove this leave</button></div></details>`;
      } else {
        aw.innerHTML = `<details class="away"><summary class="ri"><span class="ri-s">Plan time away</span></summary>` +
          `<form class="away-form" id="away-form"><label>From <input type="date" name="start" required></label><label>To <input type="date" name="end" required></label>` +
          `<label>Covering <input name="cover" list="pp-names" placeholder="Name"></label><button class="btn" type="submit">Save</button>${peopleList()}</form></details>`;
      }
    }
    // Today, main column: suggested deadlines belong next to the list they change
    const due = $("#t-due-sug");
    if (due) {
      const dl = d.deadlines || [];
      due.hidden = !dl.length;
      due.innerHTML = dl.length ? `<div class="sc-h"><h2><i class="bi bi-clock"></i>Suggested deadlines</h2><span class="muted small">Only suggestions; nothing changes until you accept</span></div><ul class="fu-list">` +
        dl.map((s) => `<li class="dl" data-task="${s.task_id}"><div><b>${esc(s.title)}</b><span class="muted small"><b>${dShort(s.date)}</b> · ${esc(s.why)}</span></div>` +
          `<span class="fu-acts"><button type="button" class="mini on" data-da="accept" data-date="${s.date}">Accept</button><input type="date" class="dl-date" value="${s.date}" aria-label="Another date"><button type="button" class="mini" data-da="change">Set</button><button type="button" class="mini" data-da="decline">No deadline</button></span></li>`).join("") + "</ul>" : "";
    }
    // Meetings page: the one-off brief picker and recent briefs (the regular meetings are drawn by paintDay)
    const mw = $("#mb-who");
    if (mw && !mw.options.length) mw.innerHTML = (d.people || []).map((p) => `<option value="${esc(p.name)}">${esc(p.name)}${p.role ? " · " + esc(p.role.split(/[;,.]/)[0]).slice(0, 48) : ""}</option>`).join("");
    const mbs = $("#mt-briefs");
    if (mbs) mbs.innerHTML = [briefLinks("", "meeting"), briefLinks("", "status")].join("");
    // Today, side column: who you are waiting on, as one line that opens to the follow-ups (asking is in Ctrl K)
    const tp = $("#t-people");
    if (tp) {
      const g = d.followups || {}, n = (p) => g[p].items.length + g[p].steps.length;
      const persons = Object.keys(g).filter((p) => n(p)).sort((a, b) => (n(b) - n(a)) || a.localeCompare(b));
      const fus = persons.map((p) => `<details class="fu-person"><summary><b>${esc(p)}</b><span class="fu-count">${n(p)}</span></summary>` +
        `<ul class="fu-list">${g[p].items.map(fuRow).join("")}${g[p].steps.map(stepRow).join("")}</ul></details>`).join("");
      const addFu = `<details class="fu-new"><summary class="linkish">Add a follow-up</summary><form class="fu-add" id="fu-add"><input name="person" list="pp-names" placeholder="Person" required aria-label="Person"><input name="topic" placeholder="What to raise or chase" required aria-label="Topic">` +
        `<select name="kind" class="sel sel-sm" aria-label="Kind"><option value="raise">Raise with them</option><option value="wait">Waiting on them</option></select><button class="btn-line" type="submit">Add</button>${peopleList()}</form></details>`;
      const top = persons.slice(0, 3).map((p) => `${esc(first(p))} ${n(p)}`).join(" · "), rest = persons.length - 3;
      tp.hidden = false;
      tp.innerHTML = `<h2>Waiting on</h2>` + (persons.length ? `<details class="wo" id="followups"><summary class="ri"><span class="ri-v">${top}</span><span class="ri-s">${rest > 0 ? `and ${plural(rest, "other")}` : "Open the list"}</span></summary>${fus}${addFu}</details>`
        : `<div class="ri-s">Nobody. ${addFu}</div>`);
    }
    // Meetings page: add a regular meeting (the list itself is drawn by paintDay)
    const pm = $("#pp-meetings");
    if (pm && !$("#meet-add", pm)) {
      pm.innerHTML = `<form class="fu-add meet-form" id="meet-add"><input type="hidden" name="mid"><label>Name <input name="name" placeholder="e.g. Sam 1-1" required></label>` +
        `<label>Day <select name="day" class="sel sel-sm">${["Mon", "Tue", "Wed", "Thu", "Fri"].map((x) => `<option>${x}</option>`).join("")}</select></label>` +
        `<label>Time <input name="time" type="time"></label><label>How often <select name="every" class="sel sel-sm"><option value="1">Weekly</option><option value="2">Every 2 weeks</option></select></label>` +
        `<div class="wide mf-f"><span class="mf-l" id="mf-with">With</span>${pickBox("attendees", "Pick or type names", "With")}</div>` +
        `<label class="wide">What it is for <textarea name="purpose" rows="2" maxlength="600" placeholder="The objective, e.g. agree next quarter's priorities with the other team"></textarea></label>` +
        `<div class="wide mf-f"><span class="mf-l">Subjects</span>${pickBox("cards", "Features or topics it covers", "Subjects")}</div>` +
        `<div class="wide mf-f"><span class="mf-l">Besides your written agenda, it draws on</span>${pickBox("draws", "Nothing else: only your agenda", "Besides your written agenda, it draws on")}</div>` +
        `<div class="mf-acts"><button class="btn" type="submit">Add meeting</button><button type="button" class="linkish" data-meet-cancel>Cancel</button></div></form>`;
      fillMeetForm($("#meet-add", pm), null);
    }
    if (typeof paintDay === "function") paintDay(d);
    // People page: counts and lists per person
    $$(".person").forEach((card) => {
      const name = card.dataset.name, g = (d.followups || {})[name] || { items: [], steps: [] };
      const ms = (d.meetings || []).filter((m) => (m.attendees || []).some((a) => a.toLowerCase() === name.toLowerCase() || first(name).toLowerCase() === a.toLowerCase()));
      const n = g.items.length + g.steps.length, badge = $(".pp-n", card);
      badge.hidden = !n; badge.textContent = n ? `${n} open` : "";
      $(".pp-live", card).innerHTML = (ms.length ? `<p class="muted small">Meets you: ${ms.map((m) => `${esc(m.name)} (${esc(m.day)}${m.next ? ", next " + dShort(m.next) : ""})`).join("; ")}</p>` : "") +
        (n ? `<ul class="fu-list">${g.items.map(fuRow).join("")}${g.steps.map(stepRow).join("")}</ul>` : "") +
        (briefLinks(name) ? `<div class="chips">${briefLinks(name)}</div>` : "");
    });
  }
  // Brief viewer: every bullet expands to its background, source and card
  async function openBrief(id) {
    let b;
    try { b = await (await fetch(jBase + "api/brief?id=" + encodeURIComponent(id), { cache: "no-store" })).json(); } catch (e) { return; }
    if (!b || !b.sections) { toast("That brief is gone."); return; }
    const m = document.createElement("div"); m.className = "modal-wrap";
    m.innerHTML = `<div class="modal brief-modal" role="dialog" aria-label="${esc(b.title)}"><div class="bm-h"><div><p class="hello">${{ handover: "Handover", status: "Status update", answer: "Ask Mantis" }[b.kind] || "Meeting brief"} · ${dShort(b.date)}</p><h2>${esc(b.title)}</h2></div>` +
      `<span class="bar-btns"><button type="button" class="btn-line" data-bcopy>Copy</button><button type="button" class="mini icon" data-bclose aria-label="Close">✕</button></span></div>` +
      `<div class="bm-body">${b.sections.map((s) => `<h3>${esc(s.name)}</h3><ul class="bb-list">${s.bullets.map((x) => `<li><details class="bb"><summary>${esc(x.text)}</summary><div class="bb-d">${x.detail ? `<p>${esc(x.detail)}</p>` : ""}` +
        `${x.source || x.card ? `<p class="muted small">${x.source ? "From: " + esc(x.source) : ""}${x.card ? ` · <a href="${jBase}features/${esc(x.card)}.html">open the card</a>` : ""}</p>` : ""}` +
        `${x.followup ? `<span class="fu-acts" data-fu="${esc(x.followup)}"><button type="button" class="mini" data-fa="raised">Raised today</button><button type="button" class="mini on" data-fa="done">Done</button></span>` : ""}</div></details></li>`).join("")}</ul>`).join("")}</div></div>`;
    document.body.appendChild(m);
    const close = () => m.remove();
    m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-bclose]")) close(); });
    document.addEventListener("keydown", function k(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", k); } });
    $("[data-bcopy]", m).addEventListener("click", () => { $$("details.bb", m).forEach((x) => (x.open = true)); copyHtml($(".bm-body", m)); });
  }
  if (xOn) {
    document.addEventListener("click", (e) => {
      const fb = e.target.closest("[data-fa]");
      if (fb) { const id = fb.closest("[data-fu]").dataset.fu; xPost("api/followups", { action: fb.dataset.fa, id }, { raised: "Noted: raised today. It stays open until done.", done: "Closed.", delete: "Removed." }[fb.dataset.fa]); return; }
      const da = e.target.closest("[data-da]");
      if (da) {
        const li = da.closest("[data-task]"), a = da.dataset.da;
        if (a === "decline") xPost("api/deadlines", { task_id: li.dataset.task, action: "decline" }, "Okay, no deadline. It won't be suggested again.");
        else xPost("api/deadlines", { task_id: li.dataset.task, action: "accept", date: a === "change" ? $(".dl-date", li).value : da.dataset.date }, "Deadline set.").then((j) => { if (j) document.dispatchEvent(new Event("mantis:tasks-changed")); });
        return;
      }
      const br = e.target.closest("[data-brief]"); if (br) { openBrief(br.dataset.brief); return; }
      const mr = e.target.closest("[data-meet-rm]");
      if (mr) { if (confirm(`${mr.getAttribute("aria-label") || "Remove this meeting"}? Its agenda and brief history stop showing here.`)) xPost("api/schedule", { action: "remove-meeting", id: mr.dataset.meetRm }, "Meeting removed."); return; }
      const ar = e.target.closest("[data-away-rm]"); if (ar && confirm("Remove this away period?")) { xPost("api/schedule", { action: "remove-away", id: ar.dataset.awayRm }, "Away period removed."); return; }
      const pa = e.target.closest(".pp-add");
      if (pa) { const t = prompt(`Follow-up with ${pa.dataset.person}: what do you want to raise or chase?`); if (t) xPost("api/followups", { action: "add", person: pa.dataset.person, topic: t }, "Follow-up added."); }
    });
    document.addEventListener("submit", (e) => {
      const f = e.target, v = (n) => (f.elements[n] || {}).value || "";
      if (f.id === "fu-add") { e.preventDefault(); xPost("api/followups", { action: "add", person: v("person"), topic: v("topic"), kind: v("kind") }, "Follow-up added.").then((j) => j && f.reset()); }
      if (f.id === "meet-add") { e.preventDefault(); const id = v("mid");
        xPost("api/schedule", { action: id ? "edit-meeting" : "add-meeting", id, name: v("name"), day: v("day"), time: v("time"), attendees: v("attendees"), every: v("every"),
          purpose: v("purpose"), cards: v("cards"), draws: v("draws") }, id ? "Meeting saved." : "Meeting added.")
          .then((j) => { if (j) { fillMeetForm(f, null); const am = f.closest("details"); if (am) am.open = false; } }); }
      if (f.matches("[data-agenda]")) { e.preventDefault();
        xPost("api/schedule", { action: "set-agenda", id: f.dataset.agenda, date: f.dataset.date, text: v("text") }, v("text").trim() ? "Agenda saved." : "Agenda removed."); }
      if (f.id === "away-form") { e.preventDefault(); xPost("api/schedule", { action: "add-away", start: v("start"), end: v("end"), cover: v("cover") }, "Away period saved."); }
    });
    // The multi-pick boxes
    document.addEventListener("focusin", (e) => { const b = e.target.closest(".pick-in") && e.target.closest(".pick"); if (b) pickOpen(b); });
    document.addEventListener("input", (e) => { const b = e.target.closest(".pick-in") && e.target.closest(".pick"); if (b) pickOpen(b); });
    document.addEventListener("focusout", (e) => { const b = e.target.closest(".pick"); if (b && !b.contains(e.relatedTarget)) pickClose(b); });
    document.addEventListener("mousedown", (e) => {
      const li = e.target.closest(".pick-list li"); if (!li) return;
      e.preventDefault();   // keeps the focus in the box, so the list stays open for the next pick
      const b = li.closest(".pick");
      if (li.dataset.v) pickAdd(b, li.dataset.v); else if (li.dataset.free) pickAdd(b, $(".pick-in", b).value.trim());
    });
    document.addEventListener("click", (e) => {
      const un = e.target.closest("[data-unpick]");
      if (un) { const b = un.closest(".pick"); pickSet(b, pickVals(b).filter((x) => x !== un.dataset.unpick)); $(".pick-in", b).focus(); return; }
      const b = e.target.closest(".pick"); if (b && $(".pick-in", b) && !e.target.closest(".pick-list")) { $(".pick-in", b).focus(); pickOpen(b); }   // a multi-pick box, not a picker button (Today, Growth)
    });
    document.addEventListener("keydown", (e) => {
      const inp = e.target.closest(".pick-in"); if (!inp) return;
      const b = inp.closest(".pick"), ul = $(".pick-list", b), items = $$("li[data-v]", ul), on = $("li.on", ul), q = inp.value.trim();
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); if (ul.hidden) { pickOpen(b); return; }
        const i = items.indexOf(on), n = items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length];
        if (on) on.classList.remove("on"); if (n) { n.classList.add("on"); n.scrollIntoView({ block: "nearest" }); ul.dataset.nav = "1"; }
      } else if ((e.key === "Enter" || e.key === "," || e.key === "Tab") && (q || ul.dataset.nav)) {
        // picks only what was typed or arrowed to; Enter in an untouched box still submits the form
        const pick = !ul.hidden && on ? on.dataset.v : PICK[b.dataset.pick].free ? q : "";
        if (!pick && e.key === "Tab") return;
        e.preventDefault(); delete ul.dataset.nav; pickAdd(b, pick);
      } else if (e.key === "Backspace" && !q) { const vs = pickVals(b); if (vs.length) { pickSet(b, vs.slice(0, -1)); pickOpen(b); } }
      else if (e.key === "Escape") { if (!ul.hidden) { e.stopPropagation(); pickClose(b); } }
    });
    const pf = $("#pp-filter");
    if (pf) pf.addEventListener("input", () => { const q = pf.value.toLowerCase(); $$(".person").forEach((c) => { c.hidden = q && !c.textContent.toLowerCase().includes(q); }); });
    if (location.hash && !location.hash.includes("=")) setTimeout(() => { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView({ block: "center" }); }, 300);
    if (xHere()) loadX();
    // A finished brief or handover job: refresh the lists so the new brief appears
    let lastDone = "";
    setInterval(() => { const jState = getJState(); if (!jState) return; const j = (jState.jobs || []).find((x) => ["meeting-brief", "handover"].includes(x.type) && x.ended); if (j && j.id !== lastDone) { if (lastDone) loadX(); lastDone = j.id; } }, 3000);
  }
  return { X, briefLinks, xOn, loadX, dShort, fuRow, stepRow };
});
