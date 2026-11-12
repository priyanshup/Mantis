/* back-to-top: the back-to-top ring. */
Mantis.define("back-to-top", ["ui-env", "core"], (m_uiEnv, m_core) => {
  const { root, calm } = m_uiEnv;
  const { $ } = m_core;
  // ---- Back to the top, with a ring that shows how far down you are ----
  const tt = document.createElement("button");
  tt.type = "button"; tt.className = "v3-totop"; tt.setAttribute("aria-label", "Back to top");
  tt.innerHTML = '<svg class="v3-ring" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="20"/><circle id="v3-prog" cx="22" cy="22" r="20"/></svg>' +
    '<svg class="v3-arr" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V6M6 12l6-6 6 6"/></svg>';
  document.body.appendChild(tt);
  const toTop = () => {
    const max = root.scrollHeight - innerHeight;
    tt.classList.toggle("show", max > innerHeight * .5 && scrollY > 480);
    const c = $("#v3-prog"); if (c) c.style.strokeDashoffset = String(125.7 * (1 - (max > 0 ? Math.min(1, scrollY / max) : 0)));
  };
  addEventListener("scroll", toTop, { passive: true }); addEventListener("resize", toTop); toTop();
  tt.addEventListener("click", () => scrollTo({ top: 0, behavior: calm.matches ? "auto" : "smooth" }));
});
