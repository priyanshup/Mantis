/* ui.js: the small component library and the layout engine. Load this first.
   A widget is written once, UI.widget("tab.name", ctx => innerHtml), in widgets-*.js. Which widgets a screen shows, in which
   column and order, comes from site_config/layout.json (window.APP_LAYOUT). Wrapping (card, stagger, id) happens here, so a widget
   returns only what is inside its card and never repeats the card markup. Colours and sizes live in theme.json. */
const UI = (() => {
  const LAY = window.APP_LAYOUT || { tabs: [], screens: {}, widgets: {} };
  const registry = {};

  /* components: one place for each repeated piece of markup */
  const cardHead = (title, o = {}) => `<div class="card-h"><h2>${title}</h2>${o.hint ? `<span class="hint">${o.hint}</span>` : ""}${o.action || ""}</div>`;
  const empty = (text) => `<p class="zero">${text}</p>`;
  const head = (title, o = {}) => `<div class="head${o.rise ? " rise" : ""}${o.flush ? " flush" : ""}"${o.rise ? ' style="--i:0"' : ""}><div><h1${o.titleClass ? ` class="${o.titleClass}"` : ""}>${title}</h1>${o.sub ? `<p class="sub${o.mono ? " mono" : ""}">${o.sub}</p>` : ""}${o.headline || ""}</div>${o.action || ""}</div>`;
  const card = (inner, o = {}) => {
    const tag = o.tag || "section";
    return `<${tag} class="card${o.variant ? " " + o.variant : ""}${o.plain ? "" : " rise"}"${o.plain ? " data-still" : ` style="--i:${o.i || 0}"`}${o.id ? ` id="${o.id}"` : ""}>${inner}</${tag}>`;
  };

  /* registry and layout. widgets.<id> in layout.json: dom_id, variant, tag (aside), plain (no entrance), raw (draws its own card), fixed_i */
  const widget = (id, render) => { registry[id] = render; };
  const place = (screen, ctx) => {
    const sc = LAY.screens[screen]; if (!sc) return "";
    const hidden = new Set(sc.hidden || []), W = LAY.widgets || {};
    const cols = sc.cols.map((col) => col.filter((id) => !hidden.has(id)).map((id) => ({ id, html: registry[id] ? registry[id](ctx) : "" })).filter((x) => x.html));
    const order = {}; let n = sc.stagger_start || 0;   // the entrance stagger runs across the columns, row by row
    for (let r = 0, depth = Math.max(0, ...cols.map((c) => c.length)); r < depth; r++) cols.forEach((c) => { if (c[r]) order[c[r].id] = n++; });
    const one = (x) => { const w = W[x.id] || {}; return w.raw ? x.html : card(x.html, { variant: w.variant, id: w.dom_id, tag: w.tag, plain: w.plain, i: w.fixed_i !== undefined ? w.fixed_i : order[x.id] }); };
    if (sc.flat) { const inner = cols.map((c) => c.map(one).join("")).join(""); return sc.cols_class ? `<div class="${sc.cols_class}">${inner}</div>` : inner; }   // cards side by side, no column wrappers
    return `<div class="cols${sc.cols_class ? " " + sc.cols_class : ""}">${cols.map((c) => `<div class="col">${c.map(one).join("")}</div>`).join("")}</div>`;
  };
  const ICONS = { find: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>' };
  const icon = (n) => `<svg viewBox="0 0 24 24" class="ico" aria-hidden="true">${ICONS[n]}</svg>`;
  const tabs = () => LAY.tabs.filter((t) => t.visible !== false).map((t) => [t.id, t.label]);
  return { cardHead, empty, head, card, widget, place, tabs, icon };
})();
