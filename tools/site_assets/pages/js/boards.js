/* boards: list and board machinery, and the Epics and stories board. */
Mantis.define("boards", ["core"], (m_core) => {
  const { store, $$, $, esc, pill, toast } = m_core;
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
});
