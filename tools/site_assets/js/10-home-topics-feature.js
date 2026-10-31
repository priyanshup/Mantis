  // ---- Features, Mine: rank what you follow (drag, or Alt+↑/↓ on a row), saved to focus.json through tools/serve.py ----
  const fl = $("#focus-list");
  if (fl) {
    let saveT = null;
    const persist = () => { clearTimeout(saveT); saveT = setTimeout(sendOrder, 500); };
    const sendOrder = async () => {
      try {
        const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "order", order: $$(".f-row", fl).map((r) => r.dataset.slug) }) });
        if (!r.ok) throw new Error();
        toast("Focus order saved.");
      } catch (e) { toast("Could not save the order. Is the site server running?"); }
    };
    fl.addEventListener("keydown", (e) => {   // a row's link focused: Alt+↑/↓ moves it within its group
      if (!e.altKey || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
      const r = e.target.closest(".f-row"), sib = r && (e.key === "ArrowUp" ? r.previousElementSibling : r.nextElementSibling);
      if (!sib) return;
      e.preventDefault(); e.key === "ArrowUp" ? sib.before(r) : sib.after(r); $("a", r).focus(); persist();
    });
    let drag = null;
    fl.addEventListener("dragstart", (e) => { drag = e.target.closest(".f-row"); if (drag) drag.classList.add("dragging"); });
    fl.addEventListener("dragend", () => { if (drag) drag.classList.remove("dragging"); $$(".f-row", fl).forEach((x) => x.classList.remove("drop-above", "drop-below")); });
    fl.addEventListener("dragover", (e) => {
      const r = e.target.closest(".f-row"); if (!r || !drag || r === drag || r.parentElement !== drag.parentElement) return;
      e.preventDefault(); const above = e.clientY < r.getBoundingClientRect().top + r.offsetHeight / 2;
      $$(".f-row", fl).forEach((x) => x.classList.remove("drop-above", "drop-below")); r.classList.add(above ? "drop-above" : "drop-below");
    });
    fl.addEventListener("drop", (e) => {
      const r = e.target.closest(".f-row"); if (!r || !drag || r === drag || r.parentElement !== drag.parentElement) return;
      e.preventDefault(); const above = e.clientY < r.getBoundingClientRect().top + r.offsetHeight / 2;
      above ? r.before(drag) : r.after(drag); drag = null; persist();
    });
  }
  // Does a card's work type pass the type filter? Business and Technical each include cards that are both.
  function workMatch(w, sel) {
    w = w || "";
    return !sel || sel === "all" || (sel === "none" ? !w : w === sel || (w === "both" && (sel === "business" || sel === "technical")));
  }

  // ---- Features: Mine / Roadmap / All (2026-10-31 redesign), plus Follow and Roadmap buttons saved via tools/serve.py ----
  // Mine shows the ranked focus list, Roadmap the board, list and timeline; All lists every card. Ideas only and
  // Archived are views of All, chosen in the Filter menu.
  const ttab = $("#ttab");
  if (ttab) {
    const PANEL = { focus: "focus", roadmap: "roadmap", ideas: "tiles", all: "tiles", archived: "tiles" };
    const fromHash = () => { const h = location.hash.slice(1); return h === "following" ? "focus" : PANEL[h] ? h : ""; };
    let tab = fromHash() || store.get("mantis-features").tab || "focus";
    if (!PANEL[tab]) tab = "focus";
    const tq = $("#tq"), tw = $("#t-work");
    let work = store.get("mantis-features").work || "all";   // the type filter (front matter "work"), shared with the roadmap
    const ff = $("#f-filter");
    const show = () => {
      $$("[data-scope-panel]").forEach((p) => (p.hidden = p.dataset.scopePanel !== PANEL[tab]));
      const q = (tq.value || "").toLowerCase(); let n = 0;
      $$(".all-row").forEach((t) => {
        const arc = t.dataset.archived === "1";
        const inTab = tab === "archived" ? arc : !arc && (tab === "all" || (tab === "ideas" && t.dataset.idea === "1"));
        t.hidden = !inTab || !workMatch(t.dataset.work, work) || (q && !t.textContent.toLowerCase().includes(q)); if (!t.hidden) n++;
      });
      const fq = ff ? ff.value.toLowerCase() : "";
      $$("#focus-list .f-row").forEach((r) => (r.hidden = !workMatch(r.dataset.work, work) || (fq && !r.textContent.toLowerCase().includes(fq))));
      if (tw) $$("button", tw).forEach((b) => b.classList.toggle("on", b.dataset.v === work));
      const lit = PANEL[tab] === "tiles" ? "all" : tab;   // Ideas only and Archived are views of All
      $$("button", ttab).forEach((b) => { b.classList.toggle("on", b.dataset.v === lit); b.setAttribute("aria-selected", String(b.dataset.v === lit)); });
      const ab = $("[data-arch]"); if (ab) ab.classList.toggle("on", tab === "archived");
      const ib = $("[data-ideas]"); if (ib) ib.classList.toggle("on", tab === "ideas");
      const ro = $(".rd-only"); if (ro) ro.hidden = tab !== "roadmap";
      const fp = $("#f-pop summary"); if (fp) fp.textContent = work !== "all" || tab === "ideas" || tab === "archived" ? "Filter · on" : "Filter";
      $("#t-empty").hidden = PANEL[tab] !== "tiles" || n > 0; store.set("mantis-features", { tab, work });
      drawBulk();
    };
    window.addEventListener("hashchange", () => { const h = fromHash(); if (h) { tab = h; show(); } });
    // Mine: a group of ideas only starts folded; opening or closing it is remembered in this browser
    $$("#focus-list details.f-fold").forEach((d) => {
      d.open = !!store.get("mantis-folds")[d.dataset.work];
      d.addEventListener("toggle", () => { const f = store.get("mantis-folds"); f[d.dataset.work] = d.open; store.set("mantis-folds", f); });
    });
    // Bulk actions work on the cards shown (so a filter narrows them). Each offers Undo, which survives
    // the page reload that follows the site rebuild.
    const BULK = { ideas: [["follow", "Follow all"], ["roadmap", "Add all to roadmap"]],
      all: [["follow", "Follow all"], ["unfollow", "Unfollow all"], ["roadmap", "Add all to roadmap"], ["unroadmap", "Clear roadmap"]],
      archived: [["unarchive", "Restore all"]] };
    const INVERSE = { follow: "unfollow", unfollow: "follow", roadmap: "unroadmap", unroadmap: "roadmap", archive: "unarchive", unarchive: "archive" };
    const FIELD = (a) => /archive/.test(a) ? "archived" : /follow/.test(a) ? "following" : "roadmap";
    const bulkEl = $("#t-bulk");
    const targets = (action) => $$(".all-row").filter((t) => !t.hidden && (t.dataset[FIELD(action)] === "1") === /^un/.test(action));
    function drawBulk() {
      const filtered = !!(tq.value || "").trim();
      bulkEl.innerHTML = (BULK[tab] || []).map(([a, l]) => { const n = targets(a).length;
        return `<button type="button" data-bulk="${a}" ${n ? "" : "disabled"}>${l}${filtered ? " shown" : ""}${n ? ` · ${n}` : ""}</button>`; }).join("");
      $("#t-bulk-box").hidden = !bulkEl.innerHTML;   // only in All, Ideas and Archived, inside the Filter menu
    }
    const LABEL = { following: ["Follow", "Following"], roadmap: ["Roadmap", "On roadmap"], archived: ["Archive", "Restore"] };
    const BTN = { following: "follow", roadmap: "roadmap", archived: "archive" };
    function setTile(tile, action) {
      const f = FIELD(action), on = !/^un/.test(action), b = $(`.act[data-a="${BTN[f]}"]`, tile);
      tile.dataset[f] = on ? "1" : "0"; b.textContent = LABEL[f][+on]; if (f !== "archived") { b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); }
      if (f === "roadmap") tile.dataset.idea = !on && tile.dataset.feat === "0" ? "1" : "0";   // an idea is a topic off the roadmap
      if (action === "archive") { setTile(tile, "unfollow"); setTile(tile, "unroadmap"); }   // the server does the same
    }
    async function bulk(action, slugs) {
      const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "bulk-" + action, order: slugs }) });
      if (!r.ok) throw new Error((await r.json()).error);
      slugs.forEach((s) => { const t = $(`.all-row[data-slug="${s}"]`); if (t) setTile(t, action); });
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
    const ab = $("[data-arch]"); if (ab) ab.addEventListener("click", () => { tab = tab === "archived" ? "all" : "archived"; show(); });
    const ib = $("[data-ideas]"); if (ib) ib.addEventListener("click", () => { tab = tab === "ideas" ? "all" : "ideas"; show(); });
    tq.addEventListener("input", show);
    if (ff) ff.addEventListener("input", show);
    if (tw) tw.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { work = b.dataset.v; show(); } });
    document.addEventListener("click", async (e) => {
      const b = e.target.closest(".row-acts .act"); if (!b) return;
      const tile = b.closest(".all-row"), f = { follow: "following", roadmap: "roadmap", archive: "archived" }[b.dataset.a];
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
      // a tab owns one panel or several ("page epic- story-": Drafts); a trailing dash matches a prefix
      $$(".tabs a").forEach((a) => { const on = a.dataset.match.split(" ").some((m) => (m.endsWith("-") ? id.startsWith(m) : id === m));
        a.classList.toggle("on", on); if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
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
  if (lib) {   // pages, epics and stories, plus the Diagrams and Decisions sections (IMP-068); #diagrams opens one directly
    const show = (v) => {
      $$("button", lib).forEach((x) => x.classList.toggle("on", x.dataset.v === v));
      const sec = v === "diagrams" || v === "decisions";
      $$(".lib").forEach((r) => (r.hidden = v !== "all" && r.dataset.kind !== v));
      $$(".lib-sec").forEach((s) => (s.hidden = v !== "all" && (sec ? s.dataset.libsec !== v : s.dataset.libsec !== "written")));
    };
    lib.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) show(b.dataset.v); });
    const h = location.hash.slice(1); if (h === "diagrams" || h === "decisions") show(h);
  }
  const bl = $("#backlog"); if (bl && location.hash === "#backlog") { bl.open = true; bl.scrollIntoView(); }

