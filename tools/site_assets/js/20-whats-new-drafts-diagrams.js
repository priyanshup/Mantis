  // ---- Visits and What's new (IMP-043) ----
  // The day of the previous visit, kept in this browser only: "since your last visit" means since that day.
  const todayISO = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const visit = store.get("mantis.visit");
  if (visit.current !== todayISO) { if (visit.current) visit.previous = visit.current; visit.current = todayISO; store.set("mantis.visit", visit); }
  const lastVisit = visit.previous || "";
  const dayName = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
  const EV_WORDS = { source: ["new source", "new sources"], question: ["new question", "new questions"], answer: ["answer", "answers"],
    likely: ["likely answer", "likely answers"], possible: ["possible conflict", "possible conflicts"], conflict: ["new conflict", "new conflicts"], decision: ["decision", "decisions"],
    stage: ["stage change", "stage changes"], jira: ["item moved to Jira", "items moved to Jira"], closed: ["question closed", "questions closed"] };

  const strip = $("#since-strip"), counts = $("#changes-counts");
  if (strip && counts && lastVisit) {
    let rows = []; try { rows = JSON.parse(counts.textContent); } catch (e) {}
    const n = {};
    rows.filter(([d]) => d >= lastVisit).forEach(([, k]) => { n[k] = (n[k] || 0) + 1; });
    const order = ["possible", "conflict", "likely", "answer", "closed", "decision", "stage", "jira", "question", "source"];
    const parts = order.filter((k) => n[k]).map((k) => `${n[k]} ${EV_WORDS[k][n[k] === 1 ? 0 : 1]}`);
    if (parts.length) {
      $(".since-t", strip).innerHTML = `<b>Since ${esc(lastVisit === todayISO ? "earlier today" : dayName(lastVisit))}:</b> ${esc(parts.slice(0, 4).join(" · "))}${parts.length > 4 ? " and more" : ""}`;
      strip.href = "changes.html#visit"; strip.hidden = false;
    }
  }

  const evFeed = $("#ev-feed");
  if (evFeed) {
    const range = $("#ev-range"), kinds = $("#ev-kind"), sum = $("#ev-sum"), none = $("#ev-none");
    const today = new Date(evFeed.dataset.today + "T12:00:00");
    const back = (days) => new Date(today - days * 864e5).toISOString().slice(0, 10);
    if (!lastVisit) { const b = $('[data-v="visit"]', range); if (b) b.hidden = true; }
    let r = location.hash === "#visit" && lastVisit ? "visit" : (store.get("mantis.ev").range || "7"), k = "all";
    if (r === "visit" && !lastVisit) r = "7";
    const apply = () => {
      const since = r === "visit" ? lastVisit : back(Number(r));
      $$("button", range).forEach((b) => b.classList.toggle("on", b.dataset.v === r));
      $$("button", kinds).forEach((b) => b.classList.toggle("on", b.dataset.v === k));
      let shown = 0;
      $$(".ev-day", evFeed).forEach((day) => {
        let n = 0;
        $$(".ev-list > .ev", day).forEach((e) => {   // a folded row ("19 card summaries refreshed") counts as its N changes
          const on = e.dataset.date >= since && (k === "all" || e.dataset.group === k); e.hidden = !on; n += on ? Number(e.dataset.n || 1) : 0;
        });
        day.hidden = !n; $(".ev-n", day).textContent = `${n} change${n === 1 ? "" : "s"}`; shown += n;
      });
      none.hidden = !!shown || !$(".ev-day", evFeed);
      sum.textContent = shown ? `${shown} change${shown === 1 ? "" : "s"} ${r === "visit" ? `since your last visit on ${dayName(lastVisit)}` : `in the last ${r} days`}.` : "";
      store.set("mantis.ev", { range: r === "visit" ? store.get("mantis.ev").range || "7" : r });
    };
    range.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { r = b.dataset.v; apply(); } });
    kinds.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { k = b.dataset.v; apply(); } });
    apply();
  }

  // ---- Draft a message to whoever can answer (IMP-048): pick questions, edit, copy for Teams ----
  const draftData = (() => { try { return JSON.parse(($("#draft-data") || {}).textContent || "{}"); } catch (e) { return {}; } })();
  function openDraft(name) {
    const d = draftData[name]; if (!d || !d.questions.length) { toast("No open questions for " + name + "."); return; }
    const m = document.createElement("div"); m.className = "modal-wrap";
    m.innerHTML = `<div class="modal dm" role="dialog" aria-modal="true" aria-labelledby="dm-t"><div class="bm-h"><div><p class="hello">${d.channel ? "Draft for " + esc(d.channel) : "Draft message"}</p><h2 id="dm-t">Questions for ${esc(name)}</h2></div>` +
      `<button type="button" class="mini icon" data-dclose aria-label="Close">✕</button></div>` +
      `<fieldset class="dm-q"><legend class="muted small">Include</legend>${d.questions.map((q, i) => `<label><input type="checkbox" data-i="${i}" checked> <span>${esc(q.q)}${q.named ? "" : ' <span class="muted small">(suggested)</span>'}</span></label>`).join("")}</fieldset>` +
      `<label class="muted small" for="dm-text">Message (edit freely)</label><textarea id="dm-text" rows="12"></textarea>` +
      `<div class="dm-acts"><button type="button" class="btn-line" data-dreset hidden>Rebuild from the list</button><button type="button" class="btn" data-dcopy>Copy message</button></div></div>`;
    document.body.appendChild(m);
    const ta = $("#dm-text", m), reset = $("[data-dreset]", m);
    let edited = false;
    const compose = () => {
      const qs = $$("input[data-i]", m).filter((c) => c.checked).map((c) => d.questions[Number(c.dataset.i)]);
      const lines = qs.map((q, i) => `${i + 1}. ${q.q}${q.card ? ` (${q.card})` : ""}` + (q.ctx ? `\n   ${q.ctx}` : ""));
      return `Hi ${d.first},\n\nI'm tracking ${qs.length === 1 ? "an open question" : "a few open questions"} I think you can help with:\n\n${lines.join("\n\n")}\n\nA short answer on any of them helps. Thanks!`;
    };
    const fill = () => { ta.value = compose(); edited = false; reset.hidden = true; };
    fill();
    ta.addEventListener("input", () => { edited = true; reset.hidden = false; });
    $$("input[data-i]", m).forEach((c) => c.addEventListener("change", () => { if (!edited) fill(); else reset.hidden = false; }));
    reset.addEventListener("click", fill);
    const close = () => { m.remove(); document.removeEventListener("keydown", key); };
    const key = (e) => { if (e.key === "Escape") close(); };
    document.addEventListener("keydown", key);
    m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-dclose]")) close(); });
    $("[data-dcopy]", m).addEventListener("click", () => copyText(ta.value));
    ta.focus(); ta.setSelectionRange(0, 0); ta.scrollTop = 0;   // read it from the greeting down
  }
  document.addEventListener("click", (e) => { const b = e.target.closest("[data-draft]"); if (b) openDraft(b.dataset.draft); });
  const oiDraft = $("#oi-draft"), oiWho = $("#oi-who");
  if (oiDraft && oiWho) {
    const sync = () => { const n = oiWho.value; oiDraft.hidden = !(n && draftData[n]); oiDraft.dataset.draft = n; oiDraft.textContent = n ? `Draft a message to ${n.split(" ")[0]}` : "Draft a message"; };
    oiWho.addEventListener("change", sync); setTimeout(sync, 0);
  }

  // ---- Diagrams chips (IMP-008) ----
  const dia = $("#f-dia");
  if (dia) dia.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    $$("button", dia).forEach((x) => x.classList.toggle("on", x === b));
    $$(".dia").forEach((r) => (r.hidden = b.dataset.v !== "all" && r.dataset.type !== b.dataset.v));
  });

