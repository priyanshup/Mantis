  // ---- Jobs: buttons that run work in the background (MANTIS-IMP-034/035), through tools/serve.py ----
  // Any element with data-job="<type>" (and optional data-arg) starts that job. A small glass panel in
  // the corner shows it running, then the result for a few seconds; "needs you" results stay until closed.
  // The page reloads by itself when the job's rebuild lands, so the panel re-opens from the server's state.
  const jobsOn = location.protocol.startsWith("http") && window.fetch;
  const jBase = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
  const SEEN = "mantis-jobs-seen";
  let jPoll = null, jState = null;
  const seen = () => { try { return JSON.parse(sessionStorage.getItem(SEEN) || "[]"); } catch (e) { return []; } };
  const markSeen = (id) => { try { sessionStorage.setItem(SEEN, JSON.stringify([...seen(), id].slice(-30))); } catch (e) {} };
  function hud() {
    let h = $("#jobhud");
    if (!h) { h = document.createElement("div"); h.id = "jobhud"; h.className = "nocopy"; h.setAttribute("role", "status"); h.setAttribute("aria-live", "polite"); document.body.appendChild(h); }
    return h;
  }
  const since = (iso) => { const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000)); return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`; };
  function showJobs(st) {
    jState = st;
    const h = hud(), active = st.active || [];
    $$("[data-job]").forEach((b) => {   // a button whose job is waiting or running is busy
      const busy = active.some((j) => j.type === b.dataset.job && (j.arg || "") === (b.dataset.arg || ""));
      b.disabled = busy; b.classList.toggle("busy", busy);
    });
    paintInbox(st);
    if (active.length) {
      const j = active[0], more = active.length - 1;
      h.className = "nocopy show run";
      h.innerHTML = `<span class="jh-spin" aria-hidden="true"></span><div class="jh-t"><b>${esc(j.label)}</b><span>${j.state === "queued" ? "Waiting to start" : "Working… " + since(j.started || j.created)}${more ? ` · ${more} more waiting` : ""}</span></div>`;
      return true;
    }
    const fresh = (st.jobs || []).find((j) => j.ended && !seen().includes(j.id) && Date.now() - new Date(j.ended).getTime() < 5 * 60 * 1000 && mine().includes(j.id));
    if (fresh) {
      const needs = (fresh.needs_you || []).length, ok = fresh.state === "done";
      const first = (fresh.summary || "").split("\n").find((l) => l.trim()) || "";
      h.className = `nocopy show ${ok ? "ok" : needs ? "needs" : "bad"}`;
      h.innerHTML = `<span class="jh-ico" aria-hidden="true">${ok ? "✓" : needs ? "!" : "×"}</span><div class="jh-t"><b>${esc(fresh.label)} · ${ok ? "done" : needs ? `needs you (${needs})` : "stopped"}</b><span>${esc(first.replace(/^[-*•]\s*/, ""))}</span>` +
        `<a href="${jBase}${fresh.type === "pull" ? "index.html#pull-box" : "sources.html#jobs"}">${fresh.type === "pull" ? "See the brief" : "Details"}</a></div><button type="button" class="jh-x" aria-label="Close">✕</button>`;
      $(".jh-x", h).addEventListener("click", () => { markSeen(fresh.id); h.className = "nocopy"; });
      if (ok) setTimeout(() => { markSeen(fresh.id); h.classList.remove("show"); }, 6500);
      return false;
    }
    h.className = "nocopy";
    return false;
  }
  const MINE = "mantis-jobs-mine";   // jobs started from this browser, so another tab's result is not shown twice
  const mine = () => { try { return JSON.parse(localStorage.getItem(MINE) || "[]"); } catch (e) { return []; } };
  const addMine = (id) => { try { localStorage.setItem(MINE, JSON.stringify([...mine(), id].slice(-30))); } catch (e) {} };
  async function pollJobs() {
    try {
      const st = await (await fetch(jBase + "api/jobs", { cache: "no-store" })).json();
      const running = showJobs(st);
      clearTimeout(jPoll);
      if (running) jPoll = setTimeout(pollJobs, 2500);
    } catch (e) { /* server not running: the buttons say so when pressed */ }
  }
  async function startJob(type, arg, label) {
    if (!jobsOn) { toast("Open Mantis from http://localhost:8000 to use this button."); return; }
    try {
      const r = await fetch(jBase + "api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type, arg: arg || "" }) });
      const j = await r.json();
      if (!r.ok) { toast(j.error || "Could not start that."); return; }
      addMine(j.job.id); showJobs(j); pollJobs();
    } catch (e) { toast("The Mantis server isn't running. Start it with Open Mantis.cmd."); }
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-job]");
    if (!b || b.disabled) return;
    e.preventDefault();
    if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
    const src = b.dataset.argFrom ? $(b.dataset.argFrom) : null;
    if (src && !src.value.trim()) { src.focus(); return; }   // nothing typed yet (the Ask box): do not start an empty job
    startJob(b.dataset.job, b.dataset.arg || (src ? src.value.trim() : ""), b.textContent.trim());
    if (src && src.tagName === "INPUT") src.value = "";
  });
  document.addEventListener("keydown", (e) => {   // Enter in the Ask box asks
    if (e.key === "Enter" && e.target.id === "ask-q") { e.preventDefault(); const b = $("#ask-go"); if (b) b.click(); }
  });
  // Questions: the answers you submitted wait for the next pull; Sources: the job list
  function paintInbox(st) {
    $$(".answers-strip").forEach((s) => { s.hidden = !(st.inbox || {}).answers; });
    const jl = $("#job-list");
    if (jl) {
      const icon = { done: "✓", "needs-you": "!", failed: "×", running: "…", queued: "…" };
      const name = { done: "Done", "needs-you": "Needs you", failed: "Stopped", running: "Running", queued: "Waiting" };
      // Real usage per Claude job (IMP-056): tokens and the list-price value; a subscription is not billed per token
      const tok = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "k" : String(n);
      const total = (u) => u ? u.input + u.output + u.cache_read + u.cache_write : 0;
      const use = (j) => j.usage ? ` · ${tok(total(j.usage))} tokens · $${j.usage.cost_usd.toFixed(2)}` : "";
      const useBody = (u) => u ? `<p class="muted small jr-use">${u.turns} turns · ${tok(u.cache_read)} re-read from cache · ${tok(u.cache_write + u.input)} new input · ${tok(u.output)} written · ` +
        `${Math.round(u.seconds / 60) || "<1"} min${u.model ? " · " + esc(u.model) : ""} · $${u.cost_usd.toFixed(2)} at list price</p>` : "";
      jl.innerHTML = (st.jobs || []).map((j) => `<details class="job-row jr-${j.state}"><summary><span class="jr-ico">${icon[j.state] || ""}</span><b>${esc(j.label)}</b>` +
        `<span class="muted small">${name[j.state] || j.state} · ${new Date(j.created).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}${j.kind === "claude" ? " · used Claude" + use(j) : " · free"}</span></summary>` +
        `<div class="jr-body">${esc(j.summary || "").replace(/\n/g, "<br>")}${(j.needs_you || []).length ? `<p><b>Needs you:</b></p><ul>${j.needs_you.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}${useBody(j.usage)}</div></details>`).join("") ||
        '<p class="empty">No jobs yet. Buttons across the site start them.</p>';
      const week = (st.jobs || []).filter((j) => j.usage && Date.now() - new Date(j.created) < 7 * 864e5);
      const wk = week.length ? ` · last 7 days: ${week.length} measured job${week.length === 1 ? "" : "s"}, ${tok(week.reduce((s, j) => s + total(j.usage), 0))} tokens, $${week.reduce((s, j) => s + j.usage.cost_usd, 0).toFixed(2)} at list price` : "";
      const q = $("#job-quota"); if (q) q.textContent = `${st.claude_today} of ${st.cap} Claude jobs used today${wk}${st.agent ? "" : " · Claude Code not found on this machine"}`;
    }
  }
  if (jobsOn) pollJobs();

  // ---- Confluence sync (MANTIS-IMP-019): copy only the sections that changed; remember what is in Confluence ----
  document.addEventListener("click", async (e) => {
    const cf = e.target.closest(".copy-field");   // Jira fields (IMP-045): Summary as text, the others formatted
    if (cf) {
      e.preventDefault(); e.stopPropagation();
      const src = $(`.jf-src[data-f="${CSS.escape(cf.dataset.f)}"]`, cf.closest(".jira"));
      if (cf.dataset.f === "Summary") copyText(src.textContent.trim()); else copyHtml(src);
      return;
    }
    const cs = e.target.closest(".copy-sec");
    if (cs) { e.preventDefault(); e.stopPropagation(); copyHtml($(".sync-body", cs.closest(".sync-sec"))); return; }
    const pb = e.target.closest("[data-publish]");
    if (!pb) return;
    e.preventDefault(); e.stopPropagation();
    if (!jobsOn) { toast("Open Mantis from http://localhost:8000 to use this."); return; }
    try {
      const r = await fetch(jBase + "api/published", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: pb.dataset.publish }) });
      const j = await r.json();
      const to = pb.dataset.to || "Confluence";
      toast(r.ok ? `Remembered as the version in ${to}. Next time only changed ${to === "Jira" ? "fields" : "sections"} show.` : (j.error || "That didn't work."));
    } catch (err) { toast("The Mantis server isn't running."); }
  });

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
  const whoOptions = (sel) => {
    const d = X.d, opts = [...(d.meetings || []).map((m) => [m.name, `Meeting · ${m.name}`]), ...(d.people || []).map((p) => [p.name, p.name])];
    return opts.map(([v, l]) => `<option value="${esc(v)}"${v === sel ? " selected" : ""}>${esc(l)}</option>`).join("");
  };
  const peopleList = () => `<datalist id="pp-names">${(X.d.people || []).map((p) => `<option value="${esc(p.name)}">`).join("")}</datalist>`;
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
    if (aw) {
      const a = d.away;
      aw.hidden = false;
      if (a) {
        const before = d.before_away || [], cover = (a.cover || [])[0] || "";
        aw.innerHTML = `<div class="sc-h"><h2><span class="away-ico" aria-hidden="true"></span>Away ${dShort(a.start)} – ${dShort(a.end)}</h2><button type="button" class="mini icon" data-away-rm="${a.id}" title="Remove this away period" aria-label="Remove">✕</button></div>` +
          `<p class="muted small">${a.cover.length ? esc(a.cover.join(", ")) + " covers" : "Nobody covering yet"}</p>` +
          (before.length ? `<p class="away-lbl">Before you go</p><ul class="away-list">${before.map((x) => `<li>${esc(x.title)}${x.due ? ` <span class="muted small">· due ${dShort(x.due)}</span>` : ""}</li>`).join("")}</ul>` : "") +
          `<div class="mb-row"><select id="ho-who" class="sel sel-sm" aria-label="Handover for">${(d.people || []).map((p) => `<option${p.name === cover ? " selected" : ""}>${esc(p.name)}</option>`).join("")}</select>` +
          `<button type="button" class="btn job ai" data-job="handover" data-arg-from="#ho-who" title="Uses Claude, on your normal quota">Handover</button></div>` +
          (briefLinks("", "handover") ? `<div class="chips sc-chips">${briefLinks("", "handover")}</div>` : "");
      } else {
        aw.innerHTML = `<details class="away-plan"><summary><span class="away-ico" aria-hidden="true"></span>Plan time away</summary><p class="muted small">Mantis lists what falls inside it, nudges you before you go and writes a handover for whoever covers.</p>` +
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
    // Today, side column: follow-ups, then Ask
    const tp = $("#t-people");
    if (tp) {
      const g = d.followups || {}, persons = Object.keys(g).sort((a, b) => (g[b].items.length - g[a].items.length) || a.localeCompare(b));
      const nFu = persons.reduce((n, p) => n + g[p].items.length + g[p].steps.length, 0);
      const fus = persons.map((p) => `<details class="fu-person"><summary><b>${esc(p)}</b><span class="fu-count">${g[p].items.length + g[p].steps.length}</span></summary>` +
        `<ul class="fu-list">${g[p].items.map(fuRow).join("")}${g[p].steps.map(stepRow).join("")}</ul></details>`).join("") || '<p class="muted small">Nothing open with anyone.</p>';
      const addFu = `<details class="fu-new"><summary>+ Add a follow-up</summary><form class="fu-add" id="fu-add"><input name="person" list="pp-names" placeholder="Person" required aria-label="Person"><input name="topic" placeholder="What to raise or chase" required aria-label="Topic">` +
        `<select name="kind" class="sel sel-sm" aria-label="Kind"><option value="raise">Raise with them</option><option value="wait">Waiting on them</option></select><button class="btn-line" type="submit">Add</button>${peopleList()}</form></details>`;
      const answers = briefLinks("", "answer");   // MANTIS-IMP-081: a question answered from the sources, with the passages it rests on
      const ask = `<section class="side-card" id="ask"><div class="sc-h"><h2>Ask Mantis</h2></div>` +
        `<div class="mb-row"><input id="ask-q" class="ask-q" type="text" placeholder="What do the sources say about…" aria-label="Your question" autocomplete="off">` +
        `<button type="button" id="ask-go" class="btn job ai" data-job="ask" data-arg-from="#ask-q" title="Uses Claude, on your normal quota">Ask</button></div>` +
        (answers ? `<div class="chips sc-chips">${answers}</div>` : `<p class="muted small sc-hint">Answers come from your sources, each point with the passage it rests on.</p>`) +
        `<button type="button" class="linkish small job ai" data-job="ask-deep" data-arg-from="#ask-q" title="A wider, slower search (a few minutes, many more tokens): when a quick answer says its passages were not enough">Dig deeper</button></section>`;
      tp.innerHTML = `<section class="side-card" id="followups"><div class="sc-h"><h2>Follow-ups</h2><span class="sc-n">${nFu || ""}</span></div>${fus}${addFu}</section>` + ask;
    }
    // Meetings page: add a regular meeting (the list itself is drawn by paintDay)
    const pm = $("#pp-meetings");
    if (pm && !$("#meet-add", pm)) {
      pm.innerHTML = `<form class="fu-add meet-form" id="meet-add"><label>Name <input name="name" placeholder="e.g. Sam 1-1" required></label>` +
        `<label>Day <select name="day" class="sel sel-sm">${["Mon", "Tue", "Wed", "Thu", "Fri"].map((x) => `<option>${x}</option>`).join("")}</select></label>` +
        `<label>Time <input name="time" type="time"></label><label>How often <select name="every" class="sel sel-sm"><option value="1">Weekly</option><option value="2">Every 2 weeks</option></select></label>` +
        `<label class="wide">With <input name="attendees" list="pp-names" placeholder="Names, comma-separated"></label><button class="btn" type="submit">Add meeting</button>${peopleList()}</form>`;
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
      if (f.id === "meet-add") { e.preventDefault(); xPost("api/schedule", { action: "add-meeting", name: v("name"), day: v("day"), time: v("time"), attendees: v("attendees"), every: v("every") }, "Meeting added."); }
      if (f.id === "away-form") { e.preventDefault(); xPost("api/schedule", { action: "add-away", start: v("start"), end: v("end"), cover: v("cover") }, "Away period saved."); }
    });
    const pf = $("#pp-filter");
    if (pf) pf.addEventListener("input", () => { const q = pf.value.toLowerCase(); $$(".person").forEach((c) => { c.hidden = q && !c.textContent.toLowerCase().includes(q); }); });
    if (location.hash && !location.hash.includes("=")) setTimeout(() => { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView({ block: "center" }); }, 300);
    if (xHere()) loadX();
    // A finished brief or handover job: refresh the lists so the new brief appears
    let lastDone = "";
    setInterval(() => { if (!jState) return; const j = (jState.jobs || []).find((x) => ["meeting-brief", "handover"].includes(x.type) && x.ended); if (j && j.id !== lastDone) { if (lastDone) loadX(); lastDone = j.id; } }, 3000);
  }

