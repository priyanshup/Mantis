/* scroll-lock: lock scrolling while the search or shortcuts sheet is open. */
Mantis.define("scroll-lock", ["ui-env", "core"], (m_uiEnv, m_core) => {
  const { root } = m_uiEnv;
  const { $ } = m_core;
  // ---- Scroll lock while the search or the shortcuts sheet is open ----
  const lock = () => root.classList.toggle("locked", !!($("#palette") && !$("#palette").hidden) || !!$("#v3-keys"));
  const pal = $("#palette"); if (pal) new MutationObserver(lock).observe(pal, { attributes: true, attributeFilter: ["hidden"] });
  return { lock };
});
