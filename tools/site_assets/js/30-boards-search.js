  // ---- Shared board/list machinery ----
  function board(opts) {
    const { items, key, st, draw } = opts;
    const fromHash = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
    Object.assign(st, store.get(key), fromHash);
    const sync = () => {
      $$(".chips").forEach((g) => $$("button", g).forEach((b) => b.classList.toggle("on", b.dataset.v === (st[g.dataset.k] || "all"))));
      $$("#view button").forEach((b) => b.classList.toggle("on", b.dataset.v === st.view));
      $("#board").hidden = st.view !== "board"; $("#list").hidden = st.view !== "list";
      const tv = $("#tl-view");   // Roadmap's Timeline view (IMP-068): its own legend and controls, so the filters step aside
      if (tv) { tv.hidden = st.view !== "timeline"; const tools = $("#rd-tools"); if (tools) tools.hidden = st.view === "timeline"; }
      const h = new URLSearchParams(); Object.keys(st).forEach((k) => st[k] && st[k] !== "all" && !["sort", "asc"].includes(k) && h.set(k, st[k]));
      history.replaceState(null, "", "#" + h.toString());
      store.set(key, { view: st.view });
      draw();
    };
    $$(".chips").forEach((g) => g.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { st[g.dataset.k] = b.dataset.v; sync(); } }));
    $("#view").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { st.view = b.dataset.v; sync(); } });
    $("#q").value = st.q || "";
    $("#q").addEventListener("input", (e) => { st.q = e.target.value; sync(); });
    $("#list").addEventListener("click", (e) => { const t = e.target.closest("th[data-k]"); if (t) { st.asc = st.sort === t.dataset.k ? !st.asc : true; st.sort = t.dataset.k; sync(); } });
    return sync;
  }
  function table(cols, rows, st) {
    const th = (k, n) => k ? `<th data-k="${k}" class="${st.sort === k ? "sorted" + (st.asc ? " asc" : "") : ""}">${n}</th>` : `<th>${n}</th>`;
    return `<section class="panel-box"><div class="tbl"><table class="list-t"><thead><tr>${cols.map(([k, n]) => th(k, n)).join("")}</tr></thead><tbody>${rows.join("") || `<tr><td colspan="${cols.length}" class="muted">Nothing matches these filters.</td></tr>`}</tbody></table></div></section>`;
  }
  function sortBy(rows, keys, st) {
    const k = keys[st.sort] || keys.title;
    return [...rows].sort((a, b) => (k(a) < k(b) ? -1 : k(a) > k(b) ? 1 : a.title.localeCompare(b.title)) * (st.asc === false ? -1 : 1));
  }

  // ---- Roadmap ----
  const rd = $("#data");
  if (rd) {
    const { items, labels } = JSON.parse(rd.textContent);
    const order = ["none", "discovery", "refinement", "build", "live"];
    const prio = { P1: 1, P2: 2, P3: 3 };
    const st = { q: "", status: "all", prio: "all", view: "board", sort: "prio", asc: true, work: store.get("mantis-features").work || "all" };
    $("#f-status").dataset.k = "status"; $("#f-prio").dataset.k = "prio";   // the type chips (#t-work, data-k "work") sit above the tabs
    const href = (i) => i.url || `features/${i.slug}.html`;
    const visible = () => {
      const q = (st.q || "").trim().toLowerCase();
      return items.filter((i) => (st.status === "all" || i.status === st.status) && (st.prio === "all" || i.priority === st.prio) && (!i.slug || workMatch(i.work, st.work)) &&
        (!q || (i.title + " " + i.summary).toLowerCase().includes(q)));
    };
    // A roadmap card (2026-10-31 redesign): the name, two lines of summary, then one mono line of facts
    const facts = (i) => [i.priority, i.jira && i.jira !== "none" ? i.jira : "", i.open ? `${i.open} question${i.open > 1 ? "s" : ""}` : "",
      i.stories ? `${i.storiesDone}/${i.stories} stories in Jira` : ""].filter(Boolean).join(" · ");
    const tile = (i) => i.slug
      ? `<a class="rd-card" href="${href(i)}"><span class="rd-t">${esc(i.title)}</span><span class="rd-s">${esc(i.summary)}</span>${i.workTag || ""}<span class="rd-m">${esc(facts(i))}</span></a>`
      : `<div class="rd-card ghost"><span class="rd-t">${esc(i.title)}</span><span class="rd-s">${esc(i.summary)}</span></div>`;
    const stageH = (s, n) => `<p class="rd-h"><span class="st st-${s}">${esc(labels[s])}</span><span class="n">${n}</span></p>`;
    const byPrio = (a, b) => (prio[a.priority] || 9) - (prio[b.priority] || 9) || a.title.localeCompare(b.title);
    const draw = () => {
      const v = visible();
      if (st.view === "board") {
        let out;
        if (st.status !== "all") {
          const xs = v.sort(byPrio);
          out = stageH(st.status, xs.length) + `<div class="rd-grid">${xs.map(tile).join("") || '<p class="empty">Nothing here with these filters.</p>'}</div>`;
        } else {
          out = `<div class="rd-board">` + ["discovery", "refinement", "build", "live"].map((s) => {
            const xs = v.filter((i) => i.status === s).sort(byPrio);
            return `<div class="rd-col">${stageH(s, xs.length)}${xs.map(tile).join("") || `<p class="rd-empty">${s === "live" ? "Nothing live yet." : "Nothing here."}</p>`}</div>`;
          }).join("") + `</div>`;
          const later = v.filter((i) => i.status === "none");
          if (later.length) out += `<p class="grp-l rd-later-h">Not started · ${later.length} on the roadmap with no detail yet</p><div class="rows">` +
            later.map((i) => `<div class="row"><span class="row-t">${esc(i.title)}</span><span class="f-sum rd-later-s">${esc(i.summary)}</span></div>`).join("") + "</div>";
        }
        $("#board").innerHTML = out;
      } else {
        const keys = { work: (i) => i.work || "z", prio: (i) => prio[i.priority] || 9, title: (i) => i.title.toLowerCase(), status: (i) => order.indexOf(i.status), epics: (i) => i.epics, stories: (i) => i.stories, open: (i) => i.open, updated: (i) => i.updated };
        $("#list").innerHTML = table([["title", "Topic"], ["work", "Type"], ["prio", "Priority"], ["status", "Status"], ["epics", "Epics"], ["stories", "Stories"], ["open", "Open questions"], ["", "Jira"], ["updated", "Updated"]],
          sortBy(v, keys, st).map((i) => `<tr><td>${i.slug ? `<a href="${href(i)}">${esc(i.title)}</a>` : esc(i.title)}</td><td>${{ business: "Business", technical: "Technical", both: "Both" }[i.work] || "–"}</td><td>${esc(i.priority) || "–"}</td><td><span class="st st-${i.status}">${esc(labels[i.status])}</span></td>` +
            `<td>${i.slug ? i.epics : "–"}</td><td>${i.slug ? i.storiesDone + "/" + i.stories : "–"}</td><td>${i.open || "–"}</td><td>${i.jira && i.jira !== "none" ? esc(i.jira) : "–"}</td><td class="muted">${esc(i.updated) || "–"}</td></tr>`), st);
      }
    };
    board({ items, key: "mantis-roadmap", st, draw })();
  }

  // ---- Epics & stories ----
  const wd = $("#work");
  if (wd) {
    const { items, labels } = JSON.parse(wd.textContent);
    const wcls = { draft: "w-draft", review: "w-review", "in-jira": "w-jira", done: "w-done" };
    const order = ["draft", "review", "in-jira", "done"];
    const st = { q: "", kind: "all", feature: "all", view: "board", sort: "status", asc: true };
    $("#f-kind").dataset.k = "kind";
    const sel = $("#f-feature");
    const visible = () => {
      const q = (st.q || "").trim().toLowerCase();
      const f = st.feature, inScope = (i) => f === "archived" ? i.archived : !i.archived && (f === "all" || (f === "mine" ? i.mine : i.feature === f));
      return items.filter((i) => inScope(i) && (st.kind === "all" || i.kind === st.kind) &&
        (!q || (i.title + " " + i.feature_title + " " + i.epic_title).toLowerCase().includes(q)));
    };
    const where = (i) => i.kind === "epic" ? (i.feature_title || "Generic epic") : [i.feature_title, i.epic_title ? "Epic: " + i.epic_title : "Not in an epic"].filter(Boolean).join(" · ");
    const kind = (i) => i.kind === "epic" ? '<span class="kind k-epic">◆ Epic</span>' : '<span class="kind k-story">▤ Story</span>';
    // Each card can be archived on its own; one archived only because its topic is, is restored from Topics.
    const arcBtn = (i) => i.topicArc ? "" : `<button type="button" class="tile-x nocopy" data-work="${esc(i.file)}" data-on="${i.own ? 1 : 0}" title="${i.own ? "Restore to the board" : "Archive: hide it from the board"}">${i.own ? "Restore" : "Archive"}</button>`;
    const card = (i) => `<div class="tile-wrap"><a class="tile wk-${i.kind}" href="${i.href}">${kind(i)}<h3><span>${esc(i.title)}</span></h3>${where(i) && where(i) !== i.title ? `<p>${esc(where(i))}</p>` : ""}` +
      `<div class="facts">${i.jira && i.jira !== "none" ? `<span>${esc(i.jira)}</span>` : ""}${i.updated ? `<span>${esc(i.updated)}</span>` : ""}${i.topicArc ? "<span>Topic archived</span>" : ""}</div></a>${arcBtn(i)}</div>`;
    const draw = () => {
      sel.value = st.feature;
      const v = visible();
      if (st.view === "board") {
        $("#board").innerHTML = `<div class="board">` + order.map((s) => {
          const xs = v.filter((i) => i.status === s).sort((a, b) => (a.kind === "epic" ? 0 : 1) - (b.kind === "epic" ? 0 : 1) || a.title.localeCompare(b.title));
          return `<div class="col"><div class="col-h">${pill(labels[s], wcls[s])}<span class="n">${xs.length}</span></div>${xs.map(card).join("") || '<p class="empty">Nothing here.</p>'}</div>`;
        }).join("") + `</div>` + (items.length ? "" : '<p class="empty">No epics or stories yet. Ask Mantis in VS Code to write one.</p>');
      } else {
        const keys = { title: (i) => i.title.toLowerCase(), kind: (i) => i.kind, status: (i) => order.indexOf(i.status), feature: (i) => i.feature_title, updated: (i) => i.updated };
        $("#list").innerHTML = table([["title", "Title"], ["kind", "Type"], ["status", "Status"], ["feature", "Topic and epic"], ["", "Jira"], ["updated", "Updated"]],
          sortBy(v, keys, st).map((i) => `<tr><td><a href="${i.href}">${esc(i.title)}</a></td><td>${kind(i)}</td><td>${pill(labels[i.status] || i.status, wcls[i.status] || "w-draft")}</td>` +
            `<td>${esc(where(i))}</td><td>${i.jira && i.jira !== "none" ? esc(i.jira) : "–"}</td><td class="muted">${esc(i.updated) || "–"}</td></tr>`), st);
      }
    };
    items.forEach((i) => (i.topicArc = i.archived && !i.own));   // archived because its topic is
    const sync = board({ items, key: "mantis-work", st, draw });
    async function archiveWork(file, on) {
      const r = await fetch("api/focus", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ slug: file, action: (on ? "un" : "") + "archive-work" }) });
      if (!r.ok) throw new Error((await r.json()).error);
      const i = items.find((x) => x.file === file); i.own = !on; i.archived = i.own || i.topicArc; sync();
    }
    $("#board").addEventListener("click", async (e) => {
      const b = e.target.closest(".tile-x"); if (!b) return;
      e.preventDefault();
      const file = b.dataset.work, on = b.dataset.on === "1";
      try {
        await archiveWork(file, on);
        toast(on ? "Restored to the board." : "Archived. Find it under Archived.", () => archiveWork(file, !on).catch(() => toast("Could not undo: is the site server running?")));
      } catch (err) { toast("Could not save: is the site running through tools/serve.py?"); }
    });
    sel.addEventListener("change", () => { st.feature = sel.value; sync(); });
    sync();
  }

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
      const d = e.target.closest("[data-dopen]"); if (d) { closePalette(); openDrawer(d.dataset.dopen); }
    });
    const kb = $("#kbar"); if (kb) kb.addEventListener("click", openPalette);
    document.addEventListener("keydown", (e) => {
      const typing = /input|textarea|select/i.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
      if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); pal.hidden ? openPalette() : closePalette(); }
      else if (e.key === "/" && !typing && pal.hidden) { e.preventDefault(); openPalette(); }
    });
  }

