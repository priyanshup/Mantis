  // ---- Editing pages, epics and stories: rich text in, Markdown out, saved to the inbox via tools/serve.py ----
  if ($(".edit-btn")) {
    const assetBase = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    const served = location.protocol.startsWith("http") && window.fetch;
    const ALLOWED = new Set(["P", "H1", "H2", "H3", "H4", "UL", "OL", "LI", "STRONG", "B", "EM", "I", "A", "TABLE", "THEAD", "TBODY", "TR", "TH", "TD", "BR", "CODE", "PRE", "BLOCKQUOTE", "HR"]);
    let libs = null;
    const loadScript = (src) => new Promise((ok, bad) => { const s = document.createElement("script"); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s); });
    const ensureLibs = () => libs || (libs = loadScript(assetBase + "assets/vendor/turndown.js").then(() => loadScript(assetBase + "assets/vendor/turndown-plugin-gfm.js")));

    function turndown() {
      const t = new window.TurndownService({ headingStyle: "atx", bulletListMarker: "-", emDelimiter: "*", strongDelimiter: "**", codeBlockStyle: "fenced", hr: "---", br: "" });
      t.use(window.turndownPluginGfm.gfm);
      t.addRule("li", { filter: "li", replacement: (content, node) => {   // "- item" / "1. item", like the Markdown Mantis writes
        content = content.replace(/^\n+/, "").replace(/\n+$/, "\n").replace(/\n/gm, "\n   ");
        const p = node.parentNode; let prefix = "- ";
        if (p.nodeName === "OL") prefix = (+(p.getAttribute("start") || 1) + Array.prototype.indexOf.call(p.children, node)) + ". ";
        return prefix + content + (node.nextSibling && !/\n$/.test(content) ? "\n" : "");
      } });
      return t;
    }
    function sanitize(root) {   // keep structure, drop styling, scripts and unknown wrappers (Word, web pages)
      $$("script,style,meta,link,title,xml,o\\:p", root).forEach((n) => n.remove());
      (function walk(el) {
        [...el.children].forEach((c) => {
          walk(c);
          if (c.tagName === "DIV" || c.tagName === "SECTION" || c.tagName === "ARTICLE") { const p = document.createElement("p"); p.append(...c.childNodes); c.replaceWith(p); return; }
          if (!ALLOWED.has(c.tagName)) { c.replaceWith(...c.childNodes); return; }
          [...c.attributes].forEach((a) => { if (!(c.tagName === "A" && a.name === "href") && a.name !== "start") c.removeAttribute(a.name); });
        });
      })(root);
      return root;
    }
    function normalizeTables(root) {   // every table gets a header row and even columns, so it converts to a Markdown table
      $$("table", root).forEach((tb) => {
        const rows = $$("tr", tb); if (!rows.length) { tb.remove(); return; }
        const width = Math.max(...rows.map((r) => [...r.children].reduce((n, c) => n + (+c.getAttribute("colspan") || 1), 0)));
        rows.forEach((r) => { [...r.children].forEach((c) => c.removeAttribute("colspan")); while (r.children.length < width) r.appendChild(document.createElement(r.parentNode.tagName === "THEAD" ? "th" : "td")); });
        if (!$("thead", tb)) {
          const head = document.createElement("thead"), first = rows[0];
          [...first.children].forEach((c) => { const th = document.createElement("th"); th.append(...c.childNodes); c.replaceWith(th); });
          head.appendChild(first); tb.insertBefore(head, tb.firstChild);
        }
        $$("th,td", tb).forEach((c) => {   // a cell must stay on one line in Markdown
          $$("p,li,h1,h2,h3,h4,div", c).forEach((b) => b.replaceWith(" ", ...b.childNodes, " "));
          $$("br", c).forEach((b) => b.replaceWith(" "));
          c.innerHTML = c.innerHTML.replace(/\|/g, "/").replace(/\s+/g, " ").trim();
        });
      });
      return root;
    }
    function toMarkdown(html) {
      const box = document.createElement("div"); box.innerHTML = html;
      sanitize(box); normalizeTables(box);
      $$("p", box).forEach((p) => { if (!p.textContent.trim() && !$("br,img", p)) p.remove(); });
      return mantisStyle(turndown().turndown(box));
    }
    function mantisStyle(md) {   // write Markdown the way Mantis files are written, so a diff shows only real changes
      return md.split("\n").map((l) => {
        if (/^\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(l)) return "|" + l.split("|").filter((c) => c.trim()).map(() => "---").join("|") + "|";
        if (/^\|/.test(l)) l = l.replace(/\|\s{2,}(?=\|)/g, "| ");   // empty cells as "| |"
        return l.replace(/\\([\[\]])/g, "$1").replace(/(\w)\\_(?=\w)/g, "$1_").replace(/\s+$/, "");
      }).join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
    }
    function problems(md) {
      const out = [];
      if (!md.trim()) out.push("The document is empty.");
      const tag = md.match(/<\/?(table|tr|td|th|div|span|font|img|style|script|iframe|u)\b[^>]*>/i);
      if (tag) out.push(`Some formatting could not be converted (${tag[0]}). Remove it or retype that part as plain text.`);
      return out;
    }
    function warnings(md) {
      const out = [];
      if (/MANTIS-(DOC|GAP|ASM|CFL)-\d/.test(md)) out.push("It contains Mantis IDs, which mean nothing in Confluence or Jira.");
      if (/\[TBC\]/.test(md)) out.push(`It still has ${md.match(/\[TBC\]/g).length} [TBC] markers.`);
      return out;
    }
    function changed(a, b) {
      const A = a.split("\n").filter((l) => l.trim()), B = b.split("\n").filter((l) => l.trim());
      const sa = new Set(A), sb = new Set(B);
      return { removed: A.filter((l) => !sb.has(l)).length, added: B.filter((l) => !sa.has(l)).length };
    }

    const TOOLS = [["P", "Text", "formatBlock", "p"], ["H2", "Heading", "formatBlock", "h2"], ["H3", "Subheading", "formatBlock", "h3"], ["|"],
      ["B", "Bold", "bold"], ["I", "Italic", "italic"], ["•", "Bullet list", "insertUnorderedList"], ["1.", "Numbered list", "insertOrderedList"], ["🔗", "Link", "link"], ["|"],
      ["▦", "Insert table", "table"], ["+row", "Add row below", "row+"], ["+col", "Add column right", "col+"], ["−row", "Delete row", "row-"], ["−col", "Delete column", "col-"], ["|"],
      ["↶", "Undo", "undo"], ["↷", "Redo", "redo"]];
    function cellAtCaret() { const s = getSelection(); const n = s.rangeCount && s.getRangeAt(0).startContainer; const el = n && (n.nodeType === 1 ? n : n.parentElement); return el && el.closest("td,th"); }
    function tableOp(op) {
      const cell = cellAtCaret(); if (!cell) { toast("Put the cursor in a table cell first."); return; }
      const row = cell.parentElement, table = row.closest("table"), idx = [...row.children].indexOf(cell);
      if (op === "row+") { const r = document.createElement("tr"); [...row.children].forEach(() => r.appendChild(document.createElement("td"))); (row.parentNode.tagName === "THEAD" ? (table.tBodies[0] || table.appendChild(document.createElement("tbody"))).prepend(r) : row.after(r)); }
      if (op === "row-") { if (row.parentNode.tagName === "THEAD") { toast("The header row stays; edit its text instead."); return; } row.remove(); }
      if (op === "col+") $$("tr", table).forEach((r) => { const c = document.createElement(r.parentNode.tagName === "THEAD" ? "th" : "td"); const ref = r.children[idx]; ref ? ref.after(c) : r.appendChild(c); });
      if (op === "col-") { if (row.children.length < 2) { toast("A table needs at least one column."); return; } $$("tr", table).forEach((r) => r.children[idx] && r.children[idx].remove()); }
    }

    function startEdit(panel) {
      const tpl = $(".edit-src", panel), art = $("article.doc", panel), bar = $(".panel-bar", panel);
      const key = "mantis-edit:" + tpl.dataset.path, saved = store.get(key);
      const ed = document.createElement("div");
      ed.className = "editor doc"; ed.contentEditable = "true"; ed.spellcheck = true;
      ed.innerHTML = saved.base === tpl.dataset.base && saved.html ? saved.html : tpl.innerHTML;
      if (saved.base === tpl.dataset.base && saved.html) toast("Restored your unsaved draft.");
      const tb = document.createElement("div"); tb.className = "ed-toolbar nocopy";
      tb.innerHTML = TOOLS.map(([l, t, c, v]) => l === "|" ? '<span class="ed-sep"></span>' : `<button type="button" title="${t}" data-c="${c}" data-v="${v || ""}">${l}</button>`).join("");
      tb.addEventListener("mousedown", (e) => e.preventDefault());   // keep the selection in the editor
      tb.addEventListener("click", (e) => {
        const b = e.target.closest("button"); if (!b) return; ed.focus();
        const c = b.dataset.c;
        if (c === "link") { const u = prompt("Link address (https://…)"); if (u) document.execCommand("createLink", false, u); }
        else if (c === "table") document.execCommand("insertHTML", false, "<table><thead><tr><th>Heading</th><th>Heading</th></tr></thead><tbody><tr><td>&nbsp;</td><td>&nbsp;</td></tr></tbody></table><p><br></p>");
        else if (/^(row|col)[+-]$/.test(c)) tableOp(c);
        else document.execCommand(c, false, b.dataset.v || null);
        keep();
      });
      ed.addEventListener("paste", (e) => {
        e.preventDefault();
        const html = e.clipboardData.getData("text/html"), text = e.clipboardData.getData("text/plain");
        const box = document.createElement("div");
        if (html) box.innerHTML = html; else box.innerHTML = text.split(/\n{2,}/).map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`).join("");
        document.execCommand("insertHTML", false, sanitize(box).innerHTML);
        keep();
      });
      const keep = () => store.set(key, { base: tpl.dataset.base, html: ed.innerHTML });
      ed.addEventListener("input", keep);
      panel._view = art; art.replaceWith(tb, ed);
      bar.classList.add("editing");
      $(".bar-note", bar).textContent = "Editing. Your draft is kept in this browser until you save or cancel.";
      $(".bar-btns", bar).hidden = true;
      const acts = document.createElement("span"); acts.className = "bar-btns ed-acts";
      acts.innerHTML = '<button class="btn-line ed-cancel" type="button">Cancel</button><button class="btn ed-review" type="button">Review and save</button>';
      bar.appendChild(acts);
      const stop = () => { tb.remove(); ed.replaceWith(panel._view); acts.remove(); bar.classList.remove("editing"); $(".bar-btns", bar).hidden = false; $(".bar-note", bar).textContent = "Formatted for Confluence and Jira"; };
      $(".ed-cancel", acts).addEventListener("click", () => {
        const dirty = toMarkdown(ed.innerHTML) !== toMarkdown(tpl.innerHTML);
        if (dirty && !confirm("Discard your changes to this document?")) return;
        store.set(key, {}); stop();
      });
      $(".ed-review", acts).addEventListener("click", () => review(panel, tpl, ed, key, stop));
      ed.focus();
    }

    function review(panel, tpl, ed, key, stop) {
      const md = toMarkdown(ed.innerHTML), base = toMarkdown(tpl.innerHTML);
      const errs = problems(md), warns = warnings(md), diff = changed(base, md);
      const m = document.createElement("div"); m.className = "modal-wrap";
      m.innerHTML = `<div class="modal" role="dialog" aria-label="Review your edit"><h2>Review your edit</h2>
        <p>${diff.added || diff.removed ? `${diff.added} line${diff.added === 1 ? "" : "s"} added or changed, ${diff.removed} removed.` : "No changes yet."}</p>
        ${errs.map((x) => `<p class="m-err">⚠ ${esc(x)}</p>`).join("")}${warns.map((x) => `<p class="m-warn">${esc(x)}</p>`).join("")}
        <details><summary>Show the Markdown that will be saved</summary><pre class="m-md">${esc(md)}</pre></details>
        <p class="muted small">Saving puts this version in the Mantis inbox. Mantis applies it in the next session; the page here updates then.</p>
        <div class="m-btns"><button class="btn-line m-back" type="button">Keep editing</button><button class="btn m-save" type="button" ${errs.length || !(diff.added || diff.removed) ? "disabled" : ""}>Save to inbox</button></div></div>`;
      document.body.appendChild(m);
      const close = () => m.remove();
      $(".m-back", m).addEventListener("click", close);
      m.addEventListener("click", (e) => { if (e.target === m) close(); });
      $(".m-save", m).addEventListener("click", async () => {
        try {
          if (!served) throw new Error("offline");
          const r = await fetch(assetBase + "api/edits", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: tpl.dataset.path, base: tpl.dataset.base, markdown: md, title: document.title }) });
          const j = await r.json(); if (!r.ok) throw new Error(j.error || "failed");
          store.set(key, {}); close(); stop(); markPending(panel);
          toast("Saved to the inbox. Mantis applies it next session.");
        } catch (e) {
          await copyText(md); close();
          toast("The site server isn't running, so the Markdown was copied instead. Paste it into Claude Code.");
        }
      });
    }

    function markPending(panel) {
      const btn = $(".edit-btn", panel); if (btn) { btn.disabled = true; btn.textContent = "Edit sent"; btn.title = "Waiting for Mantis to apply your last edit"; }
      const note = $(".bar-note", panel); if (note) note.textContent = "Your edit is in the inbox. Mantis applies it next session.";
    }
    document.addEventListener("click", (e) => {
      const b = e.target.closest(".edit-btn"); if (!b || b.disabled) return;
      ensureLibs().then(() => startEdit(b.closest(".tab-panel"))).catch(() => toast("The editor could not load. Is the site served by tools/serve.py?"));
    });
    if (served) fetch(assetBase + "api/edits/pending", { cache: "no-store" }).then((r) => r.json()).then((j) => {
      $$(".edit-src").forEach((t) => { if ((j.pending || []).includes(t.dataset.path)) markPending(t.closest(".tab-panel")); });
    }).catch(() => {});
  }

  // ---- Date picker: any .dp-btn opens a small calendar with quick picks; click it again to close ----
  // The button keeps the chosen date in data-value and fires a bubbling "dp-pick" event (detail = YYYY-MM-DD or "").
  const ISO = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const addDays = (s, n) => { const d = new Date(s + "T12:00"); d.setDate(d.getDate() + n); return ISO(d); };
  const nextDow = (s, dow) => { const d = new Date(s + "T12:00"); d.setDate(d.getDate() + (((dow - d.getDay() + 7) % 7) || 7)); return ISO(d); };
  const dp = (() => {
    let pop = null, owner = null, view = null;
    const close = () => { if (pop) pop.remove(); if (owner) owner.setAttribute("aria-expanded", "false"); pop = owner = null; };
    function draw() {
      const t0 = owner.dataset.today || ISO(new Date()), cur = owner.dataset.value || "", kind = owner.dataset.kind || "when";
      const quick = kind === "due"
        ? [["Today", t0], ["Tomorrow", addDays(t0, 1)], ["This Friday", new Date(t0 + "T12:00").getDay() === 5 ? t0 : nextDow(t0, 5)], ["Next week", nextDow(t0, 1)], ["No due date", ""]]
        : [["Today", t0], ["Tomorrow", addDays(t0, 1)], ["Next Monday", nextDow(t0, 1)], ["In a week", addDays(t0, 7)]];
      const first = new Date(view), lead = (first.getDay() + 6) % 7, days = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
      let cells = "";
      for (let i = 0; i < lead; i++) cells += "<span></span>";
      for (let d = 1; d <= days; d++) {
        const v = ISO(new Date(first.getFullYear(), first.getMonth(), d)), past = kind === "when" && v < t0;
        cells += `<button type="button" data-d="${v}" class="${v === t0 ? "is-today" : ""}${v === cur ? " is-on" : ""}" ${past ? "disabled" : ""}>${d}</button>`;
      }
      pop.innerHTML = `<div class="dp-quick">${quick.map(([l, v]) => `<button type="button" data-d="${v}" class="${v === cur ? "is-on" : ""}"><span>${l}</span><small>${v ? new Date(v + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : ""}</small></button>`).join("")}</div>
        <div class="dp-cal"><div class="dp-head"><button type="button" data-nav="-1" aria-label="Previous month">‹</button><b>${first.toLocaleDateString(undefined, { month: "long", year: "numeric" })}</b><button type="button" data-nav="1" aria-label="Next month">›</button></div>
        <div class="dp-grid">${["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((w) => `<i>${w}</i>`).join("")}${cells}</div></div>`;
    }
    function open(btn) {
      if (owner === btn) { close(); return; }
      close(); owner = btn; btn.setAttribute("aria-expanded", "true");
      view = new Date((btn.dataset.value || btn.dataset.today || ISO(new Date())) + "T12:00"); view.setDate(1);
      pop = document.createElement("div"); pop.className = "dp"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Pick a date");
      document.body.appendChild(pop); draw();
      const start = $(".dp-grid .is-on", pop) || $(".dp-grid .is-today", pop) || $(".dp-grid button:not(:disabled)", pop);
      if (start && btn.matches(":focus-visible")) start.focus();   // keyboard users land on the current day
      const r = btn.getBoundingClientRect(), w = pop.offsetWidth || 420;
      pop.style.top = `${scrollY + r.bottom + 8}px`;
      pop.style.left = `${Math.max(8, Math.min(scrollX + r.left, scrollX + document.documentElement.clientWidth - w - 8))}px`;
    }
    document.addEventListener("click", (e) => {
      const b = e.target.closest(".dp-btn");
      if (b) { e.preventDefault(); open(b); return; }
      if (!pop || !pop.contains(e.target)) { if (pop) close(); return; }
      const nav = e.target.closest("[data-nav]");
      if (nav) { view.setMonth(view.getMonth() + +nav.dataset.nav); draw(); return; }
      const d = e.target.closest("[data-d]");
      if (d && !d.disabled) { const btn = owner; btn.dataset.value = d.dataset.d; close(); btn.dispatchEvent(new CustomEvent("dp-pick", { bubbles: true, detail: d.dataset.d })); btn.focus(); }
    });
    document.addEventListener("keydown", (e) => {
      if (!pop) return;
      if (e.key === "Escape") { const b = owner; close(); b.focus(); return; }
      const cur = document.activeElement && document.activeElement.closest(".dp-grid [data-d]");
      const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
      if (!step) return;
      e.preventDefault();
      if (!cur) { const f = $(".dp-grid button:not(:disabled)", pop); if (f) f.focus(); return; }
      const want = addDays(cur.dataset.d, step), d = new Date(want + "T12:00");
      if (d.getMonth() !== view.getMonth() || d.getFullYear() !== view.getFullYear()) { view = new Date(want + "T12:00"); view.setDate(1); draw(); }
      const next = $(`.dp-grid [data-d="${want}"]:not(:disabled)`, pop); if (next) next.focus();
    });
    window.addEventListener("resize", close);
    return { close };
  })();

