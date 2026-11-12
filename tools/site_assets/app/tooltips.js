/* tooltips.js: a small themed tip for icon-only controls and titled elements, on every page.
   It appears quickly (instantly when another tip was just closed), never repeats text the control already shows, and goes away the moment
   the pointer leaves, the control is redrawn, the page scrolls or a key is pressed. */
(() => {
  if (window.__mantisTip) return; window.__mantisTip = 1;
  const hover = matchMedia("(hover: hover)");
  const DELAY = 200, WARM = 500, MAX = 110;   // ms before the first tip, window in which the next one is instant, longest text shown
  let tip = null, timer = 0, watch = 0, cur = null, lastHide = 0;
  const box = () => { if (!tip) { tip = document.createElement("div"); tip.id = "mn-tip"; tip.setAttribute("role", "tooltip"); document.body.appendChild(tip); } return tip; };
  const find = (n) => (n && n.closest ? n.closest("[data-tip],[title],button[aria-label],a[aria-label]") : null);
  const raw = (el) => el.dataset.tip || el.getAttribute("title") || ((el.classList.contains("ic") || !(el.textContent || "").trim()) && el.getAttribute("aria-label")) || "";
  const textOf = (el) => {
    let s = String(raw(el)).replace(/\s+/g, " ").trim(); if (!s) return "";
    const seen = (el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
    if (seen && seen.includes(s.toLowerCase().slice(0, 40))) return "";   // the control already says it
    return s.length > MAX ? s.slice(0, MAX - 1).trimEnd() + "…" : s;
  };
  const hide = () => { clearTimeout(timer); clearInterval(watch); if (cur) lastHide = Date.now(); cur = null; if (tip) tip.classList.remove("on"); };
  const show = (el) => {
    const s = textOf(el); if (!s || !el.isConnected || !el.matches(":hover")) return;
    if (el.hasAttribute("title")) { el.dataset.tip = el.getAttribute("title"); el.removeAttribute("title"); }
    cur = el; const d = box(); d.textContent = s; d.classList.remove("on"); d.style.left = "0px"; d.style.top = "0px";
    const r = el.getBoundingClientRect(), w = d.offsetWidth, h = d.offsetHeight;
    let top = r.top - h - 8, pos = "above"; if (top < 8) { top = r.bottom + 8; pos = "below"; }
    d.dataset.pos = pos; d.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px"; d.style.top = top + "px";
    requestAnimationFrame(() => { if (cur === el) d.classList.add("on"); });
    clearInterval(watch);   // a control that is redrawn or moved from under the pointer never gets a mouseout: look for that
    watch = setInterval(() => { if (!cur || !cur.isConnected || !(cur.matches(":hover") || cur.matches(":focus-visible"))) hide(); }, 120);
  };
  document.addEventListener("mouseover", (e) => {
    if (!hover.matches) return;
    const el = find(e.target); if (el === cur) return;
    hide(); if (el && textOf(el)) timer = setTimeout(() => show(el), Date.now() - lastHide < WARM ? 0 : DELAY);
  });
  document.addEventListener("mouseout", (e) => { const el = find(e.target); if (el && el === cur && !(e.relatedTarget && el.contains(e.relatedTarget))) hide(); else if (!e.relatedTarget) hide(); });
  document.addEventListener("focusin", (e) => { const el = find(e.target); if (el && textOf(el) && el.matches(":focus-visible")) { hide(); show(el); } });
  ["focusout", "pointerdown", "keydown", "wheel", "dragstart"].forEach((n) => document.addEventListener(n, hide, true));
  addEventListener("scroll", hide, true); addEventListener("blur", hide); document.addEventListener("mouseleave", hide);
})();
