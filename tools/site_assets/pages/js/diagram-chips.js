/* diagram-chips: the Diagrams chips. */
Mantis.define("diagram-chips", ["core"], (m_core) => {
  const { $, $$ } = m_core;
  // ---- Diagrams chips (IMP-008) ----
  const dia = $("#f-dia");
  if (dia) dia.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", dia).forEach((x) => x.classList.toggle("on", x === b));
    $$(".dia").forEach((r) => (r.hidden = b.dataset.v !== "all" && r.dataset.type !== b.dataset.v));
  });
});
