  // ---- Today: the owner's task list (MANTIS-IMP-018), saved to mantis/tasks/ through tools/serve.py ----
  // One rule for dates: `day` is when a task shows on Today. Scheduling sets day (and remind_on, so the
  // brief flags it on that day); Bring to today resets both. Deleting is soft: the task waits under
  // Recently deleted for 7 days. Every move offers Undo.
  const tList = $("#t-list");
  if (tList) {
    const served = location.protocol.startsWith("http") && window.fetch;
    const PR = { high: 0, medium: 1, low: 2, "": 3 };
    const PL = { high: ["High", "p-p1"], medium: ["Medium", "p-p2"], low: ["Low", "p-p3"] };
    let S = { rev: 0, tasks: [], dismissed: [], today: "", suggestions: { items: [] } }, openId = null, timer = null, focusNote = null;
    const uid = () => Math.random().toString(36).slice(2, 12);
    const fmtMin = (m) => (m >= 60 ? `${Math.floor(m / 60)}h${m % 60 ? " " + (m % 60) + "m" : ""}` : `${m}m`);
    const nice = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : "";
    const tomorrow = () => addDays(S.today, 1);
    const dayName = (d) => !d || d === S.today ? "Today" : d === tomorrow() ? "Tomorrow" : nice(d);
    const live = (t) => t.status === "todo" || t.status === "blocked";
    const carried = (t) => live(t) && t.day && t.day < S.today;
    // Days a focus task has been carried over (IMP-040): amber from day 1, stronger from day 3.
    const carriedDays = (t) => carried(t) ? Math.max(1, Math.round((new Date(S.today + "T12:00") - new Date(t.day + "T12:00")) / 864e5)) : 0;
    const isToday = (t) => live(t) && (!t.day || t.day <= S.today);
    const byOrder = (a, b) => a.order - b.order;
    const topOrder = () => Math.min(0, ...S.tasks.map((t) => t.order)) - 1;

    function save() {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const r = await fetch("api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rev: S.rev, tasks: S.tasks, dismissed: S.dismissed }) });
          const j = await r.json();
          if (r.status === 409) { Object.assign(S, j); draw(); toast("Your list changed in another tab; showing the latest."); return; }
          if (!r.ok) throw new Error(j.error);
          S.rev = j.rev;
        } catch (e) { toast("Could not save your tasks. Is the site server running?"); }
      }, 400);
    }
    const change = () => { draw(); save(); };
    const task = (id) => S.tasks.find((t) => t.id === id);
    function renumber(ids) { ids.forEach((id, i) => { const t = task(id); if (t) t.order = i; }); }
    // Change a task, show a message, and offer Undo (restores the task exactly as it was).
    function withUndo(t, msg, fn) {
      const before = JSON.parse(JSON.stringify(t));
      fn(); change();
      toast(msg, () => { const i = S.tasks.findIndex((x) => x.id === before.id); i < 0 ? S.tasks.push(before) : (S.tasks[i] = before); change(); });
    }
    const schedule = (t, v) => {   // put a task on a day ("" or today = Today)
      if (!v || v <= S.today) { t.day = S.today; t.remind_on = ""; } else { t.day = v; t.remind_on = v; }
      if (t.status !== "blocked") t.status = "todo";
      t.done_at = "";
      if (t.day === S.today) t.order = topOrder();
    };

    const dpBtn = (kind, value, label, extra = "") => `<button type="button" class="dp-btn ${extra}" data-kind="${kind}" data-value="${value}" data-today="${S.today}" aria-haspopup="dialog">${label}</button>`;
    function inline(t) {   // the one or two moves that matter most for where the task is now
      if (t.status === "deleted") return `<span class="t-inline"><button type="button" class="mini on" data-a="restore">Restore to today</button><button type="button" class="mini" data-a="restore-tomorrow">Restore for tomorrow</button><button type="button" class="mini t-del" data-a="purge">Delete for good</button></span>`;
      if (t.status === "parked") return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Back to today</button>${dpBtn("when", "", "Schedule…", "mini")}</span>`;
      if (live(t) && t.day > S.today) return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Bring to today</button>${dpBtn("when", t.day, "Move…", "mini")}</span>`;
      if (isToday(t)) return `<span class="t-inline hover-only"><button type="button" class="mini" data-a="tomorrow" title="Move to tomorrow">Tomorrow</button>${dpBtn("when", "", "Later…", "mini")}<button type="button" class="mini icon t-del" data-a="delete" title="Delete (you can restore it)" aria-label="Delete">✕</button></span>`;
      return "";
    }
    function row(t, opts = {}) {
      const p = PL[t.priority], over = live(t) && t.due && t.due < S.today, dueToday = t.due === S.today;
      const chips = [p ? `<span class="pill ${p[1]}">${p[0]}</span>` : "", t.status === "blocked" ? '<span class="pill w-review">Blocked</span>' : "",
        carried(t) ? `<span class="tag carry${carriedDays(t) >= 3 ? " carry-old" : ""}" title="On your list since ${nice(t.day)}">Backlog · carried ${carriedDays(t)} day${carriedDays(t) > 1 ? "s" : ""}</span>` : "",
        live(t) && t.day > S.today ? `<span class="tag tag-when">${esc(dayName(t.day))}</span>` : "",
        t.estimate ? `<span class="muted small">${fmtMin(t.estimate)}</span>` : "",
        t.due ? `<span class="small ${over ? "warn-text" : dueToday ? "due-today" : "muted"}">${over ? "Overdue · " : "Due "}${nice(t.due)}</span>` : "",
        t.contact ? `<span class="small t-who">Ask ${esc(t.contact)}</span>` : "",
        t.comments.length ? `<span class="muted small">💬 ${t.comments.length}</span>` : "",
        t.status === "deleted" ? `<span class="muted small">Deleted ${nice(t.deleted_at)}</span>` : ""].join("");
      const open = openId === t.id && t.status !== "deleted";
      return `<li class="t-row${carried(t) ? (carriedDays(t) >= 3 ? " t-carried carry-old" : " t-carried") : ""}${t.status === "done" ? " done" : ""}${t.status === "deleted" ? " gone" : ""}${open ? " open" : ""}" data-id="${t.id}" ${opts.drag ? 'draggable="true"' : ""}>
        <div class="t-main">${opts.drag ? '<span class="t-grip" title="Drag to rank">⋮⋮</span>' : ""}
        ${t.status === "deleted" ? "" : `<input type="checkbox" class="t-check" ${t.status === "done" ? "checked" : ""} aria-label="Done">`}
        <button type="button" class="t-title">${esc(t.title)}</button><span class="t-chips">${chips}</span>${inline(t)}</div>
        ${carried(t) && opts.drag ? `<div class="t-carry nocopy">Still relevant? <button type="button" class="mini on" data-a="keep">Keep for today</button>${dpBtn("when", "", "Move to…", "mini")}<button type="button" class="mini" data-a="park">Park</button></div>` : ""}
        ${open ? detail(t) : ""}</li>`;
    }
    function detail(t) {
      const log = t.comments.map((c) => `<li><span class="muted small">${esc(c.at)}</span> ${esc(c.text)}</li>`).join("");
      const est = [["0", "Time?"], ["15", "15 min"], ["30", "30 min"], ["60", "1 hour"], ["120", "2 hours"], ["240", "Half day"], ["480", "Full day"]];
      const prio = ["high", "medium", "low"].map((v) => `<button type="button" data-p="${v}" class="${t.priority === v ? "on" : ""}">${PL[v][0]}</button>`).join("");
      const later = live(t) && t.day > S.today;
      return `<div class="t-detail">
        <div class="t-fields">
          <label class="fld fld-wide"><span>Title</span><input data-f="title" value="${esc(t.title)}"></label>
          <div class="fld"><span>Priority</span><span class="prio-seg" data-f="priority">${prio}</span></div>
          <label class="fld"><span>Time</span><select class="sel sel-sm" data-f="estimate">${est.map(([v, l]) => `<option value="${v}" ${String(t.estimate) === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
          <div class="fld"><span>Do on</span>${dpBtn("when", live(t) ? t.day || S.today : "", live(t) ? dayName(t.day) : t.status === "parked" ? "Parked: pick a day" : "Pick a day")}</div>
          <div class="fld"><span>Due</span>${dpBtn("due", t.due, t.due ? nice(t.due) : "No due date")}</div>
          <label class="fld"><span>Ask</span><input data-f="contact" value="${esc(t.contact)}" placeholder="Who to reach out to"></label></div>
        <div class="t-log"><p class="small muted">Notes and findings</p><ul>${log || '<li class="muted small">None yet.</li>'}</ul>
        <div class="t-comment"><input placeholder="${t.status === "blocked" ? "What is it blocked on?" : "What you found so far, or why it is blocked"}" data-c="1"><button type="button" class="btn-line" data-a="comment">Add note</button></div></div>
        <div class="t-acts">${later || t.status === "parked" ? '<button type="button" class="btn" data-a="today">Bring to today</button>' : ""}
        ${t.status === "blocked" ? '<button type="button" class="btn-line" data-a="unblock">Unblock</button>' : t.status === "todo" ? '<button type="button" class="btn-line" data-a="block">Mark blocked</button>' : ""}
        ${t.day !== tomorrow() && t.status !== "done" ? '<button type="button" class="btn-line" data-a="tomorrow">Move to tomorrow</button>' : ""}
        ${t.status === "parked" ? "" : t.status !== "done" ? '<button type="button" class="btn-line" data-a="park">Park</button>' : ""}
        <button type="button" class="btn-line t-del" data-a="delete">Delete</button></div></div>`;
    }

    function brief() {
      const sug = (S.suggestions.items || []).filter((s) => !S.dismissed.includes(s.id));
      const body = sug.length ? sug.map((s) => `<details class="sug"><summary><b>${esc(s.title)}</b>${s.who ? `<span class="muted small">${esc(s.who)}</span>` : ""}</summary>
          <div class="sug-body">${s.why ? `<p>${esc(s.why)}</p>` : ""}${s.say ? `<p><b>What to say:</b> ${esc(s.say)}</p>` : ""}
          ${(s.questions || []).length ? `<p><b>Questions to ask:</b></p><ul>${s.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>` : ""}
          ${s.source ? `<p class="muted small">From: ${esc(s.source)}</p>` : ""}
          <div class="t-acts"><button type="button" class="btn" data-s="${s.id}" data-sa="add">Add to today</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="later">Tomorrow</button>
          <button type="button" class="btn-line" data-s="${s.id}" data-sa="copy">Copy</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="dismiss">Dismiss</button></div></div></details>`).join("")
        : S.suggestions.stale
          ? `<p class="muted small">No suggestions yet today.</p><div class="brief-acts"><button type="button" class="btn-line job ai" data-job="daily-brief" title="Uses Claude, on your normal quota">Prepare today's brief</button><button type="button" class="mini job" data-job="skip-brief" title="Free: no AI">Skip today</button></div>`
          : '<p class="muted small">Nothing more to suggest today.</p>';
      $("#t-brief").innerHTML = `<div class="sc-h"><h2><i class="bi bi-spark"></i>Mantis suggests</h2><span class="sc-n">${sug.length || ""}</span></div>${body}`;
    }

    function draw() {
      dp.close();
      const d = new Date(S.today + "T12:00");
      $("#t-date").textContent = d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
      const today = S.tasks.filter(isToday);
      // Carried-over tasks nobody has decided on yet go to the top; the rest follow the owner's ranking.
      today.sort((a, b) => (carried(b) - carried(a)) || byOrder(a, b));
      const mins = today.reduce((n, t) => n + (t.estimate || 0), 0);
      const later = S.tasks.filter((t) => live(t) && t.day > S.today).sort((a, b) => a.day.localeCompare(b.day) || byOrder(a, b));
      const parked = S.tasks.filter((t) => t.status === "parked").sort(byOrder);
      const done = S.tasks.filter((t) => t.status === "done").sort((a, b) => (b.done_at || "").localeCompare(a.done_at || ""));
      const bin = S.tasks.filter((t) => t.status === "deleted").sort((a, b) => (b.deleted_at || "").localeCompare(a.deleted_at || ""));
      const blocked = today.filter((t) => t.status === "blocked").length;
      $("#t-sum").textContent = today.length
        ? `${today.length} task${today.length === 1 ? "" : "s"} for today${mins ? `, about ${fmtMin(mins)} of work` : ""}${blocked ? `, ${blocked} blocked` : ""}. ${done.length} done.`
        : "Nothing on today's list. Add a task above.";
      $("#t-total").textContent = mins ? `≈ ${fmtMin(mins)}` : "";
      tList.innerHTML = today.map((t) => row(t, { drag: true })).join("") || '<li class="empty">Add your first task above.</li>';
      // Scheduled tasks grouped by day, so "what comes back when" reads at a glance.
      let last = "";
      $("#t-sched").innerHTML = later.map((t) => (t.day !== last ? `<li class="t-day">${esc(dayName((last = t.day)))}</li>` : "") + row(t)).join("") || '<li class="empty">Nothing scheduled.</li>';
      $("#t-park").innerHTML = parked.map((t) => row(t)).join("") || '<li class="empty">Nothing parked.</li>';
      $("#t-done").innerHTML = done.map((t) => row(t)).join("") || '<li class="empty">Nothing done yet today.</li>';
      $("#t-bin").innerHTML = bin.map((t) => row(t)).join("") || '<li class="empty">Nothing deleted.</li>';
      $("#t-sched-n").textContent = later.length; $("#t-park-n").textContent = parked.length; $("#t-done-n").textContent = done.length; $("#t-bin-n").textContent = bin.length;
      $("#t-bin-box").hidden = !bin.length; $("#t-sched-box").hidden = !later.length; $("#t-park-box").hidden = !parked.length; $("#t-done-box").hidden = !done.length;
      brief();
      if (focusNote) { const inp = document.querySelector(`.t-row[data-id="${focusNote}"] [data-c]`); if (inp) inp.focus(); focusNote = null; }
    }

    // Adding: priority toggle, when and due pickers
    const addPrio = $("#t-prio");
    addPrio.addEventListener("click", (e) => {
      const b = e.target.closest("[data-p]"); if (!b) return;
      addPrio.dataset.value = addPrio.dataset.value === b.dataset.p ? "" : b.dataset.p;
      $$("[data-p]", addPrio).forEach((x) => x.classList.toggle("on", x.dataset.p === addPrio.dataset.value));
    });
    const addWhen = $("#t-when"), addDue = $("#t-due");
    const labelAdd = () => {
      addWhen.textContent = dayName(addWhen.dataset.value); addWhen.classList.toggle("set", !!addWhen.dataset.value && addWhen.dataset.value !== S.today);
      addDue.textContent = addDue.dataset.value ? "Due " + nice(addDue.dataset.value) : "No due date"; addDue.classList.toggle("set", !!addDue.dataset.value);
    };
    addWhen.addEventListener("dp-pick", labelAdd); addDue.addEventListener("dp-pick", labelAdd);
    $("#t-add").addEventListener("submit", (e) => {
      e.preventDefault();
      const title = $("#t-title").value.trim(); if (!title) { $("#t-title").focus(); return; }
      const t = { id: uid(), title, status: "todo", priority: addPrio.dataset.value, estimate: +$("#t-est").value, due: addDue.dataset.value,
        remind_on: "", day: S.today, contact: $("#t-contact").value.trim(), comments: [], created: S.today, done_at: "", order: 0, source: "" };
      schedule(t, addWhen.dataset.value);
      if (t.day === S.today) t.order = Math.max(-1, ...S.tasks.filter(isToday).map((x) => x.order)) + 1;   // new work goes to the bottom of today
      S.tasks.push(t);
      e.target.reset(); addPrio.dataset.value = ""; $$("[data-p]", addPrio).forEach((x) => x.classList.remove("on"));
      addWhen.dataset.value = ""; addDue.dataset.value = ""; labelAdd();
      $("#t-title").focus(); change();
      toast(t.day > S.today ? `Scheduled for ${dayName(t.day)}. It comes back to Today then.` : "Added to today.", () => { S.tasks = S.tasks.filter((x) => x !== t); change(); });
    });

    // Every action on a task, in one place
    function act(t, a, rowEl) {
      const name = `"${t.title.length > 40 ? t.title.slice(0, 40) + "…" : t.title}"`;
      if (a === "keep") return withUndo(t, "Kept for today.", () => { t.day = S.today; t.remind_on = ""; });
      if (a === "today") return withUndo(t, `${name} is back on today's list.`, () => schedule(t, S.today));
      if (a === "tomorrow") return withUndo(t, `Moved to tomorrow.`, () => { schedule(t, tomorrow()); openId = null; });
      if (a === "park") return withUndo(t, "Parked. Find it under Parked.", () => { t.status = "parked"; openId = null; });
      if (a === "block") { t.status = "blocked"; openId = t.id; focusNote = t.id; t.comments.push({ at: S.today, text: "Marked blocked." }); return change(); }
      if (a === "unblock") { t.status = "todo"; t.comments.push({ at: S.today, text: "Unblocked." }); return change(); }
      if (a === "comment") { const inp = rowEl.querySelector("[data-c]"); if (!inp.value.trim()) return; t.comments.push({ at: S.today, text: inp.value.trim() }); focusNote = t.id; return change(); }
      if (a === "delete") return withUndo(t, `Deleted ${name}. It stays under Recently deleted for 7 days.`, () => { t.was = t.status; t.status = "deleted"; t.deleted_at = S.today; openId = null; });
      if (a === "restore") return withUndo(t, `Restored ${name} to today.`, () => { t.status = t.was === "blocked" ? "blocked" : "todo"; t.deleted_at = ""; t.was = ""; schedule(t, S.today); });
      if (a === "restore-tomorrow") return withUndo(t, `Restored ${name} for tomorrow.`, () => { t.status = "todo"; t.deleted_at = ""; t.was = ""; schedule(t, tomorrow()); });
      if (a === "purge") { S.tasks = S.tasks.filter((x) => x !== t); change(); toast(`Deleted ${name} for good.`, () => { S.tasks.push(t); change(); }); }
    }
    document.addEventListener("dp-pick", (e) => {
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      if (e.target.dataset.kind === "due") { withUndo(t, e.detail ? `Due ${nice(e.detail)}.` : "Due date removed.", () => { t.due = e.detail; }); return; }
      const v = e.detail;
      withUndo(t, !v || v <= S.today ? `${t.status === "parked" ? "Back on" : "On"} today's list.` : `Scheduled for ${dayName(v)}. It comes back to Today then.`, () => { schedule(t, v); if (v > S.today) openId = null; });
    });
    document.addEventListener("click", (e) => {
      const go = e.target.closest("[data-goto]");
      if (go) { openId = go.dataset.goto; draw(); const r = document.querySelector(`.t-row[data-id="${openId}"]`); if (r) r.scrollIntoView({ block: "center" }); return; }
      const sb = e.target.closest("[data-sa]");
      if (sb) {
        const s = (S.suggestions.items || []).find((x) => x.id === sb.dataset.s); if (!s) return;
        if (sb.dataset.sa === "copy") { copyText([s.title, s.why, s.who && "Who: " + s.who, s.say && "What to say: " + s.say, ...(s.questions || []).map((q) => "- " + q)].filter(Boolean).join("\n")); return; }
        let added = null;
        if (sb.dataset.sa !== "dismiss") {
          added = { id: uid(), title: s.title, status: "todo", priority: s.priority || "medium", estimate: s.estimate || 15, due: "", remind_on: "", day: S.today, contact: s.who || "",
            comments: [s.say && { at: S.today, text: "What to say: " + s.say }, (s.questions || []).length && { at: S.today, text: "Questions: " + s.questions.join(" / ") }].filter(Boolean),
            created: S.today, done_at: "", order: 0, source: "Mantis suggestion" };
          schedule(added, sb.dataset.sa === "later" ? tomorrow() : S.today);
          S.tasks.push(added);
        }
        S.dismissed.push(s.id); change();
        toast(sb.dataset.sa === "later" ? "Added to tomorrow." : sb.dataset.sa === "add" ? "Added to the top of today." : "Suggestion dismissed.",
          () => { S.dismissed = S.dismissed.filter((x) => x !== s.id); if (added) S.tasks = S.tasks.filter((x) => x !== added); change(); });
        return;
      }
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      const pb = e.target.closest(".prio-seg [data-p]");
      if (pb) { t.priority = t.priority === pb.dataset.p ? "" : pb.dataset.p; return change(); }
      if (e.target.classList.contains("t-check")) {
        if (e.target.checked) withUndo(t, "Done. Find it under Done.", () => { t.status = "done"; t.done_at = S.today; openId = null; });
        else withUndo(t, "Reopened on today's list.", () => { t.status = "todo"; t.done_at = ""; if (!t.day || t.day < S.today) t.day = S.today; });
        return;
      }
      const a = e.target.closest("[data-a]"); if (a) { act(t, a.dataset.a, r); return; }
      if (e.target.closest(".t-title") && t.status !== "deleted") { openId = openId === t.id ? null : t.id; draw(); }
    });
    document.addEventListener("change", (e) => {
      const f = e.target.closest("[data-f]"); if (!f || !f.closest(".t-row")) return;
      const t = task(f.closest(".t-row").dataset.id); if (!t) return;
      const k = f.dataset.f; t[k] = k === "estimate" ? +f.value : f.value.trim();
      if (k === "title" && !t.title) { t.title = "Untitled task"; }
      change();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && e.target.matches("[data-c]")) { e.preventDefault(); act(task(e.target.closest(".t-row").dataset.id), "comment", e.target.closest(".t-row")); }
      if (e.altKey && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
        const r = document.activeElement && document.activeElement.closest("#t-list .t-row"); if (!r) return;
        e.preventDefault();
        const ids = $$("#t-list .t-row").map((x) => x.dataset.id), i = ids.indexOf(r.dataset.id), j = i + (e.key === "ArrowUp" ? -1 : 1);
        if (j < 0 || j >= ids.length) return;
        [ids[i], ids[j]] = [ids[j], ids[i]]; renumber(ids); change();
        const again = document.querySelector(`.t-row[data-id="${r.dataset.id}"] .t-title`); if (again) again.focus();
      }
    });

    // Drag and drop ranking
    let dragId = null;
    tList.addEventListener("dragstart", (e) => { const r = e.target.closest(".t-row"); if (!r) return; dragId = r.dataset.id; r.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
    tList.addEventListener("dragend", (e) => { const r = e.target.closest(".t-row"); if (r) r.classList.remove("dragging"); $$(".t-row.drop-above,.t-row.drop-below").forEach((x) => x.classList.remove("drop-above", "drop-below")); });
    tList.addEventListener("dragover", (e) => {
      const r = e.target.closest(".t-row"); if (!r || !dragId || r.dataset.id === dragId) return;
      e.preventDefault(); const box = r.getBoundingClientRect(), above = e.clientY < box.top + box.height / 2;
      $$(".t-row.drop-above,.t-row.drop-below").forEach((x) => x.classList.remove("drop-above", "drop-below"));
      r.classList.add(above ? "drop-above" : "drop-below");
    });
    tList.addEventListener("drop", (e) => {
      const r = e.target.closest(".t-row"); if (!r || !dragId) return;
      e.preventDefault();
      const ids = $$("#t-list .t-row").map((x) => x.dataset.id).filter((id) => id !== dragId);
      const box = r.getBoundingClientRect(), above = e.clientY < box.top + box.height / 2;
      ids.splice(ids.indexOf(r.dataset.id) + (above ? 0 : 1), 0, dragId);
      const moved = task(dragId); if (moved && carried(moved)) moved.day = S.today;   // ranking a carry-over means it is today's work now
      renumber(ids); dragId = null; change();
    });
    $("#t-sortp").addEventListener("click", () => {
      const ids = S.tasks.filter(isToday).sort((a, b) => PR[a.priority] - PR[b.priority] || (a.due || "9999").localeCompare(b.due || "9999") || (a.estimate || 999) - (b.estimate || 999)).map((t) => t.id);
      const before = S.tasks.map((t) => [t.id, t.order]);
      renumber(ids); change();
      toast("Sorted by priority, then due date, then shortest first.", () => { before.forEach(([id, o]) => { const t = task(id); if (t) t.order = o; }); change(); });
    });

    if (!served) { $("#t-offline").hidden = false; $("#t-sum").textContent = ""; }
    else fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); addWhen.dataset.today = addDue.dataset.today = S.today; labelAdd(); draw(); })
      .catch(() => { $("#t-offline").hidden = false; });
    // Another part of the page changed a task (a suggested deadline was accepted): reload the list.
    document.addEventListener("mantis:tasks-changed", () => fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); draw(); }).catch(() => {}));
  }

