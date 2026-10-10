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

