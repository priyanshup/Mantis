/* shortcuts: the shortcuts sheet, / for search, G then a letter. */
Mantis.define("shortcuts", ["core", "scroll-lock", "ui-env"], (m_core, m_scrollLock, m_uiEnv) => {
  const { $, $$ } = m_core;
  const { lock } = m_scrollLock;
  const { typing } = m_uiEnv;
  const kb = $("#kbar");   // the header's search button
  // ---- The shortcuts sheet (?), "/" for search, and G then a letter to go to a page ----
  const kbd = (k) => `<kbd>${k}</kbd>`;
  const KEYS = [
    ["Go anywhere", [["Search or ask", [["Ctrl", "K"]]], ["Same, from anywhere", [["/"]]], ["Today, Meetings, Features", [["G", "T"], ["G", "M"], ["G", "F"]]], ["Questions, Sources, Growth", [["G", "Q"], ["G", "S"], ["G", "R"]]]]],
    ["Tasks on Today", [["Move a task or a group up or down", [["Alt", "↑"], ["Alt", "↓"]]], ["Mark done", [["Space"]], "on its checkbox"]]],
    ["Menus and panels", [["Close", [["Esc"]]]]],
    ["This sheet", [["Show or hide the shortcuts", [["?"]]]]]];
  const closeKeys = () => { const k = $("#v3-keys"); if (k) { k.remove(); lock(); } };
  const openKeys = () => {
    if ($("#v3-keys")) return closeKeys();
    const row = ([label, combos, note]) => `<li><span class="v3-kl">${label}${note ? `<small>${note}</small>` : ""}</span><span class="v3-kc">${combos.map((c) => `<span class="v3-kcombo">${c.map(kbd).join("")}</span>`).join("")}</span></li>`;
    const el = document.createElement("div"); el.id = "v3-keys"; el.className = "v3-keys-wrap";
    el.innerHTML = `<div class="v3-scrim"></div><div class="v3-keys" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts"><div class="v3-keys-h"><h2>Keyboard shortcuts</h2><button type="button" class="v3-x" aria-label="Close">✕</button></div>` +
      `<div class="v3-kgrid">${KEYS.map(([h, rows]) => `<section><div class="v3-cap">${h}</div><ul>${rows.map(row).join("")}</ul></section>`).join("")}</div></div>`;
    document.body.appendChild(el); lock();
    el.addEventListener("click", (e) => { if (e.target.closest(".v3-scrim,.v3-x")) closeKeys(); });
  };
  let chord = 0, hint = null;
  const hideHint = () => { if (hint) hint.classList.remove("show"); };
  const GO = { t: "index.html#today", m: "index.html#meetings", f: "index.html#features", q: "index.html#questions", s: "index.html#sources", r: "index.html#growth" };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { closeKeys(); hideHint(); return; }
    if (typing() || e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key;
    if (k === "?") { e.preventDefault(); openKeys(); return; }
    if (k === "/" && !$("#v3-keys")) { e.preventDefault(); if (kb) kb.click(); return; }
    const dest = chord && Date.now() - chord < 1300 && GO[k.toLowerCase()];
    if (dest) {
      e.preventDefault(); chord = 0; hideHint();
      const a = $$("#mainnav a, .tabbar a").find((x) => (x.getAttribute("href") || "").endsWith(dest));
      if (a) location.href = a.href; return;
    }
    if (k.toLowerCase() === "g" && !$("#v3-keys") && !($("#palette") && !$("#palette").hidden)) {
      chord = Date.now();
      if (!hint) { hint = document.createElement("div"); hint.className = "v3-chord"; document.body.appendChild(hint); }
      hint.innerHTML = "Go to " + [["T", "Today"], ["M", "Meetings"], ["F", "Features"], ["Q", "Questions"], ["S", "Sources"], ["R", "Growth"]].map(([a, b]) => `${kbd(a)} ${b}`).join(" ");
      hint.classList.add("show"); setTimeout(hideHint, 1300);
    }
  });
});
