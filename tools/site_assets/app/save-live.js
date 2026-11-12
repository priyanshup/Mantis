/* post.js (2026-11-11): after all of the mock's scripts. Saves what you change through the live APIs, and sends People, Library and
   the theme to where they live. */
(function () {
  const L = window.__LIVE || {};
  const jsonPost = (u, b) => fetch(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) })
    .then(async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(r.status === 409 ? "Your list changed in another tab. Reload to see it." : (j.error || "That did not work.")); return j; });
  const uid = () => Math.random().toString(36).slice(2, 12);

  // ---- header ----
    $("#b-lib").onclick = () => { location.href = "library.html"; };
  $("#b-theme").onclick = () => {
    const r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches, next = dark ? "light" : "dark";
    r.dataset.theme = next; try { localStorage.setItem("mantis-theme", next); } catch (e) {}
  };
  window.updCd = function () {
    const el = $("#cd"); if (!el || !LV.nextAt) return;
    const m = Math.max(0, Math.round((LV.nextAt - new Date()) / 60000)), h = Math.floor(m / 60), d = Math.floor(h / 24);
    el.textContent = `${LV.nextWhen} · in ${d ? d + " d " : ""}${h % 24 ? (h % 24) + " h " : ""}${m % 60} min`;
  };
  updCd();

  // ---- tasks: every change is written back to the live list, as a whole, a moment after you stop ----
  function desired() {
    const T = JSON.parse(JSON.stringify(LV.base)), by = {}; T.tasks.forEach((t) => (by[t.id] = t)); T.dismissed = T.dismissed || []; T.groups = T.groups || [];
    const today = REAL.today, tmr = addDays(1);
    const gid = (name) => { if (!name || name === "Other tasks") return ""; let g = T.groups.find((x) => x.name === name); if (!g) { g = { id: "g-" + uid(), name, card: "", pin: null, collapsed: false }; T.groups.push(g); } return g.id; };
    LV.ids.forEach((id, k) => {
      const t = by[id]; if (!t) return; const e = ST.edits[k] || {};
      if (ST.carryKept && t.day && t.day < today) { t.day = today; t.remind_on = ""; }
      if (e.t !== undefined) t.title = e.t;
      if (e.p !== undefined) t.priority = e.p === "none" ? "" : e.p;
      if (e.due !== undefined && !e.snz) t.due = e.due || "";
      if (e.g !== undefined) { t.group = gid(e.g); t.pin = null; }
      if (e.est !== undefined) t.estimate = +e.est || 0;
      if (e.rem !== undefined) t.remind_on = e.rem || "";
      if (e.ask !== undefined) t.contact = e.ask || "";
      if (e.n !== undefined) { const old = (t.comments || []).map((c) => c.text).join(" ").slice(0, 420); if (e.n !== old && e.n.trim()) (t.comments = t.comments || []).push({ at: today, text: e.n.trim() }); }
      if (e.snz) { t.day = tmr; t.remind_on = tmr; t.pin = null; }
      if (e.del) { t.was = t.status; t.status = "deleted"; t.deleted_at = today; t.pin = null; }
      if (ST.done.has(k) && !e.del) { t.status = "done"; t.done_at = today; t.pin = null; }
    });
    const order0 = Math.min(0, ...T.tasks.map((t) => t.order || 0)) - 1; let n = 0;
    const mk = (title, p, due, gname, ask, src) => ({ id: uid(), title, status: "todo", priority: p === "none" ? "" : (p || ""), estimate: 0, day: today, due: due || "", remind_on: "", contact: ask || "", created: today, done_at: "", order: order0 - n++, source: src, deleted_at: "", was: "", group: gid(gname), pin: null, comments: [] });
    ST.newTasks.forEach((x) => { const e = ST.edits[x.k] || {}; if (e.del) return; const f = Object.assign({}, x, e), t = mk(f.t, f.p, f.due, f.g, f.ask, "Added by you"); if (ST.done.has(x.k)) { t.status = "done"; t.done_at = today; } T.tasks.push(t); });
    ST.added.forEach((a) => { const e = ST.edits[a.k] || {}; if (e.del) return; const f = Object.assign({}, a, e), t = mk(f.t, f.p || "high", "", f.g, "", "Mantis suggestion"); if (ST.done.has(a.k)) { t.status = "done"; t.done_at = today; } T.tasks.push(t); });
    const dismiss = (s) => { if (s && s.id && !T.dismissed.includes(s.id)) T.dismissed.push(s.id); };
    ST.added.forEach((a) => dismiss(EXTRA.sugg[a.k - 900])); ST.gone.forEach((g) => dismiss(EXTRA.sugg[+String(g).slice(1)]));
    return T;
  }
  const signature = () => JSON.stringify([[...ST.done], ST.edits, ST.newTasks, ST.added, [...ST.gone], ST.carryKept]);
  let sig = signature();
  async function save() {
    const T = desired();
    try { const j = await jsonPost("api/tasks", { rev: LV.rev, tasks: T.tasks, groups: T.groups, dismissed: T.dismissed }); LV.rev = j.rev; }
    catch (e) { toast("Could not save your tasks. " + e.message); }
  }
  if (L.served) setInterval(() => { const s = signature(); if (s !== sig) { sig = s; save(); } }, 1200);

  // ---- the pull, the inbox, takeaways, filters, answers, Growth ----
  function livePull() {
    if (ST.pulling) return; ST.pulling = true; $(".top").classList.add("run");
    const btns = $$("[data-pull]"), old = btns.map((b) => b.textContent); btns.forEach((b) => { if (!b.children.length) b.textContent = "Pulling…"; });
    const before = ((L.brief || {}).last || {}).at, t0 = Date.now();
    jsonPost("api/jobs", { type: "pull", arg: "" }).then(() => {
      toast("Pull started. The page reloads when it is done.");
      const poll = async () => {
        const j = await fetch("api/pull-brief", { cache: "no-store" }).then((r) => r.json()).catch(() => null);
        if (j && j.last && j.last.at !== before) return location.reload();
        if (Date.now() - t0 > 600000) throw new Error("The pull is taking long. Reload when it ends.");
        setTimeout(() => poll().catch(fail), 3000);
      };
      poll().catch(fail);
    }).catch(fail);
    function fail(e) { ST.pulling = false; $(".top").classList.remove("run"); btns.forEach((b, i) => { if (b.isConnected && !b.children.length) b.textContent = old[i]; }); toast(e.message); }
  }
  document.addEventListener("click", (e) => {
    const t = e.target; let b;
    if (b = t.closest("[data-pull]")) { e.stopImmediatePropagation(); e.preventDefault(); livePull(); return; }
    if (b = t.closest("[data-add]")) {
      const text = ($("#ctext") || {}).value || "", name = (($("#ctitle") || {}).value || "").trim();
      if (text.trim()) jsonPost("api/inbox", { name: (name || "notes") + ".md", text }).then(() => { LV.inboxN++; }).catch((er) => toast(er.message)); return;
    }
    if (b = t.closest("[data-savetake]")) {
      const box = b.closest("#take"), text = (box.querySelector("textarea") || {}).value || "", name = (box.querySelector("input") || {}).value || "notes", meet = (($("#mdet h2") || {}).textContent || "");
      if (text.trim()) jsonPost("api/inbox", { name: name + ".md", text, meeting: meet }).catch((er) => toast(er.message)); return;
    }
    if (b = t.closest(".sw[data-fid]")) { jsonPost("api/filters", { action: "set", id: b.dataset.fid, active: !b.classList.contains("on") }).catch((er) => toast(er.message)); return; }
  }, true);
  document.addEventListener("click", (e) => {
    const b = e.target.closest && e.target.closest("[data-qsave]"); if (!b) return;
    const i = +b.dataset.qsave, a = ST.ans[i];
    if (a && a !== "Sent earlier" && LV.qIds[i]) jsonPost("api/answers", { answers: [{ id: LV.qIds[i], topic: QALL[i].q.slice(0, 300), verdict: "answers", answer: a, who: "" }] }).catch((er) => toast(er.message));
  });
  if (!L.served) $("#main").insertAdjacentHTML("afterbegin", '<p class="u-p-12-0 zero">Open Mantis at http://localhost:8000 to see and save your tasks.</p>');
})();

