/* datepicker: the small calendar behind any .dp-btn. */
Mantis.define("datepicker", ["core"], (m_core) => {
  const { $ } = m_core;
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
});
