/* whats-new: visits and What's new. */
Mantis.define("whats-new", ["core"], (m_core) => {
  const { store, $, $$ } = m_core;
  // ---- Visits and What's new (IMP-043) ----
  // The day of the previous visit, kept in this browser only: "since your last visit" means since that day.
  const todayISO = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  const visit = store.get("mantis.visit");
  if (visit.current !== todayISO) { if (visit.current) visit.previous = visit.current; visit.current = todayISO; store.set("mantis.visit", visit); }
  const lastVisit = visit.previous || "";
  const dayName = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });


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
});
