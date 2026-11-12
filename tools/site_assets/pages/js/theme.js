/* theme: the light and dark switch; follows the system until clicked. */
Mantis.define("theme", ["core"], (m_core) => {
  const { $ } = m_core;
  // ---- Theme: two states. It follows the system until the switch is clicked; only a click is remembered ----
  const tb = $("#theme");
  if (tb) {
    const sys = matchMedia("(prefers-color-scheme: dark)");
    const saved = () => { try { return localStorage.getItem("mantis-theme"); } catch (e) { return null; } };
    const dark = () => (saved() || (sys.matches ? "dark" : "light")) === "dark";
    const paint = () => { tb.setAttribute("aria-checked", String(dark())); tb.title = dark() ? "Dark theme: click for light" : "Light theme: click for dark"; };
    paint();
    sys.addEventListener("change", () => { if (!saved()) paint(); });
    tb.addEventListener("click", () => {
      const next = dark() ? "light" : "dark";
      try { localStorage.setItem("mantis-theme", next); } catch (e) {}
      document.documentElement.dataset.theme = next; paint();
    });
  }
});
