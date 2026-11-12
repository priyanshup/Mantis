/* people-page: the People page as a plain list. */
Mantis.define("people-page", ["core"], (m_core) => {
  const { $$, $ } = m_core;
  // ---- The People page: a plain list. A row opens the side panel; the actions show on hover (2026-11-11) ----
  $$("article.person").forEach((card) => {
    const h3 = $("h3", card), acts = $(".tile-acts", card); if (!h3 || !acts) return;
    const fs = $$(".pp-f", card), val = (f) => (f && f.children[1] ? f.children[1].textContent.trim().split(/[;(]/)[0].trim() : "");
    const sub = [val(fs[0]), val(fs[1])].filter(Boolean).join(" · ");
    const head = document.createElement("div"); head.className = "pr-head"; head.dataset.person = card.dataset.name; head.tabIndex = 0; head.setAttribute("role", "button");
    const s2 = document.createElement("span"); s2.className = "pr-sub"; s2.textContent = sub;
    const chev = document.createElement("span"); chev.className = "pr-chev"; chev.setAttribute("aria-hidden", "true");
    head.append(h3, s2, acts, chev); card.prepend(head);
    head.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && e.target === head) { e.preventDefault(); head.click(); } });
  });
});
