/* menus: details.pop menus close on an outside click or Esc. */
Mantis.define("menus", ["core"], (m_core) => {
  const { $$, $ } = m_core;
  // ---- Menus (details.pop: Filter, ⋯, Brief me for someone): a click outside or Esc closes them ----
  // the event's path, not contains(): a click inside may re-render the menu (the bulk buttons) and detach its target
  document.addEventListener("click", (e) => { const path = e.composedPath(); $$("details.pop[open]").forEach((d) => { if (!path.includes(d)) d.open = false; }); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    $$("details.pop[open]").forEach((d) => { d.open = false; $("summary", d).focus(); });
  });
});
