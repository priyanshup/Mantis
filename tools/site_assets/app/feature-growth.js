/* feature-growth.js: the Growth tab's actions. The server holds the record (tools/growth.py); this file only asks it to change and redraws.
   Add selected: take an opportunity or confirm a past win. Not now: set aside for a while, it comes back by itself. Dismiss: decline,
   restorable for a while, never proposed again. Select all toggles. Bring back and Restore live on the Hidden tab. */
(() => {
  const growth = () => window.__LIVE.growth || {};
  const area = (name) => ((growth().framework || {}).areas || []).find((a) => a.name === name);
  const redraw = async () => { await Live.refresh(["growth"], {}, { redraw: false }); refreshG(); const g = $("#ghead"); if (g) g.innerHTML = gHead(); };
  const selected = () => [...ST.gsel].map((i) => GROWD[i]).filter(Boolean);
  const run = async (items, body) => {   // one request each, so one failure does not lose the rest
    let ok = 0; const fails = [];
    for (const it of items) { try { await Api.post("api/growth", body(it)); ok++; } catch (e) { fails.push(`${it.title.slice(0, 40)}: ${e.message}`); } }
    return { ok, fails };
  };
  const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
  const report = (res, done, undo) => { if (res.fails.length) toast(res.fails[0] + (res.fails.length > 1 ? ` (and ${res.fails.length - 1} more)` : "")); else if (res.ok) toast(done(res.ok), undo); };
  const act = async (items, body, done, undo) => { const res = await run(items, body); ST.gsel.clear(); await redraw(); report(res, done, res.ok ? undo(items) : null); };
  const quietly = (fn) => () => fn().then(redraw).catch((e) => toast(e.message));

  Live.onRefresh(() => ST.gsel.clear());

  UI.action("growth-select-all", (el) => {
    const L = gLists(), list = (gGroups(L).find(([k]) => k === el.dataset.group) || [, []])[1];
    const every = list.every((x) => ST.gsel.has(x.i)); list.forEach((x) => (every ? ST.gsel.delete(x.i) : ST.gsel.add(x.i)));
    $("#glist").innerHTML = gListHtml();
  });
  UI.action("growth-add-selected", () => act(selected(), (it) => (it.past ? { action: "confirm", id: it.id, outcome: "" } : { action: "take", id: it.id }),
    (n) => `${plural(n, "entry")} added to your record.`, () => null));
  UI.action("growth-later", () => {
    const days = growth().hold_days || 14;
    return act(selected(), (it) => ({ action: "hold", id: it.id }), (n) => `${plural(n, "proposal")} set aside for ${days} days. They come back on their own; see Hidden.`,
      (items) => quietly(() => run(items, (it) => ({ action: "unhold", id: it.id }))));
  });
  const dismiss = (items) => act(items, (it) => ({ action: "dismiss", id: it.id }), (n) => `${plural(n, "proposal")} dismissed. Mantis will not propose ${n === 1 ? "it" : "them"} again. Kept in Hidden for ${growth().declined_days || 30} days.`,
    (its) => quietly(() => run(its, (it) => ({ action: "restore", item: { id: it.id, title: it.title, kind: it.kind, state: "proposed", past: it.past, why: it.why } }))));
  UI.action("growth-dismiss-selected", () => dismiss(selected()));
  UI.action("growth-dismiss", (el) => dismiss(GROWD.filter((x) => x.id === el.dataset.id)));
  UI.action("growth-unhold", (el) => act(GROWD.filter((x) => x.id === el.dataset.id), (it) => ({ action: "unhold", id: it.id }), () => "Back in Proposed.", () => null));
  UI.action("growth-restore", (el) => { const d = DECLINED.find((x) => x.id === el.dataset.id); if (!d) return; return act([d], (it) => ({ action: "restore", item: it.item }), () => "Restored to Proposed.", () => null); });
  UI.action("growth-add", async () => {
    readForm(); const f = ST.gform, title = (f.title || "").trim();
    if (!title) { toast("Say what it is first"); const t = $("#gtitle"); if (t) t.focus(); return; }
    const a = area([...f.areas][0]), learnt = f.kind === "Learned", win = f.kind === "Win" || learnt, why = [f.why, !win && f.when ? `Planned: ${f.when}` : ""].filter(Boolean).join(" ");
    await Api.post("api/growth", { action: "add", item: { title, kind: f.kind === "Learning" || learnt ? "learning" : "contribution", state: win ? "done" : "open", past: win, why, outcome: win ? why : "", areas: a ? [a.key] : [] } });
    ST.gv = win ? "Done" : "In progress"; f.title = ""; f.why = ""; f.areas = new Set();
    await redraw(); const form = $("#gform"); if (form) form.innerHTML = gFormHtml(); toast(win ? "Added to your record" : "Added as a goal");
  });
})();
