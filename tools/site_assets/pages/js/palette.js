/* palette: search or ask over any page (Ctrl K). */
Mantis.define("palette", ["core", "people-data", "jobs"], (m_core, m_peopleData, m_jobs) => {
  const { $, esc, $$, toast, bus } = m_core;
  const { X, briefLinks, xOn, loadX } = m_peopleData;
  const { startJob } = m_jobs;
  // ---- Search or ask (IMP-006, 2026-10-31 redesign): one box over any page, Ctrl K or / opens it ----
  // Finds people, features and documents from the index built with the site; the first row asks Mantis instead.
  const gs = $("#gsearch"), gr = $("#gresults"), pal = $("#palette");
  let openPalette = () => {}, closePalette = () => {};
  if (gs) {
    const base = gs.dataset.base || "";
    let idx = null, sel = 0;
    const load = () => idx ? Promise.resolve(idx) : fetch(base + "search.json").then((r) => r.json()).then((d) => (idx = d)).catch(() => (idx = []));
    const norm = (s) => s.toLowerCase();
    const snip = (x, terms) => {
      const l = norm(x); let i = Math.max(0, ...terms.map((t) => l.indexOf(t)).filter((n) => n >= 0).slice(0, 1));
      const s = Math.max(0, i - 60), out = (s ? "…" : "") + x.slice(s, s + 170) + (x.length > s + 170 ? "…" : "");
      return terms.reduce((h, t) => h.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"), esc(out));
    };
    const KIND = ["Feature", "Idea", "Person"];   // groups in this order, then the rest as the index names them
    const pick = (i) => { const rows = $$(".gr", gr); sel = Math.max(0, Math.min(rows.length - 1, i)); rows.forEach((l, n) => l.classList.toggle("on", n === sel)); if (rows[sel]) rows[sel].scrollIntoView({ block: "nearest" }); };
    function run() {
      const q = gs.value.trim(); sel = 0;
      const ask = q.length > 2 ? `<p class="gr-h">Ask Mantis</p><button type="button" class="gr gr-ask" data-ask="${esc(q)}"><span class="gr-t">${esc(q.endsWith("?") ? q : q + "?")}</span><span class="gr-w">a sourced answer</span></button>` : "";
      if (q.length < 2) {   // before typing: the answers Mantis gave lately (MANTIS-IMP-081), each opening in place
        const answers = X.d ? briefLinks("", "answer") : "";
        gr.innerHTML = '<p class="gr-more">Type a name, a feature or a few words from a document. A longer phrase can go to Mantis as a question.</p>' +
          (answers ? `<p class="gr-h">Recent answers</p><div class="chips gr-chips">${answers}</div>` : "");
        return;
      }
      load().then((d) => {
        const terms = norm(q).split(/\s+/).filter(Boolean);
        const hits = [];
        for (const r of d) {
          const t = norm(r.t + " " + (r.a || "")), x = norm(r.x), w = norm(r.w || "");
          if (!terms.every((s) => t.includes(s) || x.includes(s) || w.includes(s))) continue;
          let sc = terms.reduce((a, s) => a + (t.includes(s) ? 6 : 0) + (t.startsWith(s) ? 3 : 0) + (w.includes(s) ? 2 : 0) + (x.includes(s) ? 1 : 0), 0);
          if (r.k === "Feature" || r.k === "Idea") sc += 4;   // summary pages first: read the card before any document
          else if (r.k === "Person") sc += 2;
          const ql = norm(q);
          if (norm(r.t) === ql || (r.a || "").split("|").some((x) => norm(x) === ql)) sc += 20;
          hits.push([sc, r]);
        }
        hits.sort((a, b) => b[0] - a[0]);
        const top = hits.slice(0, 12).map(([, r]) => r);
        const kinds = [...new Set([...KIND.filter((k) => top.some((r) => r.k === k)), ...top.map((r) => r.k)])];
        const row = (r) => {   // one line: the name, and where it lives; documents add a matching snippet below
          const inner = `<span class="gr-t">${esc(r.t)}</span>${r.w ? `<span class="gr-w">${esc(r.w)}</span>` : ""}` + (r.x && !KIND.includes(r.k) ? `<span class="gr-x">${snip(r.x, terms)}</span>` : "");
          return r.p ? `<a class="gr" href="${base}${r.u}" data-person="${esc(r.p)}">${inner}</a>` : r.u ? `<a class="gr" href="${base}${r.u}">${inner}</a>` : `<div class="gr gr-src">${inner}</div>`;
        };
        const found = kinds.map((k) => `<p class="gr-h">${esc(k === "Person" ? "People" : k === "Idea" ? "Ideas" : k + "s")}</p>` + top.filter((r) => r.k === k).map(row).join("")).join("");
        gr.innerHTML = (found ? ask + found : `<p class="gr-more">Nothing found for "${esc(q)}".</p>` + ask) +
          (hits.length > 12 ? `<p class="gr-more">${hits.length - 12} more: add a word to narrow it down.</p>` : "");
        pick(found ? (ask ? 1 : 0) : 0);   // a match comes first; Tab or ↑ reaches the question
      });
    }
    openPalette = () => {
      if (!pal) return; pal.hidden = false; document.body.classList.add("pal-open"); gs.select(); gs.focus(); load().then(run);
      if (xOn && !X.d) loadX().then(() => { if (gs.value.trim().length < 2) run(); });
    };
    closePalette = () => { if (!pal || pal.hidden) return; pal.hidden = true; document.body.classList.remove("pal-open"); };
    const go = (el) => {
      if (!el) return;
      if (el.dataset.ask) { closePalette(); startJob("ask", el.dataset.ask, "Ask Mantis"); toast("Asking Mantis. The answer opens from the corner when it is ready."); return; }
      el.click(); closePalette();
    };
    gs.addEventListener("input", run);
    gs.addEventListener("keydown", (e) => {
      const rows = $$(".gr", gr);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); pick(sel + (e.key === "ArrowDown" ? 1 : -1)); }
      else if (e.key === "Tab" && $(".gr-ask", gr)) { e.preventDefault(); pick(0); }
      else if (e.key === "Enter") { e.preventDefault(); go(rows[sel]); }
      else if (e.key === "Escape") closePalette();
    });
    gr.addEventListener("click", (e) => { const a = e.target.closest(".gr-ask"); if (a) go(a); else if (e.target.closest("a.gr, [data-brief]")) closePalette(); });
    pal.addEventListener("click", (e) => {
      if (e.target === pal) closePalette();
      const d = e.target.closest("[data-dopen]"); if (d) { closePalette(); bus.emit("drawer:open", d.dataset.dopen); }
    });
    const kb = $("#kbar"); if (kb) kb.addEventListener("click", openPalette);
    document.addEventListener("keydown", (e) => {
      const typing = /input|textarea|select/i.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
      if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); pal.hidden ? openPalette() : closePalette(); }
      else if (e.key === "/" && !typing && pal.hidden) { e.preventDefault(); openPalette(); }
    });
  }

  bus.on("palette:close", () => closePalette());
});
