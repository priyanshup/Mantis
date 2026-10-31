// Mantis site: copy buttons, tabs, roadmap and work boards, filters, live reload. No libraries.
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = { get(k) { try { return JSON.parse(localStorage.getItem(k) || "{}"); } catch (e) { return {}; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
  const pill = (l, c) => `<span class="pill ${c}">${esc(l)}</span>`;

  // ---- Toast and copy ----
  let timer;
  function toast(msg, undo) {   // with `undo`, the toast offers an Undo button and stays a little longer
    const t = $("#toast"); t.textContent = msg; t.classList.add("show"); t.classList.toggle("has-undo", !!undo);
    if (undo) {
      const b = document.createElement("button"); b.type = "button"; b.className = "toast-undo"; b.textContent = "Undo";
      b.addEventListener("click", () => { t.classList.remove("show"); undo(); toast("Undone."); }, { once: true });
      t.appendChild(b);
    }
    clearTimeout(timer); timer = setTimeout(() => t.classList.remove("show"), undo ? 6000 : 1800);
  }
  function pasteReady(el) {
    const c = el.cloneNode(true);
    $$(".nocopy", c).forEach((n) => n.remove());
    $$(".tbl", c).forEach((w) => w.replaceWith(...w.childNodes));
    $$("table", c).forEach((t) => { t.setAttribute("border", "1"); t.style.borderCollapse = "collapse"; });
    $$("th, td", c).forEach((x) => { x.style.border = "1px solid #c1c7d0"; x.style.padding = "6px 8px"; });
    $$("section", c).forEach((s) => s.replaceWith(...s.childNodes));
    $$("[class]", c).forEach((x) => x.removeAttribute("class"));
    return c;
  }
  async function copyHtml(el) {
    const c = pasteReady(el);
    const html = c.innerHTML, text = c.innerText || c.textContent;
    try {
      await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([text], { type: "text/plain" }) })]);
    } catch (e) {
      const tmp = document.createElement("div");
      tmp.innerHTML = html; tmp.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(tmp);
      const r = document.createRange(); r.selectNodeContents(tmp);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      document.execCommand("copy"); s.removeAllRanges(); tmp.remove();
    }
    toast("Copied. Paste into Confluence or Jira.");
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); } catch (e) {
      const t = document.createElement("textarea"); t.value = text; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove();
    }
    toast("Copied: " + (text.length > 40 ? text.slice(0, 40) + "…" : text));
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.classList.contains("copy-sec")) copyHtml(b.closest(".sec"));
    else if (b.classList.contains("copy-all")) copyHtml($(".doc", b.closest(".tab-panel")));
    else if (b.classList.contains("copy-ov")) copyHtml($("#p-overview .doc"));   // the card's hidden full copy, not the folded view
    else if (b.classList.contains("copy-text")) copyText(b.dataset.text);
  });

  // ---- Something is on its way: an orange sweep along the header's bottom edge (2026-10-31). It shows for any
  // request slower than 150 ms and while a background job runs; the page's own reload check never trips it.
  const busyEl = $("#busy");
  let inflight = 0, busyT = null;
  const busy = () => busyEl && busyEl.classList.toggle("on", inflight > 0 || document.body.classList.contains("job-running"));
  if (busyEl && window.fetch) {
    const f0 = window.fetch.bind(window);
    window.fetch = (u, ...rest) => {
      if (String(u).includes("version.txt")) return f0(u, ...rest);
      inflight++; clearTimeout(busyT); busyT = setTimeout(busy, 150);
      return f0(u, ...rest).finally(() => { inflight--; clearTimeout(busyT); busy(); });
    };
  }

  // ---- Menus (details.pop: Filter, ⋯, Brief me for someone): a click outside or Esc closes them ----
  // the event's path, not contains(): a click inside may re-render the menu (the bulk buttons) and detach its target
  document.addEventListener("click", (e) => { const path = e.composedPath(); $$("details.pop[open]").forEach((d) => { if (!path.includes(d)) d.open = false; }); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    $$("details.pop[open]").forEach((d) => { d.open = false; $("summary", d).focus(); });
  });

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

  // Navigation is five plain links (MANTIS-IMP-094): the header on wide windows, the tab bar at the bottom on
  // narrow ones (CSS swaps them). Nothing to open or close, so nothing here.