/* ---- People: an overlay with a short card per person; the page is one click further ---- */
(function () {
  const L = window.__LIVE || {};
  const capped = (label, items, render, n = 3) => {
    if (!items.length) return "";
    const rest = items.slice(n);
    return `<div class="pc-s"><div class="cap muted">${label} <span class="mono">${items.length}</span></div><ul class="rows">${items.slice(0, n).map(render).join("")}</ul>` +
      (rest.length ? `<div class="acc more-acc"><div class="in"><ul class="rows">${rest.map(render).join("")}</ul></div></div><button class="more" data-more data-t="${rest.length} more">${rest.length} more</button>` : "") + "</div>";
  };
  const peopleList = (q = "") => {
    const ql = q.trim().toLowerCase(), rows = PEOPLE.filter((p) => !ql || p.name.toLowerCase().includes(ql) || String(p.role).toLowerCase().includes(ql));
    return rows.slice(0, 40).map((p, i) => `<li data-pp="${esc(p.name)}" class="${i === 0 && ql ? "sel" : ""}"><span class="t">${esc(p.name)}<small>${esc(p.role)}</small></span>${p.waiting ? `<span class="mono muted" title="Things you are waiting on">${p.waiting}</span>` : ""}</li>`).join("") || '<li><span class="t muted">No one found</span></li>';
  };
  const peopleBody = () => `<input class="psearch" id="pq" placeholder="Find a person" autocomplete="off" aria-label="Find a person"><ul class="rows plist" id="pl">${peopleList()}</ul><a class="more" href="people.html">Open the People page</a>`;
  function openPeople() { drawer("People", peopleBody()); setTimeout(() => { const i = $("#pq"); if (i) i.focus(); }, 60); }
  function showPerson(name) {
    const P = ((L.extra || {}).people || []).find((p) => p.name === name) || {};
    const meets = MEET.filter((m) => (m.w || []).includes(name)), wait = (WANT[name] || { items: [] }).items, can = QALL.filter((q) => q.who === name).map((q) => q.q);
    $("#dbody").innerHTML = `<button class="link back" data-pback>← All people</button><h2 class="u-m-10-0-2">${esc(name)}</h2><p class="muted">${esc([P.role, P.team].filter(Boolean).join(" · "))}</p>` +
      capped("Meets you", meets, (m) => `<li><span class="u-w-78 when">${m.d} ${m.t}</span><span class="t">${esc(m.n)}</span></li>`) +
      capped("You are waiting on them for", wait, (t) => `<li><span class="t">${esc(t)}</span></li>`) +
      capped("Can answer", can, (t) => `<li><span class="t">${esc(t)}</span></li>`) +
      `<a class="more" href="people.html${P.slug ? "#" + esc(P.slug) : ""}">Open ${esc(name.split(" ")[0])} on the People page</a>`;
  }
  $("#b-people").onclick = openPeople;
  document.addEventListener("input", (e) => { if (e.target.id === "pq") $("#pl").innerHTML = peopleList(e.target.value); });
  document.addEventListener("keydown", (e) => { if (e.target.id === "pq" && e.key === "Enter") { const f = $("#pl li[data-pp]"); if (f) showPerson(f.dataset.pp); } });
  document.addEventListener("click", (e) => {
    const p = e.target.closest("[data-pp]"); if (p) return showPerson(p.dataset.pp);
    if (e.target.closest("[data-pback]")) { $("#dbody").innerHTML = peopleBody(); const i = $("#pq"); if (i) i.focus(); }
    const f = e.target.closest("[data-fold]"); if (f) { const fold = f.closest(".card").querySelector(".fold"), open = fold.classList.toggle("open"); f.textContent = open ? "Collapse" : "Expand"; }
  });

  // ---- the menu on small screens ----
  const menu = $("#menu"), burger = $("#b-menu");
  const items = () => TABS.map((t) => `<a href="#${t[0]}" class="${(location.hash.slice(1) || "today") === t[0] ? "on" : ""}">${t[1]}${t[2] ? `<span class="mono muted">${t[2]}</span>` : ""}</a>`).join("") + '<button type="button" data-m-people>People</button><a href="library.html">Library</a><button type="button" data-m-keys>Keyboard shortcuts</button>';
  const closeMenu = () => { menu.hidden = true; burger.setAttribute("aria-expanded", "false"); };
  burger.onclick = () => { if (menu.hidden) { menu.innerHTML = items(); menu.hidden = false; burger.setAttribute("aria-expanded", "true"); } else closeMenu(); };
  menu.addEventListener("click", (e) => { if (e.target.closest("[data-m-people]")) { closeMenu(); openPeople(); } else if (e.target.closest("[data-m-keys]")) { closeMenu(); showKeys(); } else if (e.target.closest("a")) closeMenu(); });
  document.addEventListener("click", (e) => { if (!menu.hidden && !e.target.closest("#menu,#b-menu")) closeMenu(); });
  addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); }); addEventListener("hashchange", closeMenu);

  // ---- the meetings strip keeps the chosen meeting in view on a small screen ----

  // ---- one quiet hint about the shortcuts: the second visit, once ----
  try {
    const n = (+localStorage.getItem("mantis-visits") || 0) + 1; localStorage.setItem("mantis-visits", n);
    if (n >= 2 && !localStorage.getItem("mantis-tip-keys")) setTimeout(() => { toast("Tip: press ? to see the keyboard shortcuts."); localStorage.setItem("mantis-tip-keys", "1"); }, 20000);
  } catch (e) {}
})();

