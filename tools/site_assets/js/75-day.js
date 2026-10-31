  // ---- The owner's day (MANTIS-IMP-094): Today's pull brief and meetings, the Meetings page, Sources, the People & library panel ----
  // Live data from tools/serve.py; uses X, loadX, xPost, fuRow, stepRow, briefLinks, dShort and draftData from the parts before.
  const api = async (path, body) => {
    const r = await fetch(jBase + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : { cache: "no-store" });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || "That didn't work.");
    return j;
  };
  const when = (s) => s ? new Date(s).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "";
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;

  // ---- Since last pull: the brief a pull ends with, each card's lines, noise counted, automatic closes with Undo ----
  function briefHtml(b) {
    if (!b) return '<p class="muted pb-empty">No pull yet. Press <b>Pull now</b>: Mantis reads what changed in Jira, Confluence and your inbox, and sums it up here.</p>';
    const cards = b.cards.map((c) => `<div class="pb-card"><h3>${esc(c.title)}</h3><ul>${c.lines.map((l) => `<li>${esc(l)}</li>`).join("")}</ul></div>`).join("");
    const moves = b.status_moves.length ? `<details class="pb-also"><summary>${plural(b.status_moves.length, "ticket")} moved status only</summary><ul>${b.status_moves.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></details>` : "";
    const fmt = b.formatting.length ? `<details class="pb-also"><summary>${plural(b.formatting.length, "page")} had formatting-only edits</summary><ul>${b.formatting.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></details>` : "";
    const closed = b.closed.length ? `<div class="pb-sec"><h3>Closed automatically</h3><p class="muted small">A source answered these clearly. Undo opens one again.</p>` +
      b.closed.map((x) => `<div class="row closed-row"><span class="row-t">${esc(x.topic)}</span><button type="button" class="btn-line" data-reopen="${esc(x.id)}">Undo</button></div>`).join("") + "</div>" : "";
    const needs = b.needs.length ? `<div class="pb-sec pb-needs"><h3>Needs you</h3><ul>${b.needs.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>` : "";
    const quiet = !cards && !moves && !fmt && !closed && !needs ? '<p class="muted pb-empty">Nothing new since the pull before.</p>' : "";
    return (cards ? `<div class="pb-cards">${cards}</div>` : "") + quiet + (moves || fmt ? `<div class="pb-noise">${moves}${fmt}</div>` : "") + closed + needs;
  }
  // Today's version (2026-10-31 redesign): one line per feature that really changed, the owner's followed ones
  // first, four shown; a feature whose only news is "no real change" is left out. Ticket moves live in Sources.
  const quiet = (c) => c.lines.every((l) => /^(no (real |new )?change|nothing (changed|new))/i.test(l.trim()));
  const short = (t) => t.replace(/\s*\([^)]*\)\s*$/, "").split(":")[0];
  let pullAll = false;
  function todayBrief(b, meta) {
    if (!b) return { html: '<p class="muted">No pull yet. Press <b>Pull</b> at the top: Mantis reads what changed in Jira, Confluence and your inbox, and sums it up here.</p>', more: 0 };
    const rank = (s) => { const i = meta.rank.indexOf(s); return i < 0 ? 999 : i; };
    const cards = b.cards.filter((c) => !quiet(c)).sort((x, y) => rank(x.slug) - rank(y.slug));
    const row = (c) => `<details class="pb-row"><summary><span class="pm" aria-hidden="true"></span><span class="pb-t">${esc(short(c.title))}</span><span class="pb-s">${esc(c.lines[0])}</span></summary>` +
      `<div class="pb-d">${c.lines.length > 1 ? `<ul>${c.lines.slice(1).map((l) => `<li>${esc(l)}</li>`).join("")}</ul>` : ""}${meta.href[c.slug] ? `<a href="${jBase}${meta.href[c.slug]}">Open the card</a>` : ""}</div></details>`;
    const needs = b.needs.map((x) => `<div class="pb-row pb-needs"><span class="pm" aria-hidden="true">!</span><span class="pb-s">${esc(x)}</span></div>`).join("");
    const closed = b.closed.length ? `<a class="pb-row pb-closed" href="${jBase}questions.html#closed"><span class="pm" aria-hidden="true">✓</span><span class="pb-s">${plural(b.closed.length, "question")} closed automatically by a new source</span></a>` : "";
    const shown = pullAll ? cards : cards.slice(0, 4);
    const html = needs + shown.map(row).join("") + closed || '<p class="muted">Nothing new since the pull before.</p>';
    return { html: `<div class="rows">${html}</div>`, more: Math.max(0, cards.length - 4) };
  }
  async function paintPull() {
    const pb = $("#pull-body"), ps = $("#pn-state"), ph = $("#pull-history"), pa = $("#pull-ago");
    let j;
    try { j = await api("api/pull-brief"); } catch (e) { if (pb) pb.innerHTML = '<p class="muted">Open Mantis from http://localhost:8000 to see the brief.</p>'; return; }
    const b = j.last, p = j.pending || {};
    const waiting = [p.jira && plural(p.jira, "Jira item"), p.confluence && plural(p.confluence, "Confluence page"), p.files && plural(p.files, "inbox file")].filter(Boolean);
    const dayOf = (s) => new Date(s).toLocaleDateString(undefined, { weekday: "long" });
    if (pa) { pa.textContent = b ? new Date(b.at).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "Never"; pa.title = b ? "Last pull " + when(b.at) : "No pull yet"; }
    if (pb) {
      const meta = JSON.parse($("#pull-box").dataset.cards || '{"href":{},"rank":[]}'), t = todayBrief(b, meta);
      $("#pull-h").textContent = b && b.since ? `Changed since ${dayOf(b.since)}` : "Since your last pull";
      pb.innerHTML = t.html + (waiting.length ? `<p class="muted small pb-wait">Waiting for the next pull: ${waiting.join(", ")}.</p>` : "");
      const pm = $("#pull-more"); pm.hidden = !t.more; pm.textContent = pullAll ? "Show fewer" : `${t.more} more`;
    }
    if (ps) ps.textContent = (b ? `Last pull ${when(b.at)}.` : "No pull yet.") + (waiting.length ? ` Waiting now: ${waiting.join(", ")}.` : " Nothing waiting in the inbox.");
    if (ph) ph.innerHTML = [b, ...(j.history || [])].filter(Boolean).map((x, i) => `<details class="hist"${i ? "" : " open"}><summary><b>${when(x.at)}</b><span class="muted small">${plural(x.cards.length, "feature")} changed</span></summary>${briefHtml(x)}</details>`).join("") ||
      '<p class="muted small">No pulls yet.</p>';
  }

  // ---- Today: meetings today, the Monday look back, Going away ----
  const agendaItem = (it) => `<li class="ag-row">${it.href ? `<a class="ag-t" href="${jBase}${it.href}">${esc(it.text)}</a>` : `<span class="ag-t">${esc(it.text)}</span>`}${it.note ? `<span class="t-meta">${esc(it.note.replace(/\s*\([^)]*\)\s*$/, ""))}</span>` : ""}` +
    (it.fu ? `<span class="fu-acts" data-fu="${esc(it.fu)}"><button type="button" class="mini" data-fa="raised" title="You brought it up; it stays open">Raised</button><button type="button" class="mini on" data-fa="done">Done</button></span>` : "") + "</li>";
  const nextLabel = (m, today) => !m.next ? "" : m.next === today ? "Today" : dShort(m.next);
  const initials = (n) => n.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const agendaN = (m) => m.agenda.reduce((n, s) => n + s.items.length + s.more, 0);
  const SECNAME = { Decide: "To decide", Ask: "To ask", Chase: "To chase", "Update them on": "To tell", "Still open": "Still open" };
  // A meeting has happened (so notes make sense) on its day, or when an earlier one has no saved notes yet
  const happened = (m, today) => {
    if (!m.next) return false;
    if (m.next === today) return true;
    const prev = new Date(m.next + "T12:00"); prev.setDate(prev.getDate() - 7 * (m.every || 1));
    return !m.last || m.last.date < prev.toISOString().slice(0, 10);
  };
  function paintDay(d) {
    const tn = $("#t-next");   // Today's side column: the next two meetings, each one line
    if (tn) {
      const ms = (d.meetings || []).filter((m) => m.next).slice(0, 2);
      tn.hidden = !ms.length;
      $("#t-next-b").innerHTML = ms.map((m) => `<a class="ri" href="${jBase}meetings.html#m-${esc(m.key)}"><span class="ri-h">${m.next === d.today ? "Today" : dShort(m.next)}${m.time ? ", " + esc(m.time) : ""}</span>` +
        `<span class="ri-v">${esc(m.name)}</span><span class="ri-s">${agendaN(m) ? plural(agendaN(m), "thing") + " to raise" : "Nothing open with them"}</span></a>`).join("");
    }
    const ml = $("#mt-list");
    if (ml) {
      const ms = d.meetings || [];
      const want = location.hash.startsWith("#m-") ? location.hash.slice(3) : "";
      const sel = ms.find((m) => m.key === want) || ms[0];
      $("#mt-nav").innerHTML = ms.map((m) => { const nd = m.next ? new Date(m.next + "T12:00") : null;
        return `<a class="mi${m === sel ? " on" : ""}" href="#m-${esc(m.key)}"${m === sel ? ' aria-current="true"' : ""}><span class="mi-day">${nd ? nd.getDate() : "–"}<small>${nd ? nd.toLocaleDateString(undefined, { weekday: "short" }) : ""}</small></span>` +
          `<span class="mi-n">${esc(m.name)}</span><span class="mi-s">${m.time ? esc(m.time) + " · " : ""}${esc((m.attendees || []).map((a) => a.split(" ")[0]).join(", "))}</span></a>`; }).join("") +
        `<button type="button" class="mi mi-add" data-add-meet><span class="mi-day">+</span><span class="mi-n">Add a regular meeting</span></button>`;
      if (!sel) { ml.innerHTML = '<p class="empty">No regular meetings yet. Add the ones you have every week: each gets an agenda that builds itself.</p>'; return; }
      const m = sel, l = m.last;
      const agenda = m.agenda.length ? m.agenda.map((s) => `<h3 class="ag-h">${esc(SECNAME[s.name] || s.name)}</h3><ul class="rows ag-rows">${s.items.map(agendaItem).join("")}</ul>`).join("")
        : `<p class="muted">Nothing open with ${esc((m.attendees || []).map((a) => a.split(" ")[0]).join(" or ") || "them")}. A quiet one.</p>`;
      const more = m.agenda.reduce((n, s) => n + s.more, 0);
      const last = !l ? "" : `<details class="meet-last"><summary>Last time, ${dShort(l.date)}</summary>` + (l.decisions.length ? `<p class="lt-h">Decided</p><ul>${l.decisions.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "") +
        (l.actions.length ? `<p class="lt-h">Actions</p><ul class="lt-acts">${l.actions.map((a) => `<li><span class="t-meta">${a.state === "done" ? "Done" : "Open"}</span><span><b>${esc(a.who)}</b>: ${esc(a.text)}</span></li>`).join("")}</ul>` : "") + "</details>";
      const lb = (X.d.briefs || []).find((b) => b.for === m.name && b.kind === "meeting");   // the latest brief only
      const brief = lb ? `<button type="button" class="linkish" data-brief="${lb.id}">Last brief, ${dShort(lb.date)}` : "";
      ml.innerHTML = `<article class="meet" id="m-${esc(m.key)}"><p class="eyebrow">${m.next ? new Date(m.next + "T12:00").toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }) : esc(m.day)}${m.time ? ", " + esc(m.time) : ""} · ${m.every > 1 ? `every ${m.every} weeks` : "weekly"}</p>` +
        `<header class="meet-h"><h2>${esc(m.name)}</h2><span class="faces">${(m.attendees || []).map((a) => `<button type="button" class="face" data-person="${esc(a)}" title="${esc(a)}">${esc(initials(a))}</button>`).join("")}</span>` +
        // Removing a meeting lives behind ⋯ (it still asks first), away from Prepare brief
        `<details class="pop pop-r meet-menu nocopy"><summary aria-label="Meeting options" title="Meeting options">⋯</summary><div class="pop-b">` +
        `<button type="button" class="linkish t-del" data-meet-rm="${m.id}" aria-label="Remove ${esc(m.name)}">Remove this meeting</button></div></details></header>` +
        (m.purpose ? `<p class="meet-purpose">${esc(m.purpose)}</p>` : "") + `<section class="agenda" aria-label="Agenda">${agenda}</section>${last}` +
        `<footer class="meet-f nocopy"><button type="button" class="btn job ai" data-job="meeting-brief" data-arg="${esc(m.name)}" title="Uses Claude, on your normal quota">Prepare brief</button>` +
        (brief ? brief + "</button>" : "") +
        (happened(m, d.today) ? `<details class="notes-drop"><summary class="linkish">Add notes</summary><div class="nd-body"><textarea rows="5" placeholder="Paste the notes or transcript" aria-label="Notes or transcript"></textarea>` +
          `<div class="mb-row"><input type="file" accept=".md,.txt,.vtt,.srt,.docx,.pdf" aria-label="Or choose a file"><button type="button" class="btn" data-notes="${esc(m.name)}">Save for the next pull</button></div></div></details>` : "") +
        (more ? `<span class="meet-more"><a href="${jBase}questions.html">${more} more in Questions</a></span>` : "") + "</footer></article>";
    }
    if (dr && !dr.hidden && dr.dataset.person) showPerson(dr.dataset.person);   // the panel's live parts follow the data
  }
  if ($("#mt-list")) {   // Meetings: the list on the left picks the agenda on the right
    window.addEventListener("hashchange", () => { if (X.d && location.hash.startsWith("#m-")) paintDay(X.d); });
    document.addEventListener("click", (e) => {
      const cancel = e.target.closest("[data-meet-cancel]");
      if (cancel) { const f = cancel.closest("form"); f.reset(); f.closest("details").open = false; return; }
      if (!e.target.closest("[data-add-meet]")) return;
      const am = $("#add-meet"); am.open = true; am.scrollIntoView({ block: "center", behavior: "smooth" }); const f = $("input", am); if (f) f.focus();
    });
  }
  const wk = $("#this-week");
  if (wk && (new Date().getDay() === 1 || location.hash === "#week")) wk.hidden = false;

  // ---- Files and notes to the inbox: Meetings (per meeting) and Sources (drop zone, paste) ----
  const TEXT = /\.(md|txt|vtt|srt|html?)$/i;
  async function sendFile(file, meeting) {
    if (file.size > 15e6) throw new Error(`${file.name} is larger than 15 MB`);
    if (TEXT.test(file.name)) return api("api/inbox", { name: file.name, text: await file.text(), meeting });
    const data = await new Promise((ok, bad) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(",")[1]); r.onerror = bad; r.readAsDataURL(file); });
    return api("api/inbox", { name: file.name, data, meeting });
  }
  async function sendAll(files, meeting) {
    let n = 0;
    for (const f of files) { try { await sendFile(f, meeting); n++; } catch (e) { toast(e.message); } }
    if (n) { toast(`${plural(n, "file")} added to the inbox. The next pull digests ${n === 1 ? "it" : "them"} first.`); paintPull(); paintInboxState(); }
  }
  document.addEventListener("click", async (e) => {
    const nb = e.target.closest("[data-notes]");
    if (nb) {
      const box = nb.closest(".nd-body"), ta = $("textarea", box), fi = $("input[type=file]", box);
      try {
        if (fi.files.length) await sendAll([...fi.files], nb.dataset.notes);
        if (ta.value.trim()) { await api("api/inbox", { name: "notes.md", text: ta.value, meeting: nb.dataset.notes }); toast("Notes saved. The next pull turns them into actions and follow-ups."); }
        else if (!fi.files.length) { ta.focus(); return; }
        ta.value = ""; fi.value = ""; nb.closest("details").open = false;
      } catch (err) { toast(err.message); }
      return;
    }
    const ro = e.target.closest("[data-reopen]");
    if (ro) {
      ro.disabled = true;
      try { await api("api/reopen", { id: ro.dataset.reopen }); toast("Reopened. It is back under To answer."); ro.closest(".closed-row").remove(); }
      catch (err) { ro.disabled = false; toast(err.message); }
    }
  });
  const drop = $("#drop");
  if (drop) {
    const fi = $("#drop-file");
    drop.addEventListener("click", () => fi.click());
    drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fi.click(); } });
    fi.addEventListener("change", () => { sendAll([...fi.files]); fi.value = ""; });
    ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, () => drop.classList.remove("over")));
    drop.addEventListener("drop", (e) => { e.preventDefault(); sendAll([...e.dataTransfer.files]); });
    $("#paste-save").addEventListener("click", async () => {
      const ta = $("#paste-text"); if (!ta.value.trim()) { ta.focus(); return; }
      try { await api("api/inbox", { name: ($("#paste-name").value.trim() || "pasted") + ".md", text: ta.value }); ta.value = ""; $("#paste-name").value = ""; toast("Added to the inbox."); paintPull(); paintInboxState(); }
      catch (err) { toast(err.message); }
    });
  }
  async function paintInboxState() {
    const s = $("#ib-state"); if (!s) return;
    try { const j = await api("api/jobs"); const n = j.inbox || {}; const parts = [n.files && plural(n.files, "file"), n.answers && plural(n.answers, "answer file"), n.edits && plural(n.edits, "page edit")].filter(Boolean);
      s.textContent = parts.length ? "Waiting: " + parts.join(", ") : "Empty"; } catch (e) {}
  }

  // ---- Sources: the filters a pull reads (label, value, active, last run, what it found), edited in place ----
  const flt = $("#flt");
  async function paintFilters(list) {
    if (!flt) return;
    try { list = list || (await api("api/filters")).filters; } catch (e) { flt.innerHTML = `<p class="muted small">${esc(e.message)}</p>`; return; }
    // One row per filter: on or off, its name, where, and what the last run found; Edit opens the query itself
    flt.innerHTML = list.map((f) => { const n = f.last_counts || {};
      const found = !f.last_run ? "Not run yet" : n.new === undefined ? "" : n.new || n.changed ? `${n.new} new · ${n.changed} changed` : "No change";
      return `<div class="flt-row${f.active ? "" : " off"}" data-id="${esc(f.id)}"><div class="flt-view"><label class="switch" title="${f.active ? "On: a pull reads it" : "Off: a pull skips it"}"><input type="checkbox" data-ft="active"${f.active ? " checked" : ""}><span aria-hidden="true"></span><span class="sr-only">Read on the next pull</span></label>` +
        `<span class="row-t">${esc(f.label)}</span><span class="t-meta flt-type">${f.type === "jira" ? "Jira" : "Confluence"}</span><span class="t-meta flt-found" title="${f.last_run ? "Last run " + esc(when(f.last_run)) : ""}">${found}</span>` +
        `<button type="button" class="linkish" data-ft="edit" aria-expanded="false">Edit</button></div>` +
        `<div class="flt-main" hidden><input class="flt-label" value="${esc(f.label)}" aria-label="Label">` +
        `<textarea class="flt-value" rows="2" aria-label="${f.type === "jira" ? "JQL" : "Page link, ID or CQL"}" spellcheck="false">${esc(f.value)}</textarea>` +
        `<p class="small flt-test" hidden></p><div class="flt-acts"><button type="button" class="btn" data-ft="save" hidden>Save</button><button type="button" class="btn-line" data-ft="test">Test</button>` +
        `<button type="button" class="linkish t-del" data-ft="remove">Remove</button></div></div></div>`;
    }).join("") || '<p class="muted small">No filters yet. Add one: a pull reads only what a filter selects (Jira JQL, or a Confluence page link, ID or CQL).</p>';
  }
  if (flt) {
    paintFilters(); paintInboxState();
    flt.addEventListener("input", (e) => { const r = e.target.closest(".flt-row"); if (r && e.target.matches(".flt-label, .flt-value")) $("[data-ft=save]", r).hidden = false; });
    flt.addEventListener("change", async (e) => {
      if (!e.target.matches("[data-ft=active]")) return;
      const r = e.target.closest(".flt-row");
      try { const j = await api("api/filters", { action: "set", id: r.dataset.id, active: e.target.checked }); paintFilters(j.filters); toast(e.target.checked ? "On: the next pull reads it." : "Off: pulls skip it."); }
      catch (err) { e.target.checked = !e.target.checked; toast(err.message); }
    });
    flt.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-ft]"); if (!b || b.dataset.ft === "active") return;
      const r = b.closest(".flt-row"), id = r.dataset.id;
      if (b.dataset.ft === "edit") { const m = $(".flt-main", r); m.hidden = !m.hidden; b.setAttribute("aria-expanded", String(!m.hidden)); b.textContent = m.hidden ? "Edit" : "Close"; if (!m.hidden) $(".flt-value", r).focus(); return; }
      try {
        if (b.dataset.ft === "save") { const j = await api("api/filters", { action: "set", id, label: $(".flt-label", r).value, value: $(".flt-value", r).value }); paintFilters(j.filters); toast("Saved. A changed value starts fresh on the next pull."); }
        if (b.dataset.ft === "remove" && confirm(`Remove the filter "${$(".flt-label", r).value}"? Pulls stop reading it.`)) { const j = await api("api/filters", { action: "remove", id }); paintFilters(j.filters); toast("Filter removed."); }
        if (b.dataset.ft === "test") {
          const out = $(".flt-test", r); out.hidden = false; out.textContent = "Asking…"; b.disabled = true;
          const t = await api("api/filters", { action: "test", id }).finally(() => (b.disabled = false));
          out.textContent = `${t.count} item${t.count === 1 ? "" : "s"} now` + (t.sample.length ? `, for example: ${t.sample.slice(0, 3).join("; ")}` : "") + ".";
        }
      } catch (err) { const out = $(".flt-test", r); out.hidden = false; out.textContent = err.message; }
    });
    $("#flt-add-btn").addEventListener("click", () => {
      if ($("#flt-new")) { $("#flt-new input").focus(); return; }
      flt.insertAdjacentHTML("afterbegin", `<form class="flt-row flt-new" id="flt-new"><span class="flt-pad"></span><div class="flt-main"><div class="flt-top"><input name="label" placeholder="Label, e.g. Pricing epics" required aria-label="Label">` +
        `<select name="type" class="sel sel-sm" aria-label="Where"><option value="jira">Jira</option><option value="confluence">Confluence</option></select></div>` +
        `<textarea name="value" rows="2" required placeholder="JQL, or a Confluence page link, ID or CQL" aria-label="Value" spellcheck="false"></textarea></div>` +
        `<div class="flt-acts"><button class="btn" type="submit">Add</button><button type="button" class="mini" data-cancel>Cancel</button></div></form>`);
      $("#flt-new input").focus();
    });
    flt.addEventListener("submit", async (e) => {
      e.preventDefault(); const f = e.target;
      try { const j = await api("api/filters", { action: "add", label: f.label.value, type: f.type.value, value: f.value.value }); paintFilters(j.filters); toast("Added. The next pull reads it from the last two weeks."); }
      catch (err) { toast(err.message); }
    });
    flt.addEventListener("click", (e) => { if (e.target.closest("[data-cancel]")) $("#flt-new").remove(); });
  }
  // ---- Sources: tickets no card owns; the owner maps each Jira item (and all under it) to a card, or skips it ----
  const um = $("#unmapped");
  async function paintUnmapped(items, cards) {
    if (!um) return;
    try { if (!items) { const j = await api("api/unmapped"); items = j.items; cards = j.cards; um.dataset.cards = JSON.stringify(j.cards); } } catch (e) { return; }
    cards = cards || JSON.parse(um.dataset.cards || "[]");
    um.hidden = !items.length;
    $("#um-list").innerHTML = items.map((e) => `<div class="row um-row" data-root="${esc(e.root)}"><span class="row-t">${esc(e.root)} ${esc(e.summary)}` +
      `<span class="muted small">${esc(e.type)}${e.keys.length > 1 ? ` · ${e.keys.length} tickets under it changed` : ""}</span></span>` +
      `<select class="sel sel-sm" aria-label="Feature for ${esc(e.root)}"><option value="">Belongs to…</option>${cards.map((c) => `<option value="${esc(c.slug)}">${esc(c.title)}</option>`).join("")}</select>` +
      `<button type="button" class="mini" data-um="map">Map</button><button type="button" class="mini" data-um="skip" title="Never pull it again">Skip</button></div>`).join("");
  }
  if (um) {
    paintUnmapped();
    um.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-um]"); if (!b) return;
      const r = b.closest(".um-row"), card = b.dataset.um === "skip" ? "skip" : $("select", r).value;
      if (!card) { $("select", r).focus(); toast("Choose the feature it belongs to first."); return; }
      try { const j = await api("api/mapping", { root: r.dataset.root, card }); paintUnmapped(j.items); paintPull();
        toast(card === "skip" ? "Skipped. Pulls leave it out from now on." : "Mapped. The next pull digests it with that feature."); }
      catch (err) { toast(err.message); }
    });
  }
  const pmore = $("#pull-more"); if (pmore) pmore.addEventListener("click", () => { pullAll = !pullAll; paintPull(); });
  const hh = location.hash;
  if (["#health", "#jobs"].includes(hh) && $("#health")) { $("#health").open = true; setTimeout(() => $(hh).scrollIntoView({ block: "start" }), 100); }
  if (hh === "#history" && $("#history")) $("#history").open = true;
  document.addEventListener("click", (e) => {   // Sources' side lines open their section in place
    const o = e.target.closest("[data-open]"); if (!o) return;
    const t = document.getElementById(o.dataset.open); if (!t) return;
    e.preventDefault(); t.open = true; t.scrollIntoView({ block: "start", behavior: "smooth" });
  });
  paintPull();

  // ---- People & library: one side panel from any page. A name anywhere opens that person ----
  const dr = $("#drawer");
  let lastFocus = null, peopleCache = null, libCache = null, view = "people";
  const getJson = async (name, cache) => cache || (await (await fetch(jBase + name, { cache: "no-store" })).json());
  function openDrawer(v, person) {
    if (!dr) return;
    if (dr.hidden) lastFocus = document.activeElement;
    view = v; dr.hidden = false; document.body.classList.add("drawer-open");
    if (!$(".dr-h", dr)) {
      dr.innerHTML = `<div class="dr-h"><div class="seg" role="tablist" aria-label="Panel"><button type="button" data-dv="people" role="tab">People</button><button type="button" data-dv="library" role="tab">Library</button></div>` +
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
      if (!p) return;
      e.preventDefault(); e.stopPropagation();
      closePalette();
      openDrawer("people", p.dataset.person);
    }, true);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !dr.hidden && !document.querySelector(".modal-wrap")) closeDrawer(); });
    document.addEventListener("click", (e) => {   // a click anywhere outside the panel closes it (a name elsewhere opens that person instead)
      if (!dr.hidden && !e.composedPath().includes(dr) && !e.target.closest("[data-person], [data-dopen], .modal-wrap, #palette, #toast")) closeDrawer();
    });
  }
