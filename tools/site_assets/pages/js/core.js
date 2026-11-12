/* core: helpers every page uses ($, $$, esc, store, pill), the toast and the copy buttons. */
Mantis.define("core", [], () => {
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
    $$("th, td", c).forEach((x) => { x.style.border = "1px solid " + getComputedStyle(document.documentElement).getPropertyValue("--table-line").trim(); x.style.padding = "6px 8px"; });
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
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;
  // A tiny event bus, so two modules never need each other: one says what happened, the other listens.
  const bus = (() => { const h = {}; return { on(name, fn) { (h[name] = h[name] || []).push(fn); }, emit(name, ...a) { (h[name] || []).forEach((fn) => fn(...a)); } }; })();
  return { $, $$, store, toast, esc, copyText, pill, bus, copyHtml, plural };
});
