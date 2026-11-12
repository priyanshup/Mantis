/* feature-meetings.js: add, edit and delete a regular meeting (the Meetings tab). Saved through POST api/schedule (tools/schedule.py). */
(() => {
  const DAYS = [["Mon", "Monday"], ["Tue", "Tuesday"], ["Wed", "Wednesday"], ["Thu", "Thursday"], ["Fri", "Friday"], ["Sat", "Saturday"], ["Sun", "Sunday"]];
  const EVERY = [[1, "Every week"], [2, "Every 2 weeks"], [3, "Every 3 weeks"], [4, "Every 4 weeks"]];
  const raw = (id) => (((window.__LIVE || {}).extra || {}).meetings || []).find((m) => m.id === id);
  const fields = (m = {}) => [
    { name: "name", label: "Name", required: true, value: m.name || "", placeholder: "Weekly sync", wide: true },
    { name: "day", label: "Day", type: "select", options: DAYS, value: m.day || "Mon" },
    { name: "time", label: "Time", type: "time", value: m.time || "09:00" },
    { name: "every", label: "How often", type: "select", options: EVERY, value: m.every || 1 },
    { name: "attendees", label: "Who is in it", type: "multi", options: PEOPLE.map((p) => [p.name, p.name]), value: m.attendees || [], wide: true, hint: "Pick from your people or type a name, then Enter." },
    { name: "purpose", label: "What it is for", type: "textarea", value: m.purpose || "", wide: true, placeholder: "One line, so the agenda knows what to raise." },
    { name: "cards", label: "Subjects", type: "multi", options: (LV.cards || []).map((c) => [c.slug, c.title]), value: m.cards || [], wide: true, free: false, hint: "Features and topics this meeting is about." },
    { name: "draws", label: "The agenda draws on", type: "checks", options: [["people", "Open questions and follow-ups for the people in it"], ["subjects", "Open items on its subjects"]], value: m.draws || ["people", "subjects"], wide: true },
  ];
  const save = async (v, id) => {
    await Api.post("api/schedule", { action: id ? "edit-meeting" : "add-meeting", id, ...v });
    await Live.refresh(["extra"]);
    toast(id ? "Meeting saved." : "Meeting added.");
  };
  UI.action("meeting-new", () => UI.dialog({ title: "New meeting", intro: "A regular meeting. Mantis builds its agenda from what is open.", fields: fields(), submit: "Add meeting", onSubmit: (v) => save(v) }));
  UI.action("meeting-edit", (el) => {
    const m = raw(el.dataset.id); if (!m) { toast("That meeting is not in the schedule."); return; }
    UI.dialog({ title: "Edit meeting", fields: fields(m), submit: "Save", onSubmit: (v) => save(v, m.id),
      extra: `<button type="button" class="link danger" data-act="meeting-remove" data-id="${esc(m.id)}">Delete meeting</button>` });
  });
  UI.action("meeting-remove", (el) => {
    const m = raw(el.dataset.id); if (!m) return;
    UI.confirm({ title: `Delete ${m.name}?`, text: "Its agenda and takeaways stop showing. Notes already in the inbox are kept.", yes: "Delete meeting",
      onYes: async () => { await Api.post("api/schedule", { action: "remove-meeting", id: m.id }); await Live.refresh(["extra"]); toast("Meeting deleted."); } });
  });

  /* ---- the day chips and the search box (small screens show them) ---- */
  const curIndex = () => { const r = $(".mt .mrow[aria-pressed='true']"); return r ? +r.dataset.mi : MEET.findIndex((m) => m.next); };
  const redrawList = () => {
    const list = $("#mlist"); if (!list) return;
    list.innerHTML = meetListHtml(curIndex());
    const chips = $("#mchips"); if (chips) chips.innerHTML = meetChips();
  };
  UI.action("meeting-day", (el) => { ST.mday = ST.mday === el.dataset.day ? "All" : el.dataset.day; redrawList(); });   // the chosen day toggles off when pressed again
  UI.action("meeting-clear-filter", () => { ST.mday = "All"; ST.mq = ""; const q = $("#mq"); if (q) q.value = ""; redrawList(); });
  document.addEventListener("input", (e) => { if (e.target.id === "mq") { ST.mq = e.target.value; redrawList(); } });

  /* ---- the strip of meetings scrolls sideways with the wheel on small screens ----
     A wheel step moves the strip, not the page, until the strip reaches an end; then the page scrolls again. */
  const strip = (t) => (t.closest ? t.closest(".mt > section:first-of-type") : null);
  document.addEventListener("wheel", (e) => {
    const s = strip(e.target);
    if (!s || !matchMedia("(max-width:1020px)").matches || s.scrollWidth <= s.clientWidth) return;
    if (!e.deltaY || Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;   // a sideways swipe already scrolls the strip; a mouse wheel is vertical
    const dx = e.deltaY;
    const unit = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? s.clientWidth : 1, max = s.scrollWidth - s.clientWidth, next = Math.max(0, Math.min(max, s.scrollLeft + dx * unit));
    if (next !== s.scrollLeft) { e.preventDefault(); s.scrollLeft = next; }
  }, { passive: false });

  /* ---- once, when the screen is drawn: show the chosen meeting inside the strip. Only the strip moves, never the page. ---- */
  UI.onShow("meetings", () => {
    const s = $(".mt > section:first-of-type"), r = $(".mt .mrow[aria-pressed='true']");
    if (s && r && s.scrollWidth > s.clientWidth) s.scrollLeft = Math.max(0, r.offsetLeft - (s.clientWidth - r.offsetWidth) / 2);
  });
})();
