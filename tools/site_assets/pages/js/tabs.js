/* tabs: a feature page's tabs, stories and topic switcher. */
Mantis.define("tabs", ["core"], (m_core) => {
  const { $, $$ } = m_core;
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
});
