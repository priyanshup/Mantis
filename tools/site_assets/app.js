// Mantis site: copy buttons, tabs, roadmap and work boards, filters, live reload. No libraries.
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = { get(k) { try { return JSON.parse(localStorage.getItem(k) || "{}"); } catch (e) { return {}; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
  const pill = (l, c) => `<span class="pill ${c}">${esc(l)}</span>`;

  // ---- Toast and copy ----
  let timer;
  function toast(msg, undo) {   // with `undo`, the toast offers an Undo button and stays a little longer
    const t = $("#toast"); t.textContent = msg; t.classList.add("show"); t.classList.toggle("has-undo", !!undo);
    if (undo) {
      const b = document.createElement("button"); b.type = "button"; b.className = "toast-undo"; b.textContent = "Undo";
      b.addEventListener("click", () => { t.classList.remove("show"); undo(); toast("Undone."); }, { once: true });
      t.appendChild(b);
    }
    clearTimeout(timer); timer = setTimeout(() => t.classList.remove("show"), undo ? 6000 : 1800);
  }
  function pasteReady(el) {
    const c = el.cloneNode(true);
    $$(".nocopy", c).forEach((n) => n.remove());
    $$(".tbl", c).forEach((w) => w.replaceWith(...w.childNodes));
    $$("table", c).forEach((t) => { t.setAttribute("border", "1"); t.style.borderCollapse = "collapse"; });
    $$("th, td", c).forEach((x) => { x.style.border = "1px solid #c1c7d0"; x.style.padding = "6px 8px"; });
    $$("section", c).forEach((s) => s.replaceWith(...s.childNodes));
    $$("[class]", c).forEach((x) => x.removeAttribute("class"));
    return c;
  }
  async function copyHtml(el) {
    const c = pasteReady(el);
    const html = c.innerHTML, text = c.innerText || c.textContent;
    try {
      await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([text], { type: "text/plain" }) })]);
    } catch (e) {
      const tmp = document.createElement("div");
      tmp.innerHTML = html; tmp.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(tmp);
      const r = document.createRange(); r.selectNodeContents(tmp);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      document.execCommand("copy"); s.removeAllRanges(); tmp.remove();
    }
    toast("Copied. Paste into Confluence or Jira.");
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); } catch (e) {
      const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove();
    }
    toast("Copied: " + (text.length > 40 ? text.slice(0, 40) + "…" : text));
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.classList.contains("copy-sec")) copyHtml(b.closest(".sec"));
    else if (b.classList.contains("copy-all")) copyHtml($(".doc", b.closest(".tab-panel")));
    else if (b.classList.contains("copy-text")) copyText(b.dataset.text);
  });

  // ---- Theme: Auto (follow the system) -> Light -> Dark, remembered per browser ----
  const tb = $("#theme");
  if (tb) {
    const ICON = { auto: "◐", light: "☀", dark: "☾" }, NAME = { auto: "auto (follows your system)", light: "light", dark: "dark" };
    const cur = () => { try { return localStorage.getItem("mantis-theme") || "auto"; } catch (e) { return "auto"; } };
    const apply = (m) => {
      if (m === "auto") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = m;
      tb.textContent = ICON[m]; tb.title = "Theme: " + NAME[m] + ". Click to change.";
    };
    apply(cur());
    tb.addEventListener("click", () => {
      const next = { auto: "light", light: "dark", dark: "auto" }[cur()];
      try { localStorage.setItem("mantis-theme", next); } catch (e) {}
      apply(next); toast("Theme: " + NAME[next]);
    });
  }

  // ---- Nav: "More" closes on an outside click or Escape ----
  const nm = $(".nav-more");
  if (nm) {
    document.addEventListener("click", (e) => { if (nm.open && !nm.contains(e.target)) nm.open = false; });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") nm.open = false; });
  }

  // ---- Header menu on small windows: one button opens the nav as a panel ----
  const mb = $(".menu-btn"), top = $(".top");
  if (mb) {
    const setMenu = (open, viaKey) => {
      top.classList.toggle("menu-open", open); mb.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && viaKey) { const first = $(".mainnav a.on") || $(".mainnav a"); if (first) first.focus(); }
    };
    mb.addEventListener("click", (e) => setMenu(!top.classList.contains("menu-open"), e.detail === 0));
    document.addEventListener("click", (e) => { if (top.classList.contains("menu-open") && !e.target.closest(".mainnav, .menu-btn")) setMenu(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && top.classList.contains("menu-open")) { setMenu(false); mb.focus(); } });
    matchMedia("(min-width: 981px)").addEventListener("change", (m) => { if (m.matches) setMenu(false); });
  }

  // ---- Home: rank My focus (drag or arrows), saved to focus.json through tools/serve.py ----
  const fl = $("#focus-list");
  if (fl) {
    const renum = () => $$(".f-row", fl).forEach((r, i) => ($(".f-rank", r).textContent = i + 1));
    let saveT = null;
    const persist = () => { renum(); clearTimeout(saveT); saveT = setTimeout(sendOrder, 500); };
    const sendOrder = async () => {
      try {
        const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "order", order: $$(".f-row", fl).map((r) => r.dataset.slug) }) });
        if (!r.ok) throw new Error();
        toast("Focus order saved.");
      } catch (e) { toast("Could not save the order. Is the site server running?"); }
    };
    fl.addEventListener("click", (e) => {
      const b = e.target.closest("[data-m]"); if (!b) return;
      const r = b.closest(".f-row"), sib = +b.dataset.m < 0 ? r.previousElementSibling : r.nextElementSibling;
      if (!sib) return;
      +b.dataset.m < 0 ? sib.before(r) : sib.after(r); persist();
    });
    let drag = null;
    fl.addEventListener("dragstart", (e) => { drag = e.target.closest(".f-row"); if (drag) drag.classList.add("dragging"); });
    fl.addEventListener("dragend", () => { if (drag) drag.classList.remove("dragging"); $$(".f-row", fl).forEach((x) => x.classList.remove("drop-above", "drop-below")); });
    fl.addEventListener("dragover", (e) => {
      const r = e.target.closest(".f-row"); if (!r || !drag || r === drag) return;
      e.preventDefault(); const above = e.clientY < r.getBoundingClientRect().top + r.offsetHeight / 2;
      $$(".f-row", fl).forEach((x) => x.classList.remove("drop-above", "drop-below")); r.classList.add(above ? "drop-above" : "drop-below");
    });
    fl.addEventListener("drop", (e) => {
      const r = e.target.closest(".f-row"); if (!r || !drag || r === drag) return;
      e.preventDefault(); const above = e.clientY < r.getBoundingClientRect().top + r.offsetHeight / 2;
      above ? r.before(drag) : r.after(drag); drag = null; persist();
    });
    const ff = $("#f-filter");
    if (ff) ff.addEventListener("input", () => { const q = ff.value.toLowerCase(); $$(".f-row", fl).forEach((r) => (r.hidden = q && !r.textContent.toLowerCase().includes(q))); });
  }

  // ---- Home ----
  const hello = $("#hello");
  if (hello) { const h = new Date().getHours(); hello.textContent = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"; }
  // ---- Topics page: My focus / On roadmap / All, plus Follow and Roadmap buttons saved via tools/serve.py ----
  const ttab = $("#ttab");
  if (ttab) {
    const saved = store.get("mantis-topics");
    let tab = saved.tab || "focus";
    const tq = $("#tq");
    const show = () => {
      const q = (tq.value || "").toLowerCase(); let n = 0;
      $$(".topic-tile").forEach((t) => {
        const arc = t.dataset.archived === "1";
        const inTab = tab === "archived" ? arc : !arc && (tab === "all" || (tab === "focus" && t.dataset.following === "1") || (tab === "roadmap" && t.dataset.roadmap === "1"));
        t.hidden = !inTab || (q && !t.textContent.toLowerCase().includes(q)); if (!t.hidden) n++;
      });
      $$("button", ttab).forEach((b) => b.classList.toggle("on", b.dataset.v === tab));
      $("#t-empty").hidden = n > 0; store.set("mantis-topics", { tab });
      drawBulk();
    };
    // Bulk actions work on the cards shown (so a filter narrows them). Each offers Undo, which survives
    // the page reload that follows the site rebuild.
    const BULK = { focus: [["unfollow", "Clear all focus"]], roadmap: [["unroadmap", "Clear roadmap"]],
      all: [["follow", "Follow all"], ["unfollow", "Unfollow all"], ["roadmap", "Add all to roadmap"], ["unroadmap", "Clear roadmap"]],
      archived: [["unarchive", "Restore all"]] };
    const INVERSE = { follow: "unfollow", unfollow: "follow", roadmap: "unroadmap", unroadmap: "roadmap", archive: "unarchive", unarchive: "archive" };
    const FIELD = (a) => /archive/.test(a) ? "archived" : /follow/.test(a) ? "following" : "roadmap";
    const bulkEl = $("#t-bulk");
    const targets = (action) => $$(".topic-tile").filter((t) => !t.hidden && (t.dataset[FIELD(action)] === "1") === /^un/.test(action));
    function drawBulk() {
      const filtered = !!(tq.value || "").trim();
      bulkEl.innerHTML = BULK[tab].map(([a, l]) => { const n = targets(a).length;
        return `<button type="button" class="mini${/^un/.test(a) ? " t-del" : ""}" data-bulk="${a}" ${n ? "" : "disabled"}>${l}${filtered ? " shown" : ""}${n ? ` · ${n}` : ""}</button>`; }).join("");
    }
    const LABEL = { following: ["☆ Follow", "★ Following"], roadmap: ["+ Roadmap", "✓ On roadmap"], archived: ["Archive", "Restore"] };
    const BTN = { following: "follow", roadmap: "roadmap", archived: "archive" };
    function setTile(tile, action) {
      const f = FIELD(action), on = !/^un/.test(action), b = $(`.act[data-a="${BTN[f]}"]`, tile);
      tile.dataset[f] = on ? "1" : "0"; b.textContent = LABEL[f][+on]; if (f !== "archived") { b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); }
      if (action === "archive") { setTile(tile, "unfollow"); setTile(tile, "unroadmap"); }   // the server does the same
    }
    async function bulk(action, slugs) {
      const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "bulk-" + action, order: slugs }) });
      if (!r.ok) throw new Error((await r.json()).error);
      slugs.forEach((s) => { const t = $(`.topic-tile[data-slug="${s}"]`); if (t) setTile(t, action); });
      show();
    }
    const undoBulk = (u) => () => bulk(u.action, u.slugs).then(() => { try { sessionStorage.removeItem("mantis-undo"); } catch (e) {} }).catch(() => toast("Could not undo: is the site server running?"));
    bulkEl.addEventListener("click", async (e) => {
      const b = e.target.closest("[data-bulk]"); if (!b) return;
      const action = b.dataset.bulk, slugs = targets(action).map((t) => t.dataset.slug); if (!slugs.length) return;
      try {
        await bulk(action, slugs);
        const msg = `${b.textContent.replace(/ · \d+$/, "")}: ${slugs.length} card${slugs.length === 1 ? "" : "s"} changed.`, u = { action: INVERSE[action], slugs, msg, until: Date.now() + 15000 };
        try { sessionStorage.setItem("mantis-undo", JSON.stringify(u)); } catch (err) {}
        toast(msg, undoBulk(u));
      } catch (err) { toast("Could not save: is the site running through tools/serve.py?"); }
    });
    try {   // a bulk change made just before the rebuild reloaded this page can still be undone
      const u = JSON.parse(sessionStorage.getItem("mantis-undo") || "null");
      if (u && u.until > Date.now()) setTimeout(() => toast(u.msg, undoBulk(u)), 300); else sessionStorage.removeItem("mantis-undo");
    } catch (e) {}
    ttab.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { tab = b.dataset.v; show(); } });
    tq.addEventListener("input", show);
    document.addEventListener("click", async (e) => {
      const b = e.target.closest(".tile-acts .act"); if (!b) return;
      const tile = b.closest(".topic-tile"), f = { follow: "following", roadmap: "roadmap", archive: "archived" }[b.dataset.a];
      const on = tile.dataset[f] === "1", action = (on ? "un" : "") + b.dataset.a;
      try {
        if (!(location.protocol.startsWith("http") && window.fetch)) throw new Error("offline");
        const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ slug: tile.dataset.slug, action }) });
        if (!r.ok) throw new Error((await r.json()).error);
        setTile(tile, action);
        const MSG = { follow: "Added to your focus.", unfollow: "Removed from your focus.", roadmap: "Added to your roadmap.", unroadmap: "Taken off your roadmap.",
          archive: "Archived. It is out of your lists; find it under Archived.", unarchive: "Restored. Follow it or add it to the roadmap again if you need it." };
        toast(MSG[action]);
        show();
      } catch (err) { toast("Could not save: is the site running through tools/serve.py?"); }
    });
    show();
  }

  // ---- Feature page: tabs, stories, topic switcher ----
  if ($(".tabs")) {
    const show = () => {
      const want = decodeURIComponent(location.hash.slice(1)) || "overview";
      const id = document.getElementById("p-" + want) ? want : "overview";
      $$(".tab-panel").forEach((p) => (p.hidden = p.id !== "p-" + id));
      $$(".tabs a").forEach((a) => a.classList.toggle("on", id === a.dataset.match || (a.dataset.match.endsWith("-") && id.startsWith(a.dataset.match))));
      $$(".story").forEach((a) => a.classList.toggle("on", a.dataset.anchor === id));
    };
    // Switching tabs keeps your place; only if the tabs have scrolled out of view does the page glide back to them.
    window.addEventListener("hashchange", () => {
      show();
      const tabs = $(".tabs"), top = tabs.getBoundingClientRect().top;
      if (top < 0) try { window.scrollTo({ top: scrollY + top - 80, behavior: "smooth" }); } catch (e) {}
    });
    show();
  }
  const sw = $("#switch");
  if (sw) sw.addEventListener("change", () => (location.href = sw.value));

  // ---- Library chips ----
  const lib = $("#f-lib");
  if (lib) lib.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", lib).forEach((x) => x.classList.toggle("on", x === b));
    $$(".lib").forEach((r) => (r.hidden = b.dataset.v !== "all" && r.dataset.kind !== b.dataset.v));
  });

  // ---- Shared board/list machinery ----
  function board(opts) {
    const { items, key, st, draw } = opts;
    const fromHash = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
    Object.assign(st, store.get(key), fromHash);
    const sync = () => {
      $$(".chips").forEach((g) => $$("button", g).forEach((b) => b.classList.toggle("on", b.dataset.v === (st[g.dataset.k] || "all"))));
      $$("#view button").forEach((b) => b.classList.toggle("on", b.dataset.v === st.view));
      $("#board").hidden = st.view !== "board"; $("#list").hidden = st.view !== "list";
      const h = new URLSearchParams(); Object.keys(st).forEach((k) => st[k] && st[k] !== "all" && !["sort", "asc"].includes(k) && h.set(k, st[k]));
      history.replaceState(null, "", "#" + h.toString());
      store.set(key, { view: st.view });
      draw();
    };
    $$(".chips").forEach((g) => g.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { st[g.dataset.k] = b.dataset.v; sync(); } }));
    $("#view").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { st.view = b.dataset.v; sync(); } });
    $("#q").value = st.q || "";
    $("#q").addEventListener("input", (e) => { st.q = e.target.value; sync(); });
    $("#list").addEventListener("click", (e) => { const t = e.target.closest("th[data-k]"); if (t) { st.asc = st.sort === t.dataset.k ? !st.asc : true; st.sort = t.dataset.k; sync(); } });
    return sync;
  }
  function table(cols, rows, st) {
    const th = (k, n) => k ? `<th data-k="${k}" class="${st.sort === k ? "sorted" + (st.asc ? " asc" : "") : ""}">${n}</th>` : `<th>${n}</th>`;
    return `<section class="panel-box"><div class="tbl"><table class="list-t"><thead><tr>${cols.map(([k, n]) => th(k, n)).join("")}</tr></thead><tbody>${rows.join("") || `<tr><td colspan="${cols.length}" class="muted">Nothing matches these filters.</td></tr>`}</tbody></table></div></section>`;
  }
  function sortBy(rows, keys, st) {
    const k = keys[st.sort] || keys.title;
    return [...rows].sort((a, b) => (k(a) < k(b) ? -1 : k(a) > k(b) ? 1 : a.title.localeCompare(b.title)) * (st.asc === false ? -1 : 1));
  }

  // ---- Roadmap ----
  const rd = $("#data");
  if (rd) {
    const { items, labels } = JSON.parse(rd.textContent);
    const cls = { none: "s-none", discovery: "s-disc", refinement: "s-ref", build: "s-build", live: "s-done" };
    const order = ["none", "discovery", "refinement", "build", "live"];
    const prio = { P1: 1, P2: 2, P3: 3 };
    const st = { q: "", status: "all", prio: "all", view: "board", sort: "prio", asc: true };
    $("#f-status").dataset.k = "status"; $("#f-prio").dataset.k = "prio";
    const pp = (p) => (p ? pill(p, "p-" + p.toLowerCase()) : "");
    const href = (i) => i.url || `features/${i.slug}.html`;
    const visible = () => {
      const q = (st.q || "").trim().toLowerCase();
      return items.filter((i) => (st.status === "all" || i.status === st.status) && (st.prio === "all" || i.priority === st.prio) &&
        (!q || (i.title + " " + i.summary).toLowerCase().includes(q)));
    };
    const facts = (i) => !i.slug ? "" : `<div class="facts"><span>${i.epics ? `Epic${i.epics > 1 ? "s" : ""} <b>${i.epics}</b>` : "No epic"}</span><span>Stories <b>${i.storiesDone}/${i.stories}</b></span>` +
      (i.open ? `<span><b>${i.open}</b> open question${i.open > 1 ? "s" : ""}</span>` : "") + (i.jira && i.jira !== "none" ? `<span>${esc(i.jira)}</span>` : "") + `</div>`;
    const tile = (i) => i.slug
      ? `<a class="tile st-${i.status || "none"}" href="${href(i)}"><h3><span>${esc(i.title)}</span>${pp(i.priority)}</h3>${i.type === "workstream" ? '<span class="tag">Platform workstream</span>' : ""}<p>${esc(i.summary)}</p>${facts(i)}</a>`
      : `<div class="tile ghost"><h3><span>${esc(i.title)}</span></h3><p>${esc(i.summary)}</p></div>`;
    const byPrio = (a, b) => (prio[a.priority] || 9) - (prio[b.priority] || 9) || a.title.localeCompare(b.title);
    const draw = () => {
      const v = visible();
      if (st.view === "board") {
        let out;
        if (st.status !== "all") {
          const xs = v.sort(byPrio);
          out = `<h2 class="section-h">${pill(labels[st.status], cls[st.status])} <span class="muted">${xs.length}</span></h2><div class="later">${xs.map(tile).join("") || '<p class="empty">Nothing here with these filters.</p>'}</div>`;
        } else {
          out = `<div class="board">` + ["discovery", "refinement", "build", "live"].map((s) => {
            const xs = v.filter((i) => i.status === s).sort(byPrio);
            return `<div class="col st-${s}"><div class="col-h">${pill(labels[s], cls[s])}<span class="n">${xs.length}</span></div>${xs.map(tile).join("") || `<p class="empty">${s === "live" ? "A topic moves here when it goes live." : "Nothing here."}</p>`}</div>`;
          }).join("") + `</div>`;
          const later = v.filter((i) => i.status === "none");
          if (later.length) out += `<h2 class="section-h">${pill(labels.none, cls.none)} <span class="muted">${later.length} on the roadmap with no detail yet</span></h2><div class="later">${later.map(tile).join("")}</div>`;
        }
        $("#board").innerHTML = out;
      } else {
        const keys = { prio: (i) => prio[i.priority] || 9, title: (i) => i.title.toLowerCase(), status: (i) => order.indexOf(i.status), epics: (i) => i.epics, stories: (i) => i.stories, open: (i) => i.open, updated: (i) => i.updated };
        $("#list").innerHTML = table([["title", "Topic"], ["prio", "Priority"], ["status", "Status"], ["epics", "Epics"], ["stories", "Stories"], ["open", "Open questions"], ["", "Jira"], ["updated", "Updated"]],
          sortBy(v, keys, st).map((i) => `<tr><td>${i.slug ? `<a href="${href(i)}">${esc(i.title)}</a>` : esc(i.title)}${i.type === "workstream" ? ' <span class="tag">Workstream</span>' : ""}</td><td>${pp(i.priority) || "–"}</td><td>${pill(labels[i.status], cls[i.status])}</td>` +
            `<td>${i.slug ? i.epics : "–"}</td><td>${i.slug ? i.storiesDone + "/" + i.stories : "–"}</td><td>${i.open || "–"}</td><td>${i.jira && i.jira !== "none" ? esc(i.jira) : "–"}</td><td class="muted">${esc(i.updated) || "–"}</td></tr>`), st);
      }
    };
    board({ items, key: "mantis-roadmap", st, draw })();
  }

  // ---- Epics & stories ----
  const wd = $("#work");
  if (wd) {
    const { items, labels } = JSON.parse(wd.textContent);
    const wcls = { draft: "w-draft", review: "w-review", "in-jira": "w-jira", done: "w-done" };
    const order = ["draft", "review", "in-jira", "done"];
    const st = { q: "", kind: "all", feature: "all", view: "board", sort: "status", asc: true };
    $("#f-kind").dataset.k = "kind";
    const sel = $("#f-feature");
    const visible = () => {
      const q = (st.q || "").trim().toLowerCase();
      const f = st.feature, inScope = (i) => f === "archived" ? i.archived : !i.archived && (f === "all" || (f === "mine" ? i.mine : i.feature === f));
      return items.filter((i) => inScope(i) && (st.kind === "all" || i.kind === st.kind) &&
        (!q || (i.title + " " + i.feature_title + " " + i.epic_title).toLowerCase().includes(q)));
    };
    const where = (i) => i.kind === "epic" ? (i.feature_title || "Generic epic") : [i.feature_title, i.epic_title ? "Epic: " + i.epic_title : "Not in an epic"].filter(Boolean).join(" · ");
    const kind = (i) => i.kind === "epic" ? '<span class="kind k-epic">◆ Epic</span>' : '<span class="kind k-story">▤ Story</span>';
    // Each card can be archived on its own; one archived only because its topic is, is restored from Topics.
    const arcBtn = (i) => i.topicArc ? "" : `<button type="button" class="tile-x nocopy" data-work="${esc(i.file)}" data-on="${i.own ? 1 : 0}" title="${i.own ? "Restore to the board" : "Archive: hide it from the board"}">${i.own ? "Restore" : "Archive"}</button>`;
    const card = (i) => `<div class="tile-wrap"><a class="tile wk-${i.kind}" href="${i.href}">${kind(i)}<h3><span>${esc(i.title)}</span></h3>${where(i) && where(i) !== i.title ? `<p>${esc(where(i))}</p>` : ""}` +
      `<div class="facts">${i.jira && i.jira !== "none" ? `<span>${esc(i.jira)}</span>` : ""}${i.updated ? `<span>${esc(i.updated)}</span>` : ""}${i.topicArc ? "<span>Topic archived</span>" : ""}</div></a>${arcBtn(i)}</div>`;
    const draw = () => {
      sel.value = st.feature;
      const v = visible();
      if (st.view === "board") {
        $("#board").innerHTML = `<div class="board">` + order.map((s) => {
          const xs = v.filter((i) => i.status === s).sort((a, b) => (a.kind === "epic" ? 0 : 1) - (b.kind === "epic" ? 0 : 1) || a.title.localeCompare(b.title));
          return `<div class="col"><div class="col-h">${pill(labels[s], wcls[s])}<span class="n">${xs.length}</span></div>${xs.map(card).join("") || '<p class="empty">Nothing here.</p>'}</div>`;
        }).join("") + `</div>` + (items.length ? "" : '<p class="empty">No epics or stories yet. Ask Mantis in VS Code to write one.</p>');
      } else {
        const keys = { title: (i) => i.title.toLowerCase(), kind: (i) => i.kind, status: (i) => order.indexOf(i.status), feature: (i) => i.feature_title, updated: (i) => i.updated };
        $("#list").innerHTML = table([["title", "Title"], ["kind", "Type"], ["status", "Status"], ["feature", "Topic and epic"], ["", "Jira"], ["updated", "Updated"]],
          sortBy(v, keys, st).map((i) => `<tr><td><a href="${i.href}">${esc(i.title)}</a></td><td>${kind(i)}</td><td>${pill(labels[i.status] || i.status, wcls[i.status] || "w-draft")}</td>` +
            `<td>${esc(where(i))}</td><td>${i.jira && i.jira !== "none" ? esc(i.jira) : "–"}</td><td class="muted">${esc(i.updated) || "–"}</td></tr>`), st);
      }
    };
    items.forEach((i) => (i.topicArc = i.archived && !i.own));   // archived because its topic is
    const sync = board({ items, key: "mantis-work", st, draw });
    async function archiveWork(file, on) {
      const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ slug: file, action: (on ? "un" : "") + "archive-work" }) });
      if (!r.ok) throw new Error((await r.json()).error);
      const i = items.find((x) => x.file === file); i.own = !on; i.archived = i.own || i.topicArc; sync();
    }
    $("#board").addEventListener("click", async (e) => {
      const b = e.target.closest(".tile-x"); if (!b) return;
      e.preventDefault();
      const file = b.dataset.work, on = b.dataset.on === "1";
      try {
        await archiveWork(file, on);
        toast(on ? "Restored to the board." : "Archived. Find it under Archived.", () => archiveWork(file, !on).catch(() => toast("Could not undo: is the site server running?")));
      } catch (err) { toast("Could not save: is the site running through tools/serve.py?"); }
    });
    sel.addEventListener("change", () => { st.feature = sel.value; sync(); });
    sync();
  }

  // ---- Knowledge graph ----
  const gd = $("#graph");
  if (gd) {
    const all = JSON.parse(gd.textContent);
    const by = Object.fromEntries(all.map((e) => [e.n, e]));
    const st = { q: "", type: "all", cur: decodeURIComponent((location.hash.match(/e=([^&]+)/) || [])[1] || "") };
    if (!by[st.cur]) st.cur = all[0] && all[0].n;
    const key = (s) => s.toLowerCase().replace(/[^0-9a-z]/g, "");
    const typePill = (t) => `<span class="pill t-${t}">${esc(t)}</span>`;

    function list() {
      const q = key(st.q);
      const xs = all.filter((e) => (st.type === "all" || e.t === st.type) && (!q || key(e.n).includes(q) || e.a.some((a) => key(a).includes(q))));
      $("#ent-list").innerHTML = xs.slice(0, 200).map((e) =>
        `<a class="row ent-row${e.n === st.cur ? " on" : ""}" href="#e=${encodeURIComponent(e.n)}"><span class="dot t-${e.t}"></span><span class="row-t">${esc(e.n)}</span><span class="muted small">${e.d}</span></a>`).join("")
        || '<p class="empty">No entity matches.</p>';
    }
    let hoverWired = false;
    function wireGraphHover() {   // show a relation's label while its node or edge is under the pointer
      if (hoverWired) return; hoverWired = true;
      const box = $("#ent-detail"), mark = (i, on) => $$(`[data-i="${i}"]`, box).forEach((n) => n.classList.toggle("lit", on));
      box.addEventListener("pointerover", (e) => { const n = e.target.closest("[data-i]"); if (n) mark(n.dataset.i, true); });
      box.addEventListener("pointerout", (e) => { const n = e.target.closest("[data-i]"); if (n) mark(n.dataset.i, false); });
    }
    function svg(e) {
      const W = 560, H = 380, cx = W / 2, cy = H / 2;
      const ring = [];
      e.r.forEach(([rel, to, dir]) => { if (by[to] && !ring.some((x) => x.n === to)) ring.push({ n: to, rel: dir === "out" ? rel : to + " " + rel, w: 3, isRel: true }); });
      e.l.forEach(([n, w]) => { if (!ring.some((x) => x.n === n) && ring.length < 14) ring.push({ n, w }); });
      const maxW = Math.max(1, ...ring.map((x) => x.w));
      const pts = ring.map((x, i) => {
        const a = (i / Math.max(ring.length, 1)) * Math.PI * 2 - Math.PI / 2, r = 150;
        return { ...x, x: cx + Math.cos(a) * r * 1.35, y: cy + Math.sin(a) * r * 0.95 };
      });
      // Relation labels would pile up in the middle, so each one shows only while its node or edge is hovered.
      const lines = pts.map((p, i) => `<line x1="${cx}" y1="${cy}" x2="${p.x}" y2="${p.y}" class="g-edge${p.isRel ? " rel" : ""}" data-i="${i}" stroke-width="${p.isRel ? 2.5 : 1 + 4 * p.w / maxW}"/>` +
        `<line x1="${cx}" y1="${cy}" x2="${p.x}" y2="${p.y}" class="g-hit" data-i="${i}"/>`).join("");
      const labels = pts.map((p, i) => p.isRel ? `<text x="${cx + (p.x - cx) * 0.62}" y="${cy + (p.y - cy) * 0.62 - 6}" class="g-rel" data-i="${i}">${esc(p.rel)}</text>` : "").join("");
      const nodes = pts.map((p, i) => { const t = (by[p.n] || {}).t || "unknown";
        return `<a href="#e=${encodeURIComponent(p.n)}" data-i="${i}"><circle cx="${p.x}" cy="${p.y}" r="7" class="g-node t-${t}"/><text x="${p.x}" y="${p.y < cy - 20 ? p.y - 13 : p.y + 21}" class="g-label">${esc(p.n.length > 22 ? p.n.slice(0, 21) + "…" : p.n)}</text></a>`; }).join("");
      return `<svg viewBox="0 0 ${W} ${H}" class="g-svg" role="img" aria-label="Neighbourhood of ${esc(e.n)}">${lines}${nodes}${labels}` +
        `<circle cx="${cx}" cy="${cy}" r="12" class="g-node g-center t-${e.t}"/><text x="${cx}" y="${cy + 30}" class="g-label g-main">${esc(e.n)}</text></svg>`;
    }
    function detail() {
      const e = by[st.cur];
      if (!e) { $("#ent-detail").innerHTML = '<p class="empty">Pick an entity.</p>'; return; }
      const feats = e.f.map(([s, t, n, k]) => `<a class="chip" href="${k === "topic" ? "topics" : "features"}/${s}.html">${esc(t)} <span class="muted">${n}</span></a>`).join("");
      const rels = e.r.map(([rel, to, dir]) => `<li>${dir === "out" ? `${esc(e.n)} ${esc(rel)} <a href="#e=${encodeURIComponent(to)}">${esc(to)}</a>` : `<a href="#e=${encodeURIComponent(to)}">${esc(to)}</a> ${esc(rel)} ${esc(e.n)}`}</li>`).join("");
      const linked = e.l.map(([n, w]) => `<a class="chip" href="#e=${encodeURIComponent(n)}">${esc(n)} <span class="muted">${w}</span></a>`).join("");
      wireGraphHover();
      $("#ent-detail").innerHTML = `<div class="ent-head"><h2>${esc(e.n)}</h2>${typePill(e.t)}<span class="muted small">named in ${e.d} document${e.d === 1 ? "" : "s"}</span></div>` +
        (e.a.length ? `<p class="muted small">Also called: ${e.a.map(esc).join(", ")}</p>` : "") +
        (e.l.length || e.r.length ? svg(e) : "") +
        (rels ? `<h3>Relations</h3><ul>${rels}</ul>` : "") +
        (feats ? `<h3>Roadmap topics</h3><div class="ent-chips">${feats}</div>` : "") +
        (linked ? `<h3>Often named together with</h3><div class="ent-chips">${linked}</div><p class="muted small">Number = documents that name both.</p>` : "") +
        `<details class="ent-docs"><summary>Named in ${e.d} document${e.d === 1 ? "" : "s"}${e.d > 20 ? " (latest 20)" : ""}</summary><ul>${e.docs.filter(Boolean).map((t) => `<li>${esc(t)}</li>`).join("")}</ul></details>`;
    }
    function sync() {
      $$("#f-type button").forEach((b) => b.classList.toggle("on", b.dataset.v === st.type));
      list(); detail();
    }
    window.addEventListener("hashchange", () => { const m = location.hash.match(/e=([^&]+)/); if (m) { st.cur = decodeURIComponent(m[1]); sync(); } });
    $("#gq").addEventListener("input", (ev) => { st.q = ev.target.value; list(); });
    $("#f-type").addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (b) { st.type = b.dataset.v; sync(); } });
    sync();
  }

  // ---- Search across all of Mantis (IMP-006); index built with the site, searched here ----
  const gs = $("#gsearch"), gr = $("#gresults");
  if (gs) {
    const base = gs.dataset.base || "";
    let idx = null, sel = -1;
    const load = () => idx ? Promise.resolve(idx) : fetch(base + "search.json").then((r) => r.json()).then((d) => (idx = d)).catch(() => (idx = []));
    const norm = (s) => s.toLowerCase();
    const snip = (x, terms) => {
      const l = norm(x); let i = Math.max(0, ...terms.map((t) => l.indexOf(t)).filter((n) => n >= 0).slice(0, 1));
      const s = Math.max(0, i - 60), out = (s ? "…" : "") + x.slice(s, s + 170) + (x.length > s + 170 ? "…" : "");
      return terms.reduce((h, t) => h.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"), esc(out));
    };
    function run() {
      const q = gs.value.trim(); sel = -1;
      if (q.length < 2) { gr.hidden = true; return; }
      load().then((d) => {
        const terms = norm(q).split(/\s+/).filter(Boolean);
        const hits = [];
        for (const r of d) {
          const t = norm(r.t + " " + (r.a || "")), x = norm(r.x), w = norm(r.w || "");
          if (!terms.every((s) => t.includes(s) || x.includes(s) || w.includes(s))) continue;
          let sc = terms.reduce((a, s) => a + (t.includes(s) ? 6 : 0) + (t.startsWith(s) ? 3 : 0) + (w.includes(s) ? 2 : 0) + (x.includes(s) ? 1 : 0), 0);
          if (r.k === "Topic" || r.k === "Roadmap") sc += 4;   // summary pages first: read the card before any document
          else if (r.k === "Entity") sc += 1;
          const ql = norm(q);
          if (norm(r.t) === ql || (r.a || "").split("|").some((x) => norm(x) === ql)) sc += 20;
          hits.push([sc, r]);
        }
        hits.sort((a, b) => b[0] - a[0]);
        const top = hits.slice(0, 14).map(([, r]) => r);
        gr.innerHTML = top.length ? top.map((r, i) => {
          const inner = `<span class="gr-k">${esc(r.k)}</span><span class="gr-t">${esc(r.t)}</span>${r.w ? `<span class="gr-w">${esc(r.w)}</span>` : ""}` +
            (r.x ? `<span class="gr-x">${snip(r.x, terms)}</span>` : "");
          return r.u ? `<a class="gr" data-i="${i}" href="${base}${r.u}">${inner}</a>` : `<div class="gr gr-src" data-i="${i}">${inner}</div>`;
        }).join("") + (hits.length > 14 ? `<p class="gr-more">${hits.length - 14} more: add a word to narrow it down.</p>` : "")
          : `<p class="gr-more">Nothing found for "${esc(q)}".</p>`;
        gr.hidden = false;
      });
    }
    gs.addEventListener("input", run);
    gs.addEventListener("focus", () => { load(); if (gs.value.trim().length > 1) run(); });
    gs.addEventListener("keydown", (e) => {
      const links = $$(".gr", gr);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); sel = Math.max(0, Math.min(links.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
        links.forEach((l, i) => l.classList.toggle("on", i === sel));
      } else if (e.key === "Enter" && links[Math.max(sel, 0)] && links[Math.max(sel, 0)].href) {
        location.href = links[Math.max(sel, 0)].href; gr.hidden = true;
      } else if (e.key === "Escape") { gr.hidden = true; gs.blur(); }
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".gsearch")) gr.hidden = true; });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); gs.focus(); }
    });
  }

  // ---- Open items page (IMP-007) ----
  const oi = $("#f-oi");
  if (oi) {
    const apply = (v) => {
      $$("button", oi).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      $$("details.oi").forEach((d) => (d.hidden = !(v === "all" || d.dataset.kind === v || (v === "names" && /^(name|term)$/.test(d.dataset.kind)) || (v === "potential" && d.dataset.status !== "Open"))));
      $$(".oi-group").forEach((g) => {   // hide empty topics; the count shows what the filter leaves
        const n = $$("details.oi", g).filter((d) => !d.hidden).length;
        g.hidden = !n; $(".oi-n", g).textContent = n;
      });
    };
    oi.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) apply(b.dataset.v); });
    // One list (each question once) or By topic (grouped; a question linked to several topics repeats there)
    const view = $("#oi-view");
    const setView = (v) => {
      $$("button", view).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      $("#oi-flat").hidden = v !== "flat"; $("#oi-topics").hidden = v !== "topic"; $("#oi-topics-bar").hidden = v !== "topic";
      const n = $$(".oi-group").filter((g) => !g.hidden).length; $("#oi-topics-n").textContent = `${n} topic${n === 1 ? "" : "s"}`;
      store.set("mantis-oi-view", { v });
    };
    view.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) setView(b.dataset.v); });
    const ex = $("#oi-expand"), groups = () => $$(".oi-group").filter((g) => !g.hidden);
    const label = () => (ex.textContent = groups().every((g) => g.open) ? "Collapse all" : "Expand all");
    ex.addEventListener("click", () => { const open = !groups().every((g) => g.open); groups().forEach((g) => (g.open = open)); label(); });
    $$(".oi-group").forEach((g) => g.addEventListener("toggle", label));
    setView(location.hash.length > 1 ? "flat" : (store.get("mantis-oi-view").v || "flat"));   // a link to one question always uses the list
    const gf = $("[data-goto-filter]"); if (gf) gf.addEventListener("click", () => { apply("potential"); oi.scrollIntoView({ block: "start" }); });
    if (location.hash === "#waiting") apply("potential");
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView({ block: "center" }); }
  }

  // ---- Answering open items: drafts kept in the browser, submitted to the inbox via tools/serve.py ----
  const bar = $("#answer-bar");
  if (bar) {
    const KEY = "mantis-answers";
    const drafts = store.get(KEY);
    const LABEL = { answers: "Answers it", partly: "Partly answers it", someone: "Someone else must answer", same: "Same thing", different: "Different things" };
    const ready = (d) => d && d.verdict && (/^(same|different)$/.test(d.verdict) || (d.answer || "").trim() || (d.who || "").trim());
    const forms = $$(".answer");
    function paint(box) {
      const d = drafts[box.dataset.id] || {};
      $$(".verdict button", box).forEach((b) => b.classList.toggle("on", b.dataset.v === d.verdict));
      $(".who", box).hidden = d.verdict !== "someone";
      $(".answer-discard", box).hidden = !(d.answer || d.who || d.verdict);
      const sum = box.closest("details").querySelector("summary");
      let tag = sum.querySelector(".draft-tag");
      const has = (d.answer || d.who || d.verdict) && !box.classList.contains("sent");
      if (has && !tag) { tag = document.createElement("span"); tag.className = "tag draft-tag"; sum.appendChild(tag); }
      if (tag) { if (has) tag.textContent = ready(d) ? "Draft answer" : "Draft: choose an option"; else tag.remove(); }
    }
    function count() {
      const ids = Object.keys(drafts).filter((k) => ready(drafts[k]));
      const half = Object.keys(drafts).filter((k) => !ready(drafts[k]) && (drafts[k].answer || drafts[k].who)).length;
      bar.hidden = !ids.length && !half;
      $("#answer-count").textContent = `${ids.length} answer${ids.length === 1 ? "" : "s"} ready` + (half ? ` · ${half} still need an option chosen` : "");
      $("#answer-submit").disabled = !ids.length;
    }
    const save = () => { store.set(KEY, drafts); count(); };
    forms.forEach((box) => {
      const id = box.dataset.id, d = drafts[id];
      if (d) { $("textarea", box).value = d.answer || ""; $(".who", box).value = d.who || ""; }
      const twins = () => forms.filter((f) => f.dataset.id === id);   // the same question listed under several topics
      const upd = (k, v) => {
        drafts[id] = { ...(drafts[id] || {}), topic: box.dataset.topic, [k]: v };
        twins().forEach((f) => { if (f !== box) { $("textarea", f).value = drafts[id].answer || ""; $(".who", f).value = drafts[id].who || ""; } paint(f); });
        save();
      };
      $(".verdict", box).addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) upd("verdict", b.dataset.v); });
      $("textarea", box).addEventListener("input", (e) => upd("answer", e.target.value));
      $(".who", box).addEventListener("input", (e) => upd("who", e.target.value));
      $(".answer-discard", box).addEventListener("click", () => {   // cancel this one answer, leave the others
        delete drafts[id]; twins().forEach((f) => { $("textarea", f).value = ""; $(".who", f).value = ""; paint(f); }); save();
        toast("Answer discarded.");
      });
      paint(box);
    });
    count();
    function markSent(ids) {
      ids.forEach((id) => {
        forms.filter((f) => f.dataset.id === id).forEach((box) => {
        box.classList.add("sent"); $(".answer-form", box).hidden = true; $(".answer-sent", box).hidden = false;
        const sum = box.closest("details").querySelector("summary");
        if (!sum.querySelector(".sent-tag")) { const t = document.createElement("span"); t.className = "pill w-jira sent-tag"; t.textContent = "Answer sent"; sum.appendChild(t); }
        paint(box);
        });
      });
    }
    const served = location.protocol.startsWith("http") && window.fetch;
    if (served) fetch("api/answers/pending", { cache: "no-store" }).then((r) => r.json()).then((j) => markSent(j.pending || [])).catch(() => {});
    document.addEventListener("click", (e) => {   // one-click: accept the likely answer as a draft, submit with the rest
      const q = e.target.closest(".quick-confirm"); if (!q) return;
      const boxes = forms.filter((f) => f.dataset.id === q.dataset.q); if (!boxes.length) return;
      drafts[q.dataset.q] = { topic: boxes[0].dataset.topic, verdict: "answers", answer: "Confirmed: the likely answer is right." };
      boxes.forEach((b) => { $("textarea", b).value = drafts[q.dataset.q].answer; paint(b); }); save();
      q.textContent = "✓ Confirmed (submit below)"; q.disabled = true;
      toast("Confirmed as a draft. Press Submit answers when you are done.");
    });
    $("#answer-clear").addEventListener("click", () => {
      if (!confirm("Clear all draft answers on this page?")) return;
      Object.keys(drafts).forEach((k) => delete drafts[k]);
      forms.forEach((b) => { $("textarea", b).value = ""; $(".who", b).value = ""; paint(b); });
      save();
    });
    $("#answer-submit").addEventListener("click", async () => {
      const ids = Object.keys(drafts).filter((k) => ready(drafts[k]));
      const answers = ids.map((id) => ({ id, ...drafts[id] }));
      const asText = () => answers.map((a) => `## ${a.id}: ${a.topic}\n- Verdict: ${LABEL[a.verdict]}\n` + (a.who ? `- Who to ask: ${a.who}\n` : "") + `- Answer: ${a.answer || ""}`).join("\n\n");
      let r, j;
      try {
        if (!served) throw new Error("offline");
        r = await fetch("api/answers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers }) });
        j = await r.json();
      } catch (e) {   // only a failed connection means the server is down
        await copyText("Owner answers to open items:\n\n" + asText());
        toast("The site server isn't running, so your answers were copied instead. Paste them into Claude Code.");
        return;
      }
      if (!r.ok) { toast(j.error || "The answers could not be saved. Your drafts are still here."); return; }
      ids.forEach((k) => delete drafts[k]); save(); markSent(j.pending || ids);
      toast(`Saved ${j.saved} answer${j.saved === 1 ? "" : "s"}. Press Process answers to record ${j.saved === 1 ? "it" : "them"} now.`); if (typeof pollJobs === "function") pollJobs();
    });
  }

  // ---- Editing pages, epics and stories: rich text in, Markdown out, saved to the inbox via tools/serve.py ----
  if ($(".edit-btn")) {
    const assetBase = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    const served = location.protocol.startsWith("http") && window.fetch;
    const ALLOWED = new Set(["P", "H1", "H2", "H3", "H4", "UL", "OL", "LI", "STRONG", "B", "EM", "I", "A", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD", "BR", "CODE", "PRE", "BLOCKQUOTE", "HR"]);
    let libs = null;
    const loadScript = (src) => new Promise((ok, bad) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s); });
    const ensureLibs = () => libs || (libs = loadScript(assetBase + "assets/vendor/turndown.js").then(() => loadScript(assetBase + "assets/vendor/turndown-plugin-gfm.js")));

    function turndown() {
      const t = new window.TurndownService({ headingStyle: "atx", bulletListMarker: "-", emDelimiter: "*", strongDelimiter: "**", codeBlockStyle: "fenced", hr: "---", br: "" });
      t.use(window.turndownPluginGfm.gfm);
      t.addRule("li", { filter: "li", replacement: (content, node) => {   // "- item" / "1. item", like the Markdown Mantis writes
        content = content.replace(/^\n+/, "").replace(/\n+$/, "\n").replace(/\n/gm, "\n   ");
        const p = node.parentNode; let prefix = "- ";
        if (p.nodeName === "OL") prefix = (+(p.getAttribute("start") || 1) + Array.prototype.indexOf.call(p.children, node)) + ". ";
        return prefix + content + (node.nextSibling && !/\n$/.test(content) ? "\n" : "");
      } });
      return t;
    }
    function sanitize(root) {   // keep structure, drop styling, scripts and unknown wrappers (Word, web pages)
      $$("script,style,meta,link,title,xml,o\\:p", root).forEach((n) => n.remove());
      (function walk(el) {
        [...el.children].forEach((c) => {
          walk(c);
          if (c.tagName === "DIV" || c.tagName === "SECTION" || c.tagName === "ARTICLE") { const p = document.createElement("p"); p.append(...c.childNodes); c.replaceWith(p); return; }
          if (!ALLOWED.has(c.tagName)) { c.replaceWith(...c.childNodes); return; }
          [...c.attributes].forEach((a) => { if (!(c.tagName === "A" && a.name === "href") && a.name !== "start") c.removeAttribute(a.name); });
        });
      })(root);
      return root;
    }
    function normalizeTables(root) {   // every table gets a header row and even columns, so it converts to a Markdown table
      $$("table", root).forEach((tb) => {
        const rows = $$("tr", tb); if (!rows.length) { tb.remove(); return; }
        const width = Math.max(...rows.map((r) => [...r.children].reduce((n, c) => n + (+c.getAttribute("colspan") || 1), 0)));
        rows.forEach((r) => { [...r.children].forEach((c) => c.removeAttribute("colspan")); while (r.children.length < width) r.appendChild(document.createElement(r.parentNode.tagName === "THEAD" ? "th" : "td")); });
        if (!$("thead", tb)) {
          const head = document.createElement("thead"), first = rows[0];
          [...first.children].forEach((c) => { const th = document.createElement("th"); th.append(...c.childNodes); c.replaceWith(th); });
          head.appendChild(first); tb.insertBefore(head, tb.firstChild);
        }
        $$("th,td", tb).forEach((c) => {   // a cell must stay on one line in Markdown
          $$("p,li,h1,h2,h3,h4,div", c).forEach((b) => b.replaceWith(" ", ...b.childNodes, " "));
          $$("br", c).forEach((b) => b.replaceWith(" "));
          c.innerHTML = c.innerHTML.replace(/\|/g, "/").replace(/\s+/g, " ").trim();
        });
      });
      return root;
    }
    function toMarkdown(html) {
      const box = document.createElement("div"); box.innerHTML = html;
      sanitize(box); normalizeTables(box);
      $$("p", box).forEach((p) => { if (!p.textContent.trim() && !$("br,img", p)) p.remove(); });
      return mantisStyle(turndown().turndown(box));
    }
    function mantisStyle(md) {   // write Markdown the way Mantis files are written, so a diff shows only real changes
      return md.split("\n").map((l) => {
        if (/^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(l)) return "|" + l.split("|").filter((c) => c.trim()).map(() => "---").join("|") + "|";
        if (/^\|/.test(l)) l = l.replace(/\|\s{2,}(?=\|)/g, "| ");   // empty cells as "| |"
        return l.replace(/\\([\[\]])/g, "$1").replace(/(\w)\\_(?=\w)/g, "$1_").replace(/\s+$/, "");
      }).join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
    }
    function problems(md) {
      const out = [];
      if (!md.trim()) out.push("The document is empty.");
      const tag = md.match(/<\/?(table|tr|td|th|div|span|font|img|style|script|iframe|u)\b[^>]*>/i);
      if (tag) out.push(`Some formatting could not be converted (${tag[0]}). Remove it or retype that part as plain text.`);
      return out;
    }
    function warnings(md) {
      const out = [];
      if (/MANTIS-(DOC|GAP|ASM|CFL)-\d/.test(md)) out.push("It contains Mantis IDs, which mean nothing in Confluence or Jira.");
      if (/\[TBC\]/.test(md)) out.push(`It still has ${md.match(/\[TBC\]/g).length} [TBC] markers.`);
      return out;
    }
    function changed(a, b) {
      const A = a.split("\n").filter((l) => l.trim()), B = b.split("\n").filter((l) => l.trim());
      const sa = new Set(A), sb = new Set(B);
      return { removed: A.filter((l) => !sb.has(l)).length, added: B.filter((l) => !sa.has(l)).length };
    }

    const TOOLS = [["P", "Text", "formatBlock", "p"], ["H2", "Heading", "formatBlock", "h2"], ["H3", "Subheading", "formatBlock", "h3"], ["|"],
      ["B", "Bold", "bold"], ["I", "Italic", "italic"], ["•", "Bullet list", "insertUnorderedList"], ["1.", "Numbered list", "insertOrderedList"], ["🔗", "Link", "link"], ["|"],
      ["▦", "Insert table", "table"], ["+row", "Add row below", "row+"], ["+col", "Add column right", "col+"], ["−row", "Delete row", "row-"], ["−col", "Delete column", "col-"], ["|"],
      ["↶", "Undo", "undo"], ["↷", "Redo", "redo"]];
    function cellAtCaret() { const s = getSelection(); const n = s.rangeCount && s.getRangeAt(0).startContainer; const el = n && (n.nodeType === 1 ? n : n.parentElement); return el && el.closest("td,th"); }
    function tableOp(op) {
      const cell = cellAtCaret(); if (!cell) { toast("Put the cursor in a table cell first."); return; }
      const row = cell.parentElement, table = row.closest("table"), idx = [...row.children].indexOf(cell);
      if (op === "row+") { const r = document.createElement("tr"); [...row.children].forEach(() => r.appendChild(document.createElement("td"))); (row.parentNode.tagName === "THEAD" ? (table.tBodies[0] || table.appendChild(document.createElement("tbody"))).prepend(r) : row.after(r)); }
      if (op === "row-") { if (row.parentNode.tagName === "THEAD") { toast("The header row stays; edit its text instead."); return; } row.remove(); }
      if (op === "col+") $$("tr", table).forEach((r) => { const c = document.createElement(r.parentNode.tagName === "THEAD" ? "th" : "td"); const ref = r.children[idx]; ref ? ref.after(c) : r.appendChild(c); });
      if (op === "col-") { if (row.children.length < 2) { toast("A table needs at least one column."); return; } $$("tr", table).forEach((r) => r.children[idx] && r.children[idx].remove()); }
    }

    function startEdit(panel) {
      const tpl = $(".edit-src", panel), art = $("article.doc", panel), bar = $(".panel-bar", panel);
      const key = "mantis-edit:" + tpl.dataset.path, saved = store.get(key);
      const ed = document.createElement("div");
      ed.className = "editor doc"; ed.contentEditable = "true"; ed.spellcheck = true;
      ed.innerHTML = saved.base === tpl.dataset.base && saved.html ? saved.html : tpl.innerHTML;
      if (saved.base === tpl.dataset.base && saved.html) toast("Restored your unsaved draft.");
      const tb = document.createElement("div"); tb.className = "ed-toolbar nocopy";
      tb.innerHTML = TOOLS.map(([l, t, c, v]) => l === "|" ? '<span class="ed-sep"></span>' : `<button type="button" title="${t}" data-c="${c}" data-v="${v || ""}">${l}</button>`).join("");
      tb.addEventListener("mousedown", (e) => e.preventDefault());   // keep the selection in the editor
      tb.addEventListener("click", (e) => {
        const b = e.target.closest("button"); if (!b) return; ed.focus();
        const c = b.dataset.c;
        if (c === "link") { const u = prompt("Link address (https://…)"); if (u) document.execCommand("createLink", false, u); }
        else if (c === "table") document.execCommand("insertHTML", false, "<table><thead><tr><th>Heading</th><th>Heading</th></tr></thead><tbody><tr><td>&nbsp;</td><td>&nbsp;</td></tr></tbody></table><p><br></p>");
        else if (/^(row|col)[+-]$/.test(c)) tableOp(c);
        else document.execCommand(c, false, b.dataset.v || null);
        keep();
      });
      ed.addEventListener("paste", (e) => {
        e.preventDefault();
        const html = e.clipboardData.getData("text/html"), text = e.clipboardData.getData("text/plain");
        const box = document.createElement("div");
        if (html) box.innerHTML = html; else box.innerHTML = text.split(/\n{2,}/).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
        document.execCommand("insertHTML", false, sanitize(box).innerHTML);
        keep();
      });
      const keep = () => store.set(key, { base: tpl.dataset.base, html: ed.innerHTML });
      ed.addEventListener("input", keep);
      panel._view = art; art.replaceWith(tb, ed);
      bar.classList.add("editing");
      $(".bar-note", bar).textContent = "Editing. Your draft is kept in this browser until you save or cancel.";
      $(".bar-btns", bar).hidden = true;
      const acts = document.createElement("span"); acts.className = "bar-btns ed-acts";
      acts.innerHTML = '<button class="btn-line ed-cancel" type="button">Cancel</button><button class="btn ed-review" type="button">Review and save</button>';
      bar.appendChild(acts);
      const stop = () => { tb.remove(); ed.replaceWith(panel._view); acts.remove(); bar.classList.remove("editing"); $(".bar-btns", bar).hidden = false; $(".bar-note", bar).textContent = "Formatted for Confluence and Jira"; };
      $(".ed-cancel", acts).addEventListener("click", () => {
        const dirty = toMarkdown(ed.innerHTML) !== toMarkdown(tpl.innerHTML);
        if (dirty && !confirm("Discard your changes to this document?")) return;
        store.set(key, {}); stop();
      });
      $(".ed-review", acts).addEventListener("click", () => review(panel, tpl, ed, key, stop));
      ed.focus();
    }

    function review(panel, tpl, ed, key, stop) {
      const md = toMarkdown(ed.innerHTML), base = toMarkdown(tpl.innerHTML);
      const errs = problems(md), warns = warnings(md), diff = changed(base, md);
      const m = document.createElement("div"); m.className = "modal-wrap";
      m.innerHTML = `<div class="modal" role="dialog" aria-label="Review your edit"><h2>Review your edit</h2>
        <p>${diff.added || diff.removed ? `${diff.added} line${diff.added === 1 ? "" : "s"} added or changed, ${diff.removed} removed.` : "No changes yet."}</p>
        ${errs.map((x) => `<p class="m-err">⚠ ${esc(x)}</p>`).join("")}${warns.map((x) => `<p class="m-warn">${esc(x)}</p>`).join("")}
        <details><summary>Show the Markdown that will be saved</summary><pre class="m-md">${esc(md)}</pre></details>
        <p class="muted small">Saving puts this version in the Mantis inbox. Mantis applies it in the next session; the page here updates then.</p>
        <div class="m-btns"><button class="btn-line m-back" type="button">Keep editing</button><button class="btn m-save" type="button" ${errs.length || !(diff.added || diff.removed) ? "disabled" : ""}>Save to inbox</button></div></div>`;
      document.body.appendChild(m);
      const close = () => m.remove();
      $(".m-back", m).addEventListener("click", close);
      m.addEventListener("click", (e) => { if (e.target === m) close(); });
      $(".m-save", m).addEventListener("click", async () => {
        try {
          if (!served) throw new Error("offline");
          const r = await fetch(assetBase + "api/edits", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: tpl.dataset.path, base: tpl.dataset.base, markdown: md, title: document.title }) });
          const j = await r.json(); if (!r.ok) throw new Error(j.error || "failed");
          store.set(key, {}); close(); stop(); markPending(panel);
          toast("Saved to the inbox. Mantis applies it next session.");
        } catch (e) {
          await copyText(md); close();
          toast("The site server isn't running, so the Markdown was copied instead. Paste it into Claude Code.");
        }
      });
    }

    function markPending(panel) {
      const btn = $(".edit-btn", panel); if (btn) { btn.disabled = true; btn.textContent = "Edit sent"; btn.title = "Waiting for Mantis to apply your last edit"; }
      const note = $(".bar-note", panel); if (note) note.textContent = "Your edit is in the inbox. Mantis applies it next session.";
    }
    document.addEventListener("click", (e) => {
      const b = e.target.closest(".edit-btn"); if (!b || b.disabled) return;
      ensureLibs().then(() => startEdit(b.closest(".tab-panel"))).catch(() => toast("The editor could not load. Is the site served by tools/serve.py?"));
    });
    if (served) fetch(assetBase + "api/edits/pending", { cache: "no-store" }).then((r) => r.json()).then((j) => {
      $$(".edit-src").forEach((t) => { if ((j.pending || []).includes(t.dataset.path)) markPending(t.closest(".tab-panel")); });
    }).catch(() => {});
  }

  // ---- Date picker: any .dp-btn opens a small calendar with quick picks; click it again to close ----
  // The button keeps the chosen date in data-value and fires a bubbling "dp-pick" event (detail = YYYY-MM-DD or "").
  const ISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const addDays = (s, n) => { const d = new Date(s + "T12:00"); d.setDate(d.getDate() + n); return ISO(d); };
  const nextDow = (s, dow) => { const d = new Date(s + "T12:00"); d.setDate(d.getDate() + (((dow - d.getDay() + 7) % 7) || 7)); return ISO(d); };
  const dp = (() => {
    let pop = null, owner = null, view = null;
    const close = () => { if (pop) pop.remove(); if (owner) owner.setAttribute("aria-expanded", "false"); pop = owner = null; };
    function draw() {
      const t0 = owner.dataset.today || ISO(new Date()), cur = owner.dataset.value || "", kind = owner.dataset.kind || "when";
      const quick = kind === "due"
        ? [["Today", t0], ["Tomorrow", addDays(t0, 1)], ["This Friday", new Date(t0 + "T12:00").getDay() === 5 ? t0 : nextDow(t0, 5)], ["Next week", nextDow(t0, 1)], ["No due date", ""]]
        : [["Today", t0], ["Tomorrow", addDays(t0, 1)], ["Next Monday", nextDow(t0, 1)], ["In a week", addDays(t0, 7)]];
      const first = new Date(view), lead = (first.getDay() + 6) % 7, days = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
      let cells = "";
      for (let i = 0; i < lead; i++) cells += "<span></span>";
      for (let d = 1; d <= days; d++) {
        const v = ISO(new Date(first.getFullYear(), first.getMonth(), d)), past = kind === "when" && v < t0;
        cells += `<button type="button" data-d="${v}" class="${v === t0 ? "is-today" : ""}${v === cur ? " is-on" : ""}" ${past ? "disabled" : ""}>${d}</button>`;
      }
      pop.innerHTML = `<div class="dp-quick">${quick.map(([l, v]) => `<button type="button" data-d="${v}" class="${v === cur ? "is-on" : ""}"><span>${l}</span><small>${v ? new Date(v + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : ""}</small></button>`).join("")}</div>
        <div class="dp-cal"><div class="dp-head"><button type="button" data-nav="-1" aria-label="Previous month">‹</button><b>${first.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</b><button type="button" data-nav="1" aria-label="Next month">›</button></div>
        <div class="dp-grid">${["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((w) => `<i>${w}</i>`).join("")}${cells}</div></div>`;
    }
    function open(btn) {
      if (owner === btn) { close(); return; }
      close(); owner = btn; btn.setAttribute("aria-expanded", "true");
      view = new Date((btn.dataset.value || btn.dataset.today || ISO(new Date())) + "T12:00"); view.setDate(1);
      pop = document.createElement("div"); pop.className = "dp"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Pick a date");
      document.body.appendChild(pop); draw();
      const start = $(".dp-grid .is-on", pop) || $(".dp-grid .is-today", pop) || $(".dp-grid button:not(:disabled)", pop);
      if (start && btn.matches(":focus-visible")) start.focus();   // keyboard users land on the current day
      const r = btn.getBoundingClientRect(), w = pop.offsetWidth || 420;
      pop.style.top = `${scrollY + r.bottom + 8}px`;
      pop.style.left = `${Math.max(8, Math.min(scrollX + r.left, scrollX + document.documentElement.clientWidth - w - 8))}px`;
    }
    document.addEventListener("click", (e) => {
      const b = e.target.closest(".dp-btn");
      if (b) { e.preventDefault(); open(b); return; }
      if (!pop || !pop.contains(e.target)) { if (pop) close(); return; }
      const nav = e.target.closest("[data-nav]");
      if (nav) { view.setMonth(view.getMonth() + +nav.dataset.nav); draw(); return; }
      const d = e.target.closest("[data-d]");
      if (d && !d.disabled) { const btn = owner; btn.dataset.value = d.dataset.d; close(); btn.dispatchEvent(new CustomEvent("dp-pick", { bubbles: true, detail: d.dataset.d })); btn.focus(); }
    });
    document.addEventListener("keydown", (e) => {
      if (!pop) return;
      if (e.key === "Escape") { const b = owner; close(); b.focus(); return; }
      const cur = document.activeElement && document.activeElement.closest(".dp-grid [data-d]");
      const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
      if (!step) return;
      e.preventDefault();
      if (!cur) { const f = $(".dp-grid button:not(:disabled)", pop); if (f) f.focus(); return; }
      const want = addDays(cur.dataset.d, step), d = new Date(want + "T12:00");
      if (d.getMonth() !== view.getMonth() || d.getFullYear() !== view.getFullYear()) { view = new Date(want + "T12:00"); view.setDate(1); draw(); }
      const next = $(`.dp-grid [data-d="${want}"]:not(:disabled)`, pop); if (next) next.focus();
    });
    window.addEventListener("resize", close);
    return { close };
  })();

  // ---- Today: the owner's task list (MANTIS-IMP-018), saved to mantis/tasks/ through tools/serve.py ----
  // One rule for dates: `day` is when a task shows on Today. Scheduling sets day (and remind_on, so the
  // brief flags it on that day); Bring to today resets both. Deleting is soft: the task waits under
  // Recently deleted for 7 days. Every move offers Undo.
  const tList = $("#t-list");
  if (tList) {
    const served = location.protocol.startsWith("http") && window.fetch;
    const PR = { high: 0, medium: 1, low: 2, "": 3 };
    const PL = { high: ["High", "p-p1"], medium: ["Medium", "p-p2"], low: ["Low", "p-p3"] };
    let S = { rev: 0, tasks: [], dismissed: [], today: "", suggestions: { items: [] } }, openId = null, timer = null, focusNote = null;
    const uid = () => Math.random().toString(36).slice(2, 12);
    const fmtMin = (m) => (m >= 60 ? `${Math.floor(m / 60)}h${m % 60 ? " " + (m % 60) + "m" : ""}` : `${m}m`);
    const nice = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : "";
    const tomorrow = () => addDays(S.today, 1);
    const dayName = (d) => !d || d === S.today ? "Today" : d === tomorrow() ? "Tomorrow" : nice(d);
    const live = (t) => t.status === "todo" || t.status === "blocked";
    const carried = (t) => live(t) && t.day && t.day < S.today;
    // Days a focus task has been carried over (IMP-040): amber from day 1, stronger from day 3.
    const carriedDays = (t) => carried(t) ? Math.max(1, Math.round((new Date(S.today + "T12:00") - new Date(t.day + "T12:00")) / 864e5)) : 0;
    const isToday = (t) => live(t) && (!t.day || t.day <= S.today);
    const byOrder = (a, b) => a.order - b.order;
    const topOrder = () => Math.min(0, ...S.tasks.map((t) => t.order)) - 1;

    function save() {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const r = await fetch("api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rev: S.rev, tasks: S.tasks, dismissed: S.dismissed }) });
          const j = await r.json();
          if (r.status === 409) { Object.assign(S, j); draw(); toast("Your list changed in another tab; showing the latest."); return; }
          if (!r.ok) throw new Error(j.error);
          S.rev = j.rev;
        } catch (e) { toast("Could not save your tasks. Is the site server running?"); }
      }, 400);
    }
    const change = () => { draw(); save(); };
    const task = (id) => S.tasks.find((t) => t.id === id);
    function renumber(ids) { ids.forEach((id, i) => { const t = task(id); if (t) t.order = i; }); }
    // Change a task, show a message, and offer Undo (restores the task exactly as it was).
    function withUndo(t, msg, fn) {
      const before = JSON.parse(JSON.stringify(t));
      fn(); change();
      toast(msg, () => { const i = S.tasks.findIndex((x) => x.id === before.id); i < 0 ? S.tasks.push(before) : (S.tasks[i] = before); change(); });
    }
    const schedule = (t, v) => {   // put a task on a day ("" or today = Today)
      if (!v || v <= S.today) { t.day = S.today; t.remind_on = ""; } else { t.day = v; t.remind_on = v; }
      if (t.status !== "blocked") t.status = "todo";
      t.done_at = "";
      if (t.day === S.today) t.order = topOrder();
    };

    const dpBtn = (kind, value, label, extra = "") => `<button type="button" class="dp-btn ${extra}" data-kind="${kind}" data-value="${value}" data-today="${S.today}" aria-haspopup="dialog">${label}</button>`;
    function inline(t) {   // the one or two moves that matter most for where the task is now
      if (t.status === "deleted") return `<span class="t-inline"><button type="button" class="mini on" data-a="restore">Restore to today</button><button type="button" class="mini" data-a="restore-tomorrow">Restore for tomorrow</button><button type="button" class="mini t-del" data-a="purge">Delete for good</button></span>`;
      if (t.status === "parked") return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Back to today</button>${dpBtn("when", "", "Schedule…", "mini")}</span>`;
      if (live(t) && t.day > S.today) return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Bring to today</button>${dpBtn("when", t.day, "Move…", "mini")}</span>`;
      if (isToday(t)) return `<span class="t-inline hover-only"><button type="button" class="mini" data-a="tomorrow" title="Move to tomorrow">Tomorrow</button>${dpBtn("when", "", "Later…", "mini")}<button type="button" class="mini icon t-del" data-a="delete" title="Delete (you can restore it)" aria-label="Delete">✕</button></span>`;
      return "";
    }
    function row(t, opts = {}) {
      const p = PL[t.priority], over = live(t) && t.due && t.due < S.today, dueToday = t.due === S.today;
      const chips = [p ? `<span class="pill ${p[1]}">${p[0]}</span>` : "", t.status === "blocked" ? '<span class="pill w-review">Blocked</span>' : "",
        carried(t) ? `<span class="tag carry${carriedDays(t) >= 3 ? " carry-old" : ""}" title="On your list since ${nice(t.day)}">Backlog · carried ${carriedDays(t)} day${carriedDays(t) > 1 ? "s" : ""}</span>` : "",
        live(t) && t.day > S.today ? `<span class="tag tag-when">${esc(dayName(t.day))}</span>` : "",
        t.estimate ? `<span class="muted small">${fmtMin(t.estimate)}</span>` : "",
        t.due ? `<span class="small ${over ? "warn-text" : dueToday ? "due-today" : "muted"}">${over ? "Overdue · " : "Due "}${nice(t.due)}</span>` : "",
        t.contact ? `<span class="small t-who">Ask ${esc(t.contact)}</span>` : "",
        t.comments.length ? `<span class="muted small">💬 ${t.comments.length}</span>` : "",
        t.status === "deleted" ? `<span class="muted small">Deleted ${nice(t.deleted_at)}</span>` : ""].join("");
      const open = openId === t.id && t.status !== "deleted";
      return `<li class="t-row${carried(t) ? (carriedDays(t) >= 3 ? " t-carried carry-old" : " t-carried") : ""}${t.status === "done" ? " done" : ""}${t.status === "deleted" ? " gone" : ""}${open ? " open" : ""}" data-id="${t.id}" ${opts.drag ? 'draggable="true"' : ""}>
        <div class="t-main">${opts.drag ? '<span class="t-grip" title="Drag to rank">⋮⋮</span>' : ""}
        ${t.status === "deleted" ? "" : `<input type="checkbox" class="t-check" ${t.status === "done" ? "checked" : ""} aria-label="Done">`}
        <button type="button" class="t-title">${esc(t.title)}</button><span class="t-chips">${chips}</span>${inline(t)}</div>
        ${carried(t) && opts.drag ? `<div class="t-carry nocopy">Still relevant? <button type="button" class="mini on" data-a="keep">Keep for today</button>${dpBtn("when", "", "Move to…", "mini")}<button type="button" class="mini" data-a="park">Park</button></div>` : ""}
        ${open ? detail(t) : ""}</li>`;
    }
    function detail(t) {
      const log = t.comments.map((c) => `<li><span class="muted small">${esc(c.at)}</span> ${esc(c.text)}</li>`).join("");
      const est = [["0", "Time?"], ["15", "15 min"], ["30", "30 min"], ["60", "1 hour"], ["120", "2 hours"], ["240", "Half day"], ["480", "Full day"]];
      const prio = ["high", "medium", "low"].map((v) => `<button type="button" data-p="${v}" class="${t.priority === v ? "on" : ""}">${PL[v][0]}</button>`).join("");
      const later = live(t) && t.day > S.today;
      return `<div class="t-detail">
        <div class="t-fields">
          <label class="fld fld-wide"><span>Title</span><input data-f="title" value="${esc(t.title)}"></label>
          <div class="fld"><span>Priority</span><span class="prio-seg" data-f="priority">${prio}</span></div>
          <label class="fld"><span>Time</span><select class="sel sel-sm" data-f="estimate">${est.map(([v, l]) => `<option value="${v}" ${String(t.estimate) === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
          <div class="fld"><span>Do on</span>${dpBtn("when", live(t) ? t.day || S.today : "", live(t) ? dayName(t.day) : t.status === "parked" ? "Parked: pick a day" : "Pick a day")}</div>
          <div class="fld"><span>Due</span>${dpBtn("due", t.due, t.due ? nice(t.due) : "No due date")}</div>
          <label class="fld"><span>Ask</span><input data-f="contact" value="${esc(t.contact)}" placeholder="Who to reach out to"></label></div>
        <div class="t-log"><p class="small muted">Notes and findings</p><ul>${log || '<li class="muted small">None yet.</li>'}</ul>
        <div class="t-comment"><input placeholder="${t.status === "blocked" ? "What is it blocked on?" : "What you found so far, or why it is blocked"}" data-c="1"><button type="button" class="btn-line" data-a="comment">Add note</button></div></div>
        <div class="t-acts">${later || t.status === "parked" ? '<button type="button" class="btn" data-a="today">Bring to today</button>' : ""}
        ${t.status === "blocked" ? '<button type="button" class="btn-line" data-a="unblock">Unblock</button>' : t.status === "todo" ? '<button type="button" class="btn-line" data-a="block">Mark blocked</button>' : ""}
        ${t.day !== tomorrow() && t.status !== "done" ? '<button type="button" class="btn-line" data-a="tomorrow">Move to tomorrow</button>' : ""}
        ${t.status === "parked" ? "" : t.status !== "done" ? '<button type="button" class="btn-line" data-a="park">Park</button>' : ""}
        <button type="button" class="btn-line t-del" data-a="delete">Delete</button></div></div>`;
    }

    function brief() {
      const sug = (S.suggestions.items || []).filter((s) => !S.dismissed.includes(s.id));
      const body = sug.length ? sug.map((s) => `<details class="sug"><summary><b>${esc(s.title)}</b>${s.who ? `<span class="muted small">${esc(s.who)}</span>` : ""}</summary>
          <div class="sug-body">${s.why ? `<p>${esc(s.why)}</p>` : ""}${s.say ? `<p><b>What to say:</b> ${esc(s.say)}</p>` : ""}
          ${(s.questions || []).length ? `<p><b>Questions to ask:</b></p><ul>${s.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>` : ""}
          ${s.source ? `<p class="muted small">From: ${esc(s.source)}</p>` : ""}
          <div class="t-acts"><button type="button" class="btn" data-s="${s.id}" data-sa="add">Add to today</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="later">Tomorrow</button>
          <button type="button" class="btn-line" data-s="${s.id}" data-sa="copy">Copy</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="dismiss">Dismiss</button></div></div></details>`).join("")
        : S.suggestions.stale
          ? `<p class="muted small">No suggestions yet today.</p><div class="brief-acts"><button type="button" class="btn-line job ai" data-job="daily-brief" title="Uses Claude, on your normal quota">Prepare today's brief</button><button type="button" class="mini job" data-job="skip-brief" title="Free: no AI">Skip today</button></div>`
          : '<p class="muted small">Nothing more to suggest today.</p>';
      $("#t-brief").innerHTML = `<div class="sc-h"><h2><i class="bi bi-spark"></i>Mantis suggests</h2><span class="sc-n">${sug.length || ""}</span></div>${body}`;
    }

    function draw() {
      dp.close();
      const d = new Date(S.today + "T12:00");
      $("#t-date").textContent = d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
      const today = S.tasks.filter(isToday);
      // Carried-over tasks nobody has decided on yet go to the top; the rest follow the owner's ranking.
      today.sort((a, b) => (carried(b) - carried(a)) || byOrder(a, b));
      const mins = today.reduce((n, t) => n + (t.estimate || 0), 0);
      const later = S.tasks.filter((t) => live(t) && t.day > S.today).sort((a, b) => a.day.localeCompare(b.day) || byOrder(a, b));
      const parked = S.tasks.filter((t) => t.status === "parked").sort(byOrder);
      const done = S.tasks.filter((t) => t.status === "done").sort((a, b) => (b.done_at || "").localeCompare(a.done_at || ""));
      const bin = S.tasks.filter((t) => t.status === "deleted").sort((a, b) => (b.deleted_at || "").localeCompare(a.deleted_at || ""));
      const blocked = today.filter((t) => t.status === "blocked").length;
      $("#t-sum").textContent = today.length
        ? `${today.length} task${today.length === 1 ? "" : "s"} for today${mins ? `, about ${fmtMin(mins)} of work` : ""}${blocked ? `, ${blocked} blocked` : ""}. ${done.length} done.`
        : "Nothing on today's list. Add a task above.";
      $("#t-total").textContent = mins ? `≈ ${fmtMin(mins)}` : "";
      tList.innerHTML = today.map((t) => row(t, { drag: true })).join("") || '<li class="empty">Add your first task above.</li>';
      // Scheduled tasks grouped by day, so "what comes back when" reads at a glance.
      let last = "";
      $("#t-sched").innerHTML = later.map((t) => (t.day !== last ? `<li class="t-day">${esc(dayName((last = t.day)))}</li>` : "") + row(t)).join("") || '<li class="empty">Nothing scheduled.</li>';
      $("#t-park").innerHTML = parked.map((t) => row(t)).join("") || '<li class="empty">Nothing parked.</li>';
      $("#t-done").innerHTML = done.map((t) => row(t)).join("") || '<li class="empty">Nothing done yet today.</li>';
      $("#t-bin").innerHTML = bin.map((t) => row(t)).join("") || '<li class="empty">Nothing deleted.</li>';
      $("#t-sched-n").textContent = later.length; $("#t-park-n").textContent = parked.length; $("#t-done-n").textContent = done.length; $("#t-bin-n").textContent = bin.length;
      $("#t-bin-box").hidden = !bin.length; $("#t-sched-box").hidden = !later.length; $("#t-park-box").hidden = !parked.length; $("#t-done-box").hidden = !done.length;
      brief();
      if (focusNote) { const inp = document.querySelector(`.t-row[data-id="${focusNote}"] [data-c]`); if (inp) inp.focus(); focusNote = null; }
    }

    // Adding: priority toggle, when and due pickers
    const addPrio = $("#t-prio");
    addPrio.addEventListener("click", (e) => {
      const b = e.target.closest("[data-p]"); if (!b) return;
      addPrio.dataset.value = addPrio.dataset.value === b.dataset.p ? "" : b.dataset.p;
      $$("[data-p]", addPrio).forEach((x) => x.classList.toggle("on", x.dataset.p === addPrio.dataset.value));
    });
    const addWhen = $("#t-when"), addDue = $("#t-due");
    const labelAdd = () => {
      addWhen.textContent = dayName(addWhen.dataset.value); addWhen.classList.toggle("set", !!addWhen.dataset.value && addWhen.dataset.value !== S.today);
      addDue.textContent = addDue.dataset.value ? "Due " + nice(addDue.dataset.value) : "No due date"; addDue.classList.toggle("set", !!addDue.dataset.value);
    };
    addWhen.addEventListener("dp-pick", labelAdd); addDue.addEventListener("dp-pick", labelAdd);
    $("#t-add").addEventListener("submit", (e) => {
      e.preventDefault();
      const title = $("#t-title").value.trim(); if (!title) { $("#t-title").focus(); return; }
      const t = { id: uid(), title, status: "todo", priority: addPrio.dataset.value, estimate: +$("#t-est").value, due: addDue.dataset.value,
        remind_on: "", day: S.today, contact: $("#t-contact").value.trim(), comments: [], created: S.today, done_at: "", order: 0, source: "" };
      schedule(t, addWhen.dataset.value);
      if (t.day === S.today) t.order = Math.max(-1, ...S.tasks.filter(isToday).map((x) => x.order)) + 1;   // new work goes to the bottom of today
      S.tasks.push(t);
      e.target.reset(); addPrio.dataset.value = ""; $$("[data-p]", addPrio).forEach((x) => x.classList.remove("on"));
      addWhen.dataset.value = ""; addDue.dataset.value = ""; labelAdd();
      $("#t-title").focus(); change();
      toast(t.day > S.today ? `Scheduled for ${dayName(t.day)}. It comes back to Today then.` : "Added to today.", () => { S.tasks = S.tasks.filter((x) => x !== t); change(); });
    });

    // Every action on a task, in one place
    function act(t, a, rowEl) {
      const name = `"${t.title.length > 40 ? t.title.slice(0, 40) + "…" : t.title}"`;
      if (a === "keep") return withUndo(t, "Kept for today.", () => { t.day = S.today; t.remind_on = ""; });
      if (a === "today") return withUndo(t, `${name} is back on today's list.`, () => schedule(t, S.today));
      if (a === "tomorrow") return withUndo(t, `Moved to tomorrow.`, () => { schedule(t, tomorrow()); openId = null; });
      if (a === "park") return withUndo(t, "Parked. Find it under Parked.", () => { t.status = "parked"; openId = null; });
      if (a === "block") { t.status = "blocked"; openId = t.id; focusNote = t.id; t.comments.push({ at: S.today, text: "Marked blocked." }); return change(); }
      if (a === "unblock") { t.status = "todo"; t.comments.push({ at: S.today, text: "Unblocked." }); return change(); }
      if (a === "comment") { const inp = rowEl.querySelector("[data-c]"); if (!inp.value.trim()) return; t.comments.push({ at: S.today, text: inp.value.trim() }); focusNote = t.id; return change(); }
      if (a === "delete") return withUndo(t, `Deleted ${name}. It stays under Recently deleted for 7 days.`, () => { t.was = t.status; t.status = "deleted"; t.deleted_at = S.today; openId = null; });
      if (a === "restore") return withUndo(t, `Restored ${name} to today.`, () => { t.status = t.was === "blocked" ? "blocked" : "todo"; t.deleted_at = ""; t.was = ""; schedule(t, S.today); });
      if (a === "restore-tomorrow") return withUndo(t, `Restored ${name} for tomorrow.`, () => { t.status = "todo"; t.deleted_at = ""; t.was = ""; schedule(t, tomorrow()); });
      if (a === "purge") { S.tasks = S.tasks.filter((x) => x !== t); change(); toast(`Deleted ${name} for good.`, () => { S.tasks.push(t); change(); }); }
    }
    document.addEventListener("dp-pick", (e) => {
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      if (e.target.dataset.kind === "due") { withUndo(t, e.detail ? `Due ${nice(e.detail)}.` : "Due date removed.", () => { t.due = e.detail; }); return; }
      const v = e.detail;
      withUndo(t, !v || v <= S.today ? `${t.status === "parked" ? "Back on" : "On"} today's list.` : `Scheduled for ${dayName(v)}. It comes back to Today then.`, () => { schedule(t, v); if (v > S.today) openId = null; });
    });
    document.addEventListener("click", (e) => {
      const go = e.target.closest("[data-goto]");
      if (go) { openId = go.dataset.goto; draw(); const r = document.querySelector(`.t-row[data-id="${openId}"]`); if (r) r.scrollIntoView({ block: "center" }); return; }
      const sb = e.target.closest("[data-sa]");
      if (sb) {
        const s = (S.suggestions.items || []).find((x) => x.id === sb.dataset.s); if (!s) return;
        if (sb.dataset.sa === "copy") { copyText([s.title, s.why, s.who && "Who: " + s.who, s.say && "What to say: " + s.say, ...(s.questions || []).map((q) => "- " + q)].filter(Boolean).join("\n")); return; }
        let added = null;
        if (sb.dataset.sa !== "dismiss") {
          added = { id: uid(), title: s.title, status: "todo", priority: s.priority || "medium", estimate: s.estimate || 15, due: "", remind_on: "", day: S.today, contact: s.who || "",
            comments: [s.say && { at: S.today, text: "What to say: " + s.say }, (s.questions || []).length && { at: S.today, text: "Questions: " + s.questions.join(" / ") }].filter(Boolean),
            created: S.today, done_at: "", order: 0, source: "Mantis suggestion" };
          schedule(added, sb.dataset.sa === "later" ? tomorrow() : S.today);
          S.tasks.push(added);
        }
        S.dismissed.push(s.id); change();
        toast(sb.dataset.sa === "later" ? "Added to tomorrow." : sb.dataset.sa === "add" ? "Added to the top of today." : "Suggestion dismissed.",
          () => { S.dismissed = S.dismissed.filter((x) => x !== s.id); if (added) S.tasks = S.tasks.filter((x) => x !== added); change(); });
        return;
      }
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      const pb = e.target.closest(".prio-seg [data-p]");
      if (pb) { t.priority = t.priority === pb.dataset.p ? "" : pb.dataset.p; return change(); }
      if (e.target.classList.contains("t-check")) {
        if (e.target.checked) withUndo(t, "Done. Find it under Done.", () => { t.status = "done"; t.done_at = S.today; openId = null; });
        else withUndo(t, "Reopened on today's list.", () => { t.status = "todo"; t.done_at = ""; if (!t.day || t.day < S.today) t.day = S.today; });
        return;
      }
      const a = e.target.closest("[data-a]"); if (a) { act(t, a.dataset.a, r); return; }
      if (e.target.closest(".t-title") && t.status !== "deleted") { openId = openId === t.id ? null : t.id; draw(); }
    });
    document.addEventListener("change", (e) => {
      const f = e.target.closest("[data-f]"); if (!f || !f.closest(".t-row")) return;
      const t = task(f.closest(".t-row").dataset.id); if (!t) return;
      const k = f.dataset.f; t[k] = k === "estimate" ? +f.value : f.value.trim();
      if (k === "title" && !t.title) { t.title = "Untitled task"; }
      change();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches("[data-c]")) { e.preventDefault(); act(task(e.target.closest(".t-row").dataset.id), "comment", e.target.closest(".t-row")); }
      if (e.altKey && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
        const r = document.activeElement && document.activeElement.closest("#t-list .t-row"); if (!r) return;
        e.preventDefault();
        const ids = $$("#t-list .t-row").map((x) => x.dataset.id), i = ids.indexOf(r.dataset.id), j = i + (e.key === "ArrowUp" ? -1 : 1);
        if (j < 0 || j >= ids.length) return;
        [ids[i], ids[j]] = [ids[j], ids[i]]; renumber(ids); change();
        const again = document.querySelector(`.t-row[data-id="${r.dataset.id}"] .t-title`); if (again) again.focus();
      }
    });

    // Drag and drop ranking
    let dragId = null;
    tList.addEventListener("dragstart", (e) => { const r = e.target.closest(".t-row"); if (!r) return; dragId = r.dataset.id; r.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
    tList.addEventListener("dragend", (e) => { const r = e.target.closest(".t-row"); if (r) r.classList.remove("dragging"); $$(".t-row.drop-above,.t-row.drop-below").forEach((x) => x.classList.remove("drop-above", "drop-below")); });
    tList.addEventListener("dragover", (e) => {
      const r = e.target.closest(".t-row"); if (!r || !dragId || r.dataset.id === dragId) return;
      e.preventDefault(); const box = r.getBoundingClientRect(), above = e.clientY < box.top + box.height / 2;
      $$(".t-row.drop-above,.t-row.drop-below").forEach((x) => x.classList.remove("drop-above", "drop-below"));
      r.classList.add(above ? "drop-above" : "drop-below");
    });
    tList.addEventListener("drop", (e) => {
      const r = e.target.closest(".t-row"); if (!r || !dragId) return;
      e.preventDefault();
      const ids = $$("#t-list .t-row").map((x) => x.dataset.id).filter((id) => id !== dragId);
      const box = r.getBoundingClientRect(), above = e.clientY < box.top + box.height / 2;
      ids.splice(ids.indexOf(r.dataset.id) + (above ? 0 : 1), 0, dragId);
      const moved = task(dragId); if (moved && carried(moved)) moved.day = S.today;   // ranking a carry-over means it is today's work now
      renumber(ids); dragId = null; change();
    });
    $("#t-sortp").addEventListener("click", () => {
      const ids = S.tasks.filter(isToday).sort((a, b) => PR[a.priority] - PR[b.priority] || (a.due || "9999").localeCompare(b.due || "9999") || (a.estimate || 999) - (b.estimate || 999)).map((t) => t.id);
      const before = S.tasks.map((t) => [t.id, t.order]);
      renumber(ids); change();
      toast("Sorted by priority, then due date, then shortest first.", () => { before.forEach(([id, o]) => { const t = task(id); if (t) t.order = o; }); change(); });
    });

    if (!served) { $("#t-offline").hidden = false; $("#t-sum").textContent = ""; }
    else fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); addWhen.dataset.today = addDue.dataset.today = S.today; labelAdd(); draw(); })
      .catch(() => { $("#t-offline").hidden = false; });
    // Another part of the page changed a task (a suggested deadline was accepted): reload the list.
    document.addEventListener("mantis:tasks-changed", () => fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); draw(); }).catch(() => {}));
  }

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
        `<a href="${jBase}health.html#jobs">Details</a></div><button type="button" class="jh-x" aria-label="Close">✕</button>`;
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
    startJob(b.dataset.job, b.dataset.arg || (b.dataset.argFrom ? ($(b.dataset.argFrom) || {}).value : ""), b.textContent.trim());
  });
  // Inbox strip (Home, Health): what is waiting, with one button to process it all
  function paintInbox(st) {
    $$(".inbox-strip").forEach((s) => {
      const n = st.inbox || {}, parts = [];
      if (n.files) parts.push(`${n.files} file${n.files > 1 ? "s" : ""} to read`);
      if (n.edits) parts.push(`${n.edits} page edit${n.edits > 1 ? "s" : ""}`);
      if (n.answers) parts.push(`${n.answers} answer file${n.answers > 1 ? "s" : ""}`);
      const busy = (st.active || []).some((j) => j.type === "process-inbox");
      s.hidden = !parts.length && !busy;
      $(".is-what", s).textContent = parts.length ? "Waiting in your inbox: " + parts.join(" · ") : "Processing your inbox…";
    });
    $$(".answers-strip").forEach((s) => { s.hidden = !(st.inbox || {}).answers; });
    const jl = $("#job-list");
    if (jl) {
      const icon = { done: "✓", "needs-you": "!", failed: "×", running: "…", queued: "…" };
      const name = { done: "Done", "needs-you": "Needs you", failed: "Stopped", running: "Running", queued: "Waiting" };
      jl.innerHTML = (st.jobs || []).map((j) => `<details class="job-row jr-${j.state}"><summary><span class="jr-ico">${icon[j.state] || ""}</span><b>${esc(j.label)}</b>` +
        `<span class="muted small">${name[j.state] || j.state} · ${new Date(j.created).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}${j.kind === "claude" ? " · used Claude" : " · free"}</span></summary>` +
        `<div class="jr-body">${esc(j.summary || "").replace(/\n/g, "<br>")}${(j.needs_you || []).length ? `<p><b>Needs you:</b></p><ul>${j.needs_you.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</div></details>`).join("") ||
        '<p class="empty">No jobs yet. Buttons across the site start them.</p>';
      const q = $("#job-quota"); if (q) q.textContent = `${st.claude_today} of ${st.cap} Claude jobs used today${st.agent ? "" : " · Claude Code not found on this machine"}`;
    }
  }
  if (jobsOn) pollJobs();

  // ---- Confluence sync (MANTIS-IMP-019): copy only the sections that changed; remember what is in Confluence ----
  document.addEventListener("click", async (e) => {
    const cs = e.target.closest(".copy-sec");
    if (cs) { e.preventDefault(); e.stopPropagation(); copyHtml($(".sync-body", cs.closest(".sync-sec"))); return; }
    const pb = e.target.closest("[data-publish]");
    if (!pb) return;
    e.preventDefault(); e.stopPropagation();
    if (!jobsOn) { toast("Open Mantis from http://localhost:8000 to use this."); return; }
    try {
      const r = await fetch(jBase + "api/published", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: pb.dataset.publish }) });
      const j = await r.json();
      toast(r.ok ? "Remembered as the version in Confluence. Next time only changed sections show." : (j.error || "That didn't work."));
    } catch (err) { toast("The Mantis server isn't running."); }
  });

  // ---- People, follow-ups, briefs, deadlines, meetings, away (MANTIS-IMP-020/022/037/038/041) ----
  // Live data from tools/serve.py (GET /api/extra), changed through POST /api/followups, /api/deadlines,
  // /api/schedule. Briefs and handovers are written by Claude jobs and opened here; each bullet expands.
  const X = { d: null };
  const xOn = jobsOn && ($("#t-people") || $(".people-grid"));
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
    return bs.map((b) => `<button type="button" class="chip" data-brief="${b.id}">${((t, k) => t.toLowerCase().startsWith(k.toLowerCase()) ? esc(t) : esc(k) + " · " + esc(t))(b.title || b.for, { handover: "Handover", status: "Status" }[b.kind] || "Brief")} · ${dShort(b.date)}</button>`).join("");
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
    // Today, side column: brief me, then follow-ups
    const tp = $("#t-people");
    if (tp) {
      const g = d.followups || {}, persons = Object.keys(g).sort((a, b) => (g[b].items.length - g[a].items.length) || a.localeCompare(b));
      const nFu = persons.reduce((n, p) => n + g[p].items.length + g[p].steps.length, 0);
      const briefs = [briefLinks("", "meeting"), briefLinks("", "status")].join("");
      const meet = `<section class="side-card"><div class="sc-h"><h2>Meeting brief</h2></div>` +
        `<div class="mb-row"><select id="mb-who" class="sel sel-sm" aria-label="Meeting with">${whoOptions()}</select><button type="button" class="btn job ai" data-job="meeting-brief" data-arg-from="#mb-who" title="Uses Claude, on your normal quota">Brief me</button></div>` +
        (briefs ? `<div class="chips sc-chips">${briefs}</div>` : "") +
        `<button type="button" class="linkish small job ai" data-job="status-update" title="Uses Claude, on your normal quota">Write this week's status update</button></section>`;
      const fus = persons.map((p) => `<details class="fu-person"><summary><b>${esc(p)}</b><span class="fu-count">${g[p].items.length + g[p].steps.length}</span></summary>` +
        `<ul class="fu-list">${g[p].items.map(fuRow).join("")}${g[p].steps.map(stepRow).join("")}</ul></details>`).join("") || '<p class="muted small">Nothing open with anyone.</p>';
      const addFu = `<details class="fu-new"><summary>+ Add a follow-up</summary><form class="fu-add" id="fu-add"><input name="person" list="pp-names" placeholder="Person" required aria-label="Person"><input name="topic" placeholder="What to raise or chase" required aria-label="Topic">` +
        `<select name="kind" class="sel sel-sm" aria-label="Kind"><option value="raise">Raise with them</option><option value="wait">Waiting on them</option></select><button class="btn-line" type="submit">Add</button>${peopleList()}</form></details>`;
      tp.innerHTML = meet + `<section class="side-card" id="followups"><div class="sc-h"><h2>Follow-ups</h2><span class="sc-n">${nFu || ""}</span></div>${fus}${addFu}</section>`;
    }
    // People page: regular meetings (set up here, used by briefs and deadlines)
    const pm = $("#pp-meetings");
    if (pm) {
      const ms = (d.meetings || []).map((m) => `<li><b>${esc(m.name)}</b> <span class="muted small">${esc(m.day)}${m.time ? " " + esc(m.time) : ""}${m.every > 1 ? ` · every ${m.every} weeks` : ""} · with ${esc((m.attendees || []).join(", ") || "-")}${m.next ? ` · next ${dShort(m.next)}` : ""}</span> <button type="button" class="mini icon" data-meet-rm="${m.id}" aria-label="Remove">✕</button></li>`).join("");
      pm.innerHTML = `<ul class="meet-list">${ms || '<li class="muted small">None yet. Add your weekly meetings.</li>'}</ul>` +
        `<form class="fu-add" id="meet-add"><input name="name" placeholder="Meeting name (e.g. Sam 1-1)" required aria-label="Meeting name"><select name="day" class="sel sel-sm" aria-label="Day">${["Mon", "Tue", "Wed", "Thu", "Fri"].map((x) => `<option>${x}</option>`).join("")}</select>` +
        `<input name="time" type="time" aria-label="Time"><input name="attendees" list="pp-names" placeholder="With (names, comma-separated)" aria-label="With"><select name="every" class="sel sel-sm" aria-label="How often"><option value="1">Weekly</option><option value="2">Every 2 weeks</option></select><button class="btn-line" type="submit">Add</button>${peopleList()}</form>`;
    }
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
    m.innerHTML = `<div class="modal brief-modal" role="dialog" aria-label="${esc(b.title)}"><div class="bm-h"><div><p class="hello">${{ handover: "Handover", status: "Status update" }[b.kind] || "Meeting brief"} · ${dShort(b.date)}</p><h2>${esc(b.title)}</h2></div>` +
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
      const mr = e.target.closest("[data-meet-rm]"); if (mr) { xPost("api/schedule", { action: "remove-meeting", id: mr.dataset.meetRm }, "Meeting removed."); return; }
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
    if (location.hash) setTimeout(() => { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView({ block: "center" }); }, 300);
    loadX();
    // A finished brief or handover job: refresh the lists so the new brief appears
    let lastDone = "";
    setInterval(() => { if (!jState) return; const j = (jState.jobs || []).find((x) => ["meeting-brief", "handover"].includes(x.type) && x.ended); if (j && j.id !== lastDone) { if (lastDone) loadX(); lastDone = j.id; } }, 3000);
  }

  // ---- Live reload when served by tools/serve.py ----
  if (location.protocol.startsWith("http") && window.fetch) {
    const base = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    let ver = null;
    setInterval(() => fetch(base + "version.txt", { cache: "no-store" }).then((r) => r.text()).then((v) => {
      if (ver && v !== ver) location.reload(); ver = v;
    }).catch(() => {}), 2000);
  }
})();
