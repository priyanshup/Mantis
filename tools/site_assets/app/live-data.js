/* live.js (2026-11-11): runs after the mock's app files and before its first screen. It fills the mock's data from window.__LIVE
   (the live endpoints and static.json), defines the few screens that need live content, and saves changes through the live APIs. */
var LV = {};
/* The data build is a function so a save can re-read part of the server's data and run it again (Live.refresh in platform.js). */
window.rebuildLive = function () {
  const L = window.__LIVE || {};
  const T = L.tasks || { today: REAL.today, tasks: [], groups: [], suggestions: { items: [] }, dismissed: [], rev: 0 };
  const X = L.extra || { meetings: [], followups: {}, people: [] };
  const S0 = L.stat || { features: [], questions: [], recent: [], health: [], docs: 0, topics: 0, built: "" };
  const today = T.today || REAL.today;
  try { ST.flat = localStorage.getItem('mantis-flat') === '1'; } catch (e) {}
  const D = (s) => new Date(s + "T12:00:00");
  const isoOf = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const plus = (s, n) => { const d = D(s); d.setDate(d.getDate() + n); return isoOf(d); };
  const day = (s) => `${D(s).getDate()} ${MONTHS[D(s).getMonth()]}`;
  const when = (s) => { if (!s) return ""; const d = new Date(s); return `${d.getDate()} ${MONTHS[d.getMonth()]}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
  const plural = (n, a, b) => `${n} ${n === 1 ? a : (b || a + "s")}`;
  const mut = (arr, items) => { arr.length = 0; arr.push(...items); };

  // ---- the week ----
  const WK = ["Mon", "Tue", "Wed", "Thu", "Fri"];
  const dow = (D(today).getDay() + 6) % 7, mon = plus(today, -dow + (dow > 4 ? 7 : 0)), weekDates = [0, 1, 2, 3, 4].map((i) => plus(mon, i));
  window.TODAY_D = WK[Math.min(dow, 4)];
  Object.keys(DATES).forEach((k) => delete DATES[k]); WK.forEach((d, i) => (DATES[d] = day(weekDates[i])));

  // ---- tasks: what is on today's list, in the mock's shape; LV.ids says which live task each one is ----
  const groups = {}; (T.groups || []).forEach((g) => (groups[g.id] = g));
  const openT = (t) => t.status === "todo" || t.status === "blocked";
  const mine = T.tasks.filter((t) => openT(t) && (!t.day || t.day <= today)).sort((a, b) => (a.order || 0) - (b.order || 0));
  LV.ids = mine.map((t) => t.id); LV.base = JSON.parse(JSON.stringify(T)); LV.rev = T.rev;
  mut(REAL.tasks, mine.map((t) => ({ t: t.title, p: t.priority || "none", g: (groups[t.group] || {}).name || "Other tasks", due: t.due || "", ask: t.contact || "", n: (t.comments || []).map((c) => c.text).join(" ").slice(0, 420), est: t.estimate || 0, rem: t.remind_on || "", src: t.source || "" })));
  const doneOn = (d) => T.tasks.filter((t) => t.status === "done" && t.done_at === d).length;
  mut(EXTRA.week, weekDates.map((d) => ({ d, due: 0, done: doneOn(d) })));
  EXTRA.carried = mine.filter((t) => t.day && t.day < today).length;
  mut(EXTRA.sugg, ((T.suggestions || {}).items || []).map((s) => ({ id: s.id, t: s.title, why: (s.why || "").slice(0, 150), say: (s.say || "").slice(0, 320), p: s.priority || "", min: s.estimate || 0 })));
  const doneAll = T.tasks.filter((t) => t.status === "done").sort((a, b) => (b.done_at || "").localeCompare(a.done_at || ""));
  EXTRA.archN = doneAll.length; mut(EXTRA.arch, doneAll.slice(0, 6).map((t) => ({ t: t.title, d: t.done_at || "" })));

  // ---- meetings: this week's occurrences ----
  const now = new Date(), meetings = [];
  (X.meetings || []).forEach((m) => {
    if (!m.next || !m.time) return;
    const nx = D(m.next), idx = (nx.getDay() + 6) % 7; if (idx > 4) return;
    const diff = Math.round((D(weekDates[idx]) - nx) / 864e5); if (diff % (7 * (m.every || 1)) !== 0) return;
    const ag = [];
    (m.agenda || []).forEach((s) => s.items.forEach((it) => ag.push([it.text, (it.note || "").replace(/\s*\([^)]*\)\s*$/, "")])));
    meetings.push({ d: WK[idx], date: weekDates[idx], n: m.name, t: m.time, w: m.attendees || [], why: m.purpose || "", ag, key: m.key, id: m.id, at: new Date(weekDates[idx] + "T" + m.time + ":00") });
  });
  meetings.sort((a, b) => a.at - b.at);
  const nextM = meetings.find((m) => m.at >= now); if (nextM) nextM.next = true;
  mut(MEET, meetings); LV.nextM = nextM;

  // ---- who we are waiting on ----
  const fu = X.followups || {};
  Object.keys(WANT).forEach((k) => delete WANT[k]);
  Object.entries(fu).forEach(([name, v]) => {
    const w = (v.items || []).filter((i) => i.status === "open" && i.kind === "wait"); if (!w.length) return;
    const since = Math.max(...w.map((i) => Math.round((D(today) - D(i.created || today)) / 864e5)));
    WANT[name] = { since: plural(since, "day"), n: since, items: w.map((i) => i.topic) };
  });
  const wantSorted = Object.entries(WANT).sort((a, b) => b[1].n - a[1].n); Object.keys(WANT).forEach((k) => delete WANT[k]); wantSorted.forEach(([k, v]) => (WANT[k] = v));
  mut(PEOPLE, (X.people || []).slice(0, 40).map((p) => ({ name: p.name, role: p.role || p.team || "", waiting: (WANT[p.name] || {}).items ? WANT[p.name].items.length : 0 })));
  Object.keys(NEXTM).forEach((k) => delete NEXTM[k]);
  meetings.forEach((m) => (m.w || []).forEach((p) => { if (!NEXTM[p] && m.at >= now) NEXTM[p] = `${m.n}, ${m.d} ${m.t}`; }));
  NEXTM["You"] = "Yours to settle";

  // ---- what changed (the last pull) ----
  const brief = (L.brief || {}).last, filters = (L.filters || {}).filters || [];
  const feat = {}; (S0.features || []).forEach((f) => (feat[f.slug] = f));
  const short = (t) => String(t || "").replace(/\s*\([^)]*\)\s*$/, "").split(":")[0];
  const overdueG = new Set(mine.filter((t) => t.due && t.due < today && t.group && groups[t.group]).map((t) => groups[t.group].card));
  mut(TOPICS, ((brief || {}).cards || []).filter((c) => !c.lines.every((l) => /^(no (real |new )?change|nothing (changed|new))/i.test(l.trim()))).slice(0, 8).map((c) => ({
    t: short(c.title), s: c.lines[0] || "", tag: ["Discovery", "Refinement", "Build"][(feat[c.slug] || {}).stage] || "", hot: overdueG.has(c.slug), more: c.lines.slice(1).join(" ") || c.lines[0] || "", slug: c.slug })));
  LV.pullAt = brief ? when(brief.at) : "";
  const cnt = (type, k) => filters.filter((f) => f.type === type).reduce((a, f) => a + ((f.last_counts || {})[k] || 0), 0);
  LV.counts = { jn: cnt("jira", "new"), jc: cnt("jira", "changed"), cn: cnt("confluence", "new"), cc: cnt("confluence", "changed") };

  // ---- features and the questions about them ----
  mut(FEATS, (S0.features || []).filter((f) => f.following && !f.archived).map((f) => ({ title: short(f.title), stage: f.stage, priority: f.priority, sources: f.sources, slug: f.slug })));
  LV.nFeat = FEATS.length; LV.nTopics = S0.topics || 0; LV.featSub = `${plural(FEATS.length, "feature")} you follow.`;
  const hashMeet = {};
  (X.meetings || []).forEach((m) => (m.agenda || []).forEach((s) => s.items.forEach((it) => { const k = ((it.href || "").match(/#k=([0-9a-f]+)/) || [])[1]; if (k && !hashMeet[k]) hashMeet[k] = m.name; })));
  const pend = new Set(((L.pending || {}).pending) || []);
  mut(QALL, (S0.questions || []).map((q) => ({ q: q.q, who: q.who, feat: q.feat, pri: q.pri, meet: hashMeet[q.k] || "Not on an agenda" })));
  mut(QCTX, (S0.questions || []).map((q) => [q.ctx || "", q.src.length ? q.src : ["Open item"]]));
  LV.qIds = (S0.questions || []).map((q) => q.id);
  (S0.questions || []).forEach((q, i) => { if (pend.has(q.id)) ST.ans[i] = "Sent earlier"; });
  QOPT.who = ["Anyone", ...new Set(QALL.map((q) => q.who))]; QOPT.feat = ["All features", ...new Set(QALL.map((q) => q.feat))];
  const youN = QALL.filter((q) => q.who === "You").length, otherN = QALL.length - youN;
  LV.qHead = `<b>${plural(youN, "question is", "questions are")} yours to answer.</b> ${otherN} more ${otherN === 1 ? "sits" : "sit"} with other people.`;
  TABS.find((t) => t[0] === "questions")[2] = youN || undefined;

  // ---- sources ----
  mut(FILT, filters.map((f) => ({ label: f.label, kind: f.type === "jira" ? "Jira" : "Confluence", found: f.last_counts ? `${f.last_counts.new || 0} new · ${f.last_counts.changed || 0} changed` : "not run yet", on: !!f.active, id: f.id })));
  mut(RECENT, (S0.recent || []).map((r) => ({ title: r.title, kind: r.kind, feat: r.feat, date: r.date })));
  const pb = (L.brief || {}).pending || {};
  LV.inboxN = pb.files || 0;
  LV.pullLine = brief ? `Last pull ${LV.pullAt}: <b class="u-c-ink">${LV.counts.jn + LV.counts.cn} new</b>, ${LV.counts.jc + LV.counts.cc} changed. ${LV.inboxN ? `<button class="link" data-inbox>${plural(LV.inboxN, "file is", "files are")} waiting in the inbox.</button>` : "Nothing waiting in the inbox."}` : "No pull yet.";
  const health = S0.health || [];
  LV.healthHtml = health.length ? `<div class="hist rise" style="--i:3"><button class="gh hh" data-hh><span class="pulse"></span><span class="nm">${plural(health.length, "thing needs", "things need")} a look</span>${CHEV}</button><div class="acc"><div class="in"><ul class="rows">${health.map((h) => `<li><span class="t">${esc(h)}</span></li>`).join("")}</ul></div></div></div>` : "";

  // ---- growth ----
  const gf = (L.growth || {}).framework || { areas: [] }, aname = {}; (gf.areas || []).forEach((a) => (aname[a.key] = a.name));
  mut(GROWD, ((L.growth || {}).items || []).map((i) => ({ id: i.id, past: !!i.past, kind: i.kind, title: i.title, why: (i.why || i.outcome || "").slice(0, 170), areas: (i.areas || []).map((a) => aname[a] || a), state: i.state, hold: i.hold_until || "" })));
  mut(DECLINED, (L.growth || {}).declined || []);   // dismissed entries kept for a while so they can be restored
  if ((gf.areas || []).length) mut(AREAS, gf.areas.map((a) => ({ name: a.name, n: GROWD.filter((g) => g.areas.includes(a.name) && g.state !== "proposed").length })));

  // ---- sentences on Today ----
  LV.dateLong = D(today).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
  const todayMs = meetings.filter((m) => m.date === today);
  LV.nextLine = `${todayMs.length ? plural(todayMs.length, "meeting") + " today." : "No meetings today."}${nextM ? ` Next: ${esc(nextM.n)}, ${nextM.date === today ? "at" : nextM.date === plus(today, 1) ? "tomorrow at" : nextM.d + " at"} ${nextM.t}.` : ""}`;
  const nw = nextM ? (nextM.date === today ? "Today" : nextM.date === plus(today, 1) ? "Tomorrow" : nextM.d) + " " + nextM.t : "";
  LV.nextAt = nextM ? nextM.at : null; LV.nextWhen = nw;
  LV.nextCard = nextM ? `<div class="card-h"><h2>Next meeting</h2><span class="mono muted" id="cd">${esc(nw)}</span></div><h3 class="u-fs-20 u-mb8">${esc(nextM.n)}</h3><p class="u-mb16 muted">${esc((nextM.w || []).slice(0, 3).join(", "))}. ${nextM.ag.length ? `Brief ready, ${nextM.ag.length} to raise.` : "Nothing to raise."}</p><a class="u-c-glow-2 link" href="#meetings" data-gomeet="${MEET.indexOf(nextM)}">Open the brief</a>`
    : `<div class="card-h"><h2>Next meeting</h2></div><p class="muted">No more meetings this week.</p>`;
  const moreW = Math.max(0, Object.keys(WANT).length - 3);
  LV.moreWaitingHtml = moreW ? `<a class="more" href="#questions">${plural(moreW, "more person", "more people")}</a>` : "";
  LV.footer = `${brief ? "Last pull " + LV.pullAt + " · " : ""}${plural(S0.docs || 0, "document")} read${health.length ? " · " + plural(health.length, "thing needs", "things need") + " a look in Sources" : ""} · Press ? for shortcuts`;
};
window.rebuildLive();

/* ---- screens that need live content: Changes, Sources, a feature page ---- */
function changesInner() {
  const c = LV.counts;
  return `<div class="card-h"><h2>What changed</h2><span class="hint mono">${LV.pullAt ? "since " + LV.pullAt : ""}</span></div>` +
    (LV.pullAt ? `<div class="mini"><span>Jira <b>${c.jn}</b> new · <b>${c.jc}</b> changed</span><span>Confluence <b>${c.cn}</b> new · <b>${c.cc}</b> changed</span></div>` : "") +
    (TOPICS.length ? TOPICS.slice(0, 3).map((x, i) => topicRow(x, i)).join("") + `<div class="acc more-acc"><div class="in">${TOPICS.slice(3).map((x, i) => topicRow(x, i + 3)).join("")}</div></div>` + (TOPICS.length > 3 ? `<button class="more" data-more>${TOPICS.length - 3} more topics</button>` : "") : `<p class="zero">${LV.pullAt ? "Nothing new since the pull before." : "No pull yet. Press Start a pull."}</p>`);
}
function topicRow(x) {
  return `<div class="tp"><button class="tph hh" data-tp>${x.hot ? '<span class="pulse" title="Ties to an overdue task"></span>' : '<span class="sp"></span>'}<span class="t"><b>${esc(x.t)}</b><small>${esc(x.s)}</small></span><span class="tag">${esc(x.tag)}</span>${CHEV}</button><div class="acc"><div class="in"><p class="tpb">${esc(x.more)} <span class="srcl">Source: pull of ${esc(LV.pullAt)}</span><a href="features/${esc(x.slug)}.html">Open the card</a></p></div></div></div>`;
}
