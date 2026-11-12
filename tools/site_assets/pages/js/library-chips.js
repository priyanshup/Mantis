/* library-chips: the Library page's chips. */
Mantis.define("library-chips", ["core"], (m_core) => {
  const { $, $$ } = m_core;
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
});