/* ---- Your plan: grouping on or off ---- */
document.addEventListener("click", (e) => {
  if (!e.target.closest("[data-flat]")) return;
  ST.flat = !ST.flat; try { localStorage.setItem("mantis-flat", ST.flat ? "1" : "0"); } catch (er) {}
  ST.manual = null; ST.sort = "mantis"; ST.openName = undefined; ST.rankDirty = true; ST.expanded.clear();
  rerenderPlan(); toast(ST.flat ? "Grouping off. Each task shows its group as a label." : "Grouping on.");
});


/* ---- the add form's options stay open while one of its menus is open ---- */
const keepAddOpts = () => setTimeout(() => { const o = $("#addopts"); if (!o) return; const f = ST.addf || { man: {} }; const want = !!((($("#addin") || {}).value) || Object.keys(f.man).length || $(".pop")); if (want !== o.classList.contains("has")) o.classList.toggle("has", want); }, 0);
document.addEventListener("click", keepAddOpts); document.addEventListener("keydown", keepAddOpts);

/* ---- Old addresses: questions.html#k=<key> redirects here with the key kept; the question opens in the Questions tab ---- */
(function () {
  let h = ""; try { h = sessionStorage.getItem("mantis-deep") || ""; sessionStorage.removeItem("mantis-deep"); } catch (e) {}
  const k = (h.match(/k=([0-9a-f]+)/) || [])[1]; if (!k) return;
  const i = ((window.__LIVE || {}).stat || { questions: [] }).questions.findIndex((q) => q.k === k);
  if (i < 0) return;
  QF.who = "Anyone"; QF.feat = "All features"; QF.pri = "Any priority"; ST.qx.add(i); go("questions");
})();
