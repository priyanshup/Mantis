/* person-card: a person's card stays short. */
Mantis.define("person-card", ["core"], (m_core) => {
  const { $, $$ } = m_core;
  // ---- A person's card stays short: a long list shows three, the rest behind a button (2026-11-11) ----
  const drw = $("#drawer");
  const capLists = () => $$(".dr-ul", drw).forEach((ul) => {
    if (ul.dataset.cap || ul.children.length <= 4) return; ul.dataset.cap = "1";
    const extra = [...ul.children].slice(3); extra.forEach((li) => (li.hidden = true));
    const b = document.createElement("button"); b.type = "button"; b.className = "linkish small dr-more"; b.textContent = `Show ${extra.length} more`; ul.after(b);
    b.addEventListener("click", () => { const open = b.dataset.open !== "1"; extra.forEach((li) => (li.hidden = !open)); b.dataset.open = open ? "1" : ""; b.textContent = open ? "Show fewer" : `Show ${extra.length} more`; });
  });
  if (drw) new MutationObserver(capLists).observe(drw, { childList: true, subtree: true });
});
