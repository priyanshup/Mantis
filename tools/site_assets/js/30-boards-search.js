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
    const cls = { none: "s-none", discovery: "s-disc", refinement: "s-ref", build: "s-build", live: "s-done" };
    const order = ["none", "discovery", "refinement", "build", "live"];
    const prio = { P1: 1, P2: 2, P3: 3 };
    const st = { q: "", status: "all", prio: "all", view: "board", sort: "prio", asc: true };
    $("#f-status").dataset.k = "status"; $("#f-prio").dataset.k = "prio";
    const pp = (p) => (p ? pill(p, "p-" + p.toLowerCase()) : "");
    const href = (i) => i.url || `features/${i.slug}.html`;
    const visible = () => {
      const q = (st.q || "").trim().toLowerCase();
      return items.filter((i) => (st.status === "all" || i.status === st.status) && (st.prio === "all" || i.priority === st.prio) &&
        (!q || (i.title + " " + i.summary).toLowerCase().includes(q)));
    };
    const facts = (i) => !i.slug ? "" : `<div class="facts"><span>${i.epics ? `Epic${i.epics > 1 ? "s" : ""} <b>${i.epics}</b>` : "No epic"}</span><span>Stories <b>${i.storiesDone}/${i.stories}</b></span>` +
      (i.open ? `<span><b>${i.open}</b> open question${i.open > 1 ? "s" : ""}</span>` : "") + (i.jira && i.jira !== "none" ? `<span>${esc(i.jira)}</span>` : "") + `</div>`;
    const tile = (i) => i.slug
      ? `<a class="tile st-${i.status || "none"}" href="${href(i)}"><h3><span>${esc(i.title)}</span>${pp(i.priority)}</h3>${i.type === "workstream" ? '<span class="tag">Platform workstream</span>' : ""}<p>${esc(i.summary)}</p>${facts(i)}</a>`
      : `<div class="tile ghost"><h3><span>${esc(i.title)}</span></h3><p>${esc(i.summary)}</p></div>`;
    const byPrio = (a, b) => (prio[a.priority] || 9) - (prio[b.priority] || 9) || a.title.localeCompare(b.title);
    const draw = () => {
      const v = visible();
      if (st.view === "board") {
        let out;
        if (st.status !== "all") {
          const xs = v.sort(byPrio);
          out = `<h2 class="section-h">${pill(labels[st.status], cls[st.status])} <span class="muted">${xs.length}</span></h2><div class="later">${xs.map(tile).join("") || '<p class="empty">Nothing here with these filters.</p>'}</div>`;
        } else {
          out = `<div class="board">` + ["discovery", "refinement", "build", "live"].map((s) => {
            const xs = v.filter((i) => i.status === s).sort(byPrio);
            return `<div class="col st-${s}"><div class="col-h">${pill(labels[s], cls[s])}<span class="n">${xs.length}</span></div>${xs.map(tile).join("") || `<p class="empty">${s === "live" ? "A topic moves here when it goes live." : "Nothing here."}</p>`}</div>`;
          }).join("") + `</div>`;
          const later = v.filter((i) => i.status === "none");
          if (later.length) out += `<h2 class="section-h">${pill(labels.none, cls.none)} <span class="muted">${later.length} on the roadmap with no detail yet</span></h2><div class="later">${later.map(tile).join("")}</div>`;
        }
        $("#board").innerHTML = out;
      } else {
        const keys = { prio: (i) => prio[i.priority] || 9, title: (i) => i.title.toLowerCase(), status: (i) => order.indexOf(i.status), epics: (i) => i.epics, stories: (i) => i.stories, open: (i) => i.open, updated: (i) => i.updated };
        $("#list").innerHTML = table([["title", "Topic"], ["prio", "Priority"], ["status", "Status"], ["epics", "Epics"], ["stories", "Stories"], ["open", "Open questions"], ["", "Jira"], ["updated", "Updated"]],
          sortBy(v, keys, st).map((i) => `<tr><td>${i.slug ? `<a href="${href(i)}">${esc(i.title)}</a>` : esc(i.title)}${i.type === "workstream" ? ' <span class="tag">Workstream</span>' : ""}</td><td>${pp(i.priority) || "–"}</td><td>${pill(labels[i.status], cls[i.status])}</td>` +
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

  // ---- Search across all of Mantis (IMP-006); index built with the site, searched here ----
  const gs = $("#gsearch"), gr = $("#gresults");
  if (gs) {
    const base = gs.dataset.base || "";
    let idx = null, sel = -1;
    const load = () => idx ? Promise.resolve(idx) : fetch(base + "search.json").then((r) => r.json()).then((d) => (idx = d)).catch(() => (idx = []));
    const norm = (s) => s.toLowerCase();
    const snip = (x, terms) => {
      const l = norm(x); let i = Math.max(0, ...terms.map((t) => l.indexOf(t)).filter((n) => n >= 0).slice(0, 1));
      const s = Math.max(0, i - 60), out = (s ? "…" : "") + x.slice(s, s + 170) + (x.length > s + 170 ? "…" : "");
      return terms.reduce((h, t) => h.replace(new RegExp("(" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), "<mark>$1</mark>"), esc(out));
    };
    function run() {
      const q = gs.value.trim(); sel = -1;
      if (q.length < 2) { gr.hidden = true; return; }
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
        const top = hits.slice(0, 14).map(([, r]) => r);
        gr.innerHTML = top.length ? top.map((r, i) => {
          const inner = `<span class="gr-k">${esc(r.k)}</span><span class="gr-t">${esc(r.t)}</span>${r.w ? `<span class="gr-w">${esc(r.w)}</span>` : ""}` +
            (r.x ? `<span class="gr-x">${snip(r.x, terms)}</span>` : "");
          return r.p ? `<a class="gr" data-i="${i}" href="${base}${r.u}" data-person="${esc(r.p)}">${inner}</a>` : r.u ? `<a class="gr" data-i="${i}" href="${base}${r.u}">${inner}</a>` : `<div class="gr gr-src" data-i="${i}">${inner}</div>`;
        }).join("") + (hits.length > 14 ? `<p class="gr-more">${hits.length - 14} more: add a word to narrow it down.</p>` : "")
          : `<p class="gr-more">Nothing found for "${esc(q)}".</p>`;
        gr.hidden = false;
      });
    }
    gs.addEventListener("input", run);
    gs.addEventListener("focus", () => { load(); if (gs.value.trim().length > 1) run(); });
    gs.addEventListener("keydown", (e) => {
      const links = $$(".gr", gr);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); sel = Math.max(0, Math.min(links.length - 1, sel + (e.key === "ArrowDown" ? 1 : -1)));
        links.forEach((l, i) => l.classList.toggle("on", i === sel));
      } else if (e.key === "Enter" && links[Math.max(sel, 0)] && links[Math.max(sel, 0)].href) {
        e.preventDefault(); links[Math.max(sel, 0)].click(); gr.hidden = true;   // a person opens their panel (see the drawer)
      } else if (e.key === "Escape") { gr.hidden = true; gs.blur(); }
    });
    document.addEventListener("click", (e) => { if (!e.target.closest(".gsearch")) gr.hidden = true; });
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); gs.focus(); }
    });
  }

