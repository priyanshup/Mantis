  // ---- Today: the owner's task list (MANTIS-IMP-018), saved to mantis/tasks/ through tools/serve.py ----
  // One rule for dates: `day` is when a task shows on Today. Scheduling sets day (and remind_on, so the
  // brief flags it on that day); Bring to today resets both. Deleting is soft: the task waits under
  // Recently deleted for 7 days. Every move offers Undo.
  const tList = $("#t-list");
  if (tList) {
    const served = location.protocol.startsWith("http") && window.fetch;
    const PR = { high: 0, medium: 1, low: 2, "": 3 };
    const PL = { high: ["High", "p-p1"], medium: ["Medium", "p-p2"], low: ["Low", "p-p3"] };
    let S = { rev: 0, tasks: [], groups: [], dismissed: [], today: "", suggestions: { items: [] } }, openId = null, timer = null, focusNote = null;
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
    // Today's default rank (2026-10-31): priority, then the sooner due date (overdue first), then the shorter
    // task; blocked work, then the older task, breaks a tie so the list never reshuffles on its own.
    const key = (t) => [PR[t.priority] ?? 3, t.due || "9999", t.estimate || 1e9, t.status === "blocked" ? 1 : 0, t.created || "", t.id];
    const cmpKey = (a, b) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1; return 0; };
    const pinned = (o) => o.pin != null;
    // Unpinned items in default rank, then each dragged item put back at the place it was dropped in
    function place(units) {
      const out = units.filter((u) => !pinned(u.o)).sort((a, b) => cmpKey(a.k, b.k));
      units.filter((u) => pinned(u.o)).sort((a, b) => a.o.pin - b.o.pin || cmpKey(a.k, b.k)).forEach((u) => out.splice(Math.min(u.o.pin, out.length), 0, u));
      return out;
    }
    // Today's list as units: an ungrouped task, or a group (ranked as its best task) holding its own ranked tasks
    function layout(today) {
      const unit = (t) => ({ id: "t:" + t.id, t, o: t, k: key(t) });
      const units = today.filter((t) => !groupOf(t.group)).map(unit);
      for (const g of S.groups.filter((x) => x.id)) {   // never the old "" placeholder: ungrouped tasks rank on their own
        const items = place(today.filter((t) => t.group === g.id).map(unit));
        if (items.length) units.push({ id: "g:" + g.id, g, o: g, items, k: items.map((x) => x.k).reduce((a, b) => (cmpKey(a, b) <= 0 ? a : b)) });
      }
      return place(units);
    }
    // After a drag or Alt+arrow: the moved item holds its new place, and every other dragged item the place it shows now
    const pinAll = (list, moved) => list.forEach((u, i) => { if (u.o === moved || pinned(u.o)) u.o.pin = i; });

    function save() {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          const r = await fetch("api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rev: S.rev, tasks: S.tasks, groups: S.groups, dismissed: S.dismissed }) });
          const j = await r.json();
          if (r.status === 409) { Object.assign(S, j); draw(); toast("Your list changed in another tab; showing the latest."); return; }
          if (!r.ok) throw new Error(j.error);
          S.rev = j.rev;
        } catch (e) { toast("Could not save your tasks. Is the site server running?"); }
      }, 400);
    }
    const change = () => { draw(); save(); };
    // Saving an edit in an open task closes it (2026-10-31): a pick, a date, a note, Enter in a field. Focus goes back
    // to its row, which then glides to its new place. A field left by Tab or a click saves but stays open, since
    // the owner is still editing; Mark blocked stays open to ask for the reason.
    let focusRow = null;
    const settle = (t) => { if (openId === t.id) { openId = null; focusRow = t.id; } };
    const task = (id) => S.tasks.find((t) => t.id === id);
    // Change a task, show a message, and offer Undo (restores the task exactly as it was).
    function withUndo(t, msg, fn) {
      const before = JSON.parse(JSON.stringify(t));
      fn(); change();
      toast(msg, () => { const i = S.tasks.findIndex((x) => x.id === before.id); i < 0 ? S.tasks.push(before) : (S.tasks[i] = before); change(); });
    }
    const schedule = (t, v) => {   // put a task on a day ("" or today = Today); it arrives in its default place
      if (!v || v <= S.today) { t.day = S.today; t.remind_on = ""; } else { t.day = v; t.remind_on = v; }
      t.pin = null;
      if (t.status !== "blocked") t.status = "todo";
      t.done_at = "";
      if (t.day === S.today) t.order = topOrder();
    };

    // ---- Pickers (2026-10-31): Priority, Time and Group each open one small menu under their button ----
    // Groups are the owner's own (a feature, or a name they type); Mantis never guesses one.
    const OPT = {
      prio: [["high", "High"], ["medium", "Medium"], ["low", "Low"], ["", "No priority"]],
      est: [["15", "15m"], ["30", "30m"], ["60", "1h"], ["120", "2h"], ["240", "½ day"], ["480", "1 day"], ["", "No estimate"]],
    };
    const CARDS = (() => { try { return JSON.parse($("#t-add").dataset.cards || "[]"); } catch (e) { return []; } })();
    const HREF = (() => { try { return JSON.parse(($("#pull-box") || {}).dataset.cards || "{}").href || {}; } catch (e) { return {}; } })();
    const groupOf = (id) => (id ? S.groups.find((g) => g.id === id) : null);
    const pickLabel = { prio: (v) => (v ? PL[v][0] : "Priority"), est: (v) => (+v ? fmtMin(+v) : "Time"), group: (v) => (groupOf(v) ? groupOf(v).name : "Group") };
    const shortTitle = (t) => t.replace(/\s*\([^)]*\)\s*$/, "");
    let menu = null;
    function closePick() { if (menu) { menu.remove(); menu = null; } }
    // opts.items replaces the standard options; opts.input asks for a name instead (Enter answers "name:<text>");
    // opts.ask puts a question above the options (a confirmation);
    // opts.back is where focus returns after a pick (the add line sends it to the title, so Enter adds the task)
    function openPick(btn, onPick, opts = {}) {
      if (menu && menu.owner === btn) return closePick();   // a second click on the same picker closes its menu
      closePick(); dp.close();   // one dropdown at a time: the date picker closes too
      const kind = btn.dataset.pick, cur = btn.dataset.value || "";
      menu = document.createElement("div"); menu.className = "pickmenu"; menu.setAttribute("role", "menu"); menu.owner = btn;
      const r = btn.getBoundingClientRect();
      menu.style.left = Math.max(8, Math.min(r.left, innerWidth - 300)) + scrollX + "px"; menu.style.top = r.bottom + scrollY + 6 + "px";
      const item = (v, l, sub) => `<button type="button" role="menuitemradio" aria-checked="${v === cur}" class="pm-i${v === cur ? " on" : ""}" data-v="${esc(v)}"><span>${esc(l)}</span>${sub ? `<span class="pm-s">${esc(sub)}</span>` : ""}</button>`;
      const paint = (q = "") => {
        if (opts.items) return opts.items.map(([v, l]) => item(v, l)).join("");
        if (kind !== "group") return OPT[kind].map(([v, l]) => item(v, l)).join("");
        const ql = q.trim().toLowerCase(), hit = (t) => !ql || t.toLowerCase().includes(ql);
        const mine = S.groups.filter((g) => g.id && hit(g.name)).map((g) => item(g.id, g.name, g.card ? "Feature" : ""));
        const taken = new Set(S.groups.map((g) => g.card).filter(Boolean));
        const feats = CARDS.filter(([slug, title]) => !taken.has(slug) && hit(title)).slice(0, 8).map(([slug, title, f]) => item("card:" + slug, shortTitle(title), f ? "Following" : ""));
        const make = ql && !S.groups.some((g) => g.name.toLowerCase() === ql) ? item("new:" + q.trim(), `New group “${q.trim()}”`) : "";
        return ((cur ? item("", "No group") : "") + (mine.length ? `<p class="pm-h">Your groups</p>${mine.join("")}` : "")
          + (feats.length ? `<p class="pm-h">Features</p>${feats.join("")}` : "") + make) || '<p class="pm-h">Type a name to start a group</p>';
      };
      const input = opts.input ? `<input class="pm-q" value="${esc(opts.input.value || "")}" placeholder="${esc(opts.input.placeholder)}" aria-label="${esc(opts.input.placeholder)}" maxlength="80">`
        : kind === "group" && !opts.items ? '<input class="pm-q" placeholder="Find a feature or name a group" aria-label="Find a feature or name a group">' : "";
      menu.innerHTML = (opts.ask ? `<p class="pm-ask">${esc(opts.ask)}</p>` : "") + input
        + (opts.input ? '<p class="pm-h">Enter to save · Esc to cancel</p>' : `<div class="pm-list">${paint()}</div>`);
      document.body.appendChild(menu);
      const q = $(".pm-q", menu);
      if (q) { q.focus(); q.select(); if (!opts.input) q.addEventListener("input", () => { $(".pm-list", menu).innerHTML = paint(q.value); }); }
      else { const f = $(".pm-i.on", menu) || $(".pm-i", menu); if (f) f.focus(); }
      menu.addEventListener("click", (e) => { e.stopPropagation(); const b = e.target.closest(".pm-i"); if (!b) return; const v = resolve(b.dataset.v); closePick(); onPick(v); if (!menu) (opts.back || btn).focus(); });
      menu.addEventListener("keydown", (e) => {
        const items = $$(".pm-i", menu), i = items.indexOf(document.activeElement);
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); const n = items[Math.max(0, Math.min(items.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))]; if (n) n.focus(); }
        else if (e.key === "Enter" && e.target === q) {
          e.preventDefault();
          if (opts.input) { const v = q.value.trim(); closePick(); if (v) onPick("name:" + v); (opts.back || btn).focus(); }
          else { const b = $(".pm-i", menu); if (b) b.click(); }
        } else if (e.key === "Escape") { e.stopPropagation(); closePick(); btn.focus(); }
      });
    }
    // A group pick may name a feature or a new group: make it exist, then answer with its id
    function resolve(v) {
      if (v.startsWith("card:")) {
        const slug = v.slice(5), c = CARDS.find((x) => x[0] === slug), id = "f-" + slug;
        if (!groupOf(id)) S.groups.push({ id, name: shortTitle(c ? c[1] : slug), card: slug });
        return id;
      }
      if (v.startsWith("new:")) { const id = "g-" + uid().slice(0, 6); S.groups.push({ id, name: v.slice(4, 84), card: "" }); return id; }
      return v;
    }
    // Any click outside the menu closes it, Today and Due included (they open the date picker); a picker's own
    // button is left to openPick, which toggles it or swaps in the new menu
    document.addEventListener("click", (e) => { if (menu && !e.composedPath().includes(menu) && !e.target.closest(".pick[data-pick], .tg-more, #t-sortp")) closePick(); });

    const dpBtn = (kind, value, label, extra = "") => `<button type="button" class="dp-btn ${extra}" data-kind="${kind}" data-value="${value}" data-today="${S.today}" aria-haspopup="dialog">${label}</button>`;
    function inline(t) {   // the one or two moves that matter most for where the task is now
      if (t.status === "deleted") return `<span class="t-inline"><button type="button" class="mini on" data-a="restore">Restore to today</button><button type="button" class="mini" data-a="restore-tomorrow">Restore for tomorrow</button><button type="button" class="mini t-del" data-a="purge">Delete for good</button></span>`;
      if (t.status === "parked") return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Back to today</button>${dpBtn("when", "", "Schedule…", "mini")}</span>`;
      if (live(t) && t.day > S.today) return `<span class="t-inline"><button type="button" class="mini on" data-a="today">Bring to today</button>${dpBtn("when", t.day, "Move…", "mini")}</span>`;
      if (isToday(t)) return `<span class="t-inline hover-only"><button type="button" class="mini" data-a="tomorrow" title="Move to tomorrow">Tomorrow</button>${dpBtn("when", "", "Later…", "mini")}<button type="button" class="mini icon t-del" data-a="delete" title="Delete (you can restore it)" aria-label="Delete">✕</button></span>`;
      return "";
    }
    // A row says only what changes what you do (2026-10-31 redesign): who to ask, a deadline, blocked, and a dot
    // for high priority. Time, notes and the rest open with the task.
    let reviewing = false, showAll = false, otherList = "";
    const CAP = 5;
    function row(t, opts = {}) {
      const over = live(t) && t.due && t.due < S.today, dueToday = t.due === S.today;
      const chips = [t.status === "blocked" ? '<span class="t-meta warn-text">Blocked</span>' : "",
        live(t) && t.day > S.today ? `<span class="t-meta">${esc(dayName(t.day))}</span>` : "",
        t.due && live(t) ? `<span class="t-meta${over ? " warn-text" : dueToday ? " due-today" : ""}">${over ? "Overdue, " : "Due "}${nice(t.due)}</span>` : "",
        t.contact ? `<span class="t-meta t-who">${esc(t.contact)}</span>` : "",
        t.status === "deleted" ? `<span class="t-meta">Deleted ${nice(t.deleted_at)}</span>` : ""].join("");
      const open = openId === t.id && t.status !== "deleted";
      return `<li class="t-row${t.status === "done" ? " done" : ""}${t.status === "deleted" ? " gone" : ""}${open ? " open" : ""}${opts.g ? " in-g" : ""}${opts.last ? " g-last" : ""}" data-id="${t.id}" data-g="${esc(opts.g || "")}" ${opts.drag ? 'draggable="true"' : ""}>
        <div class="t-main">${t.status === "deleted" ? "" : `<input type="checkbox" class="t-check" ${t.status === "done" ? "checked" : ""} aria-label="Done">`}
        <button type="button" class="t-title">${esc(t.title)}</button><span class="t-chips">${chips}</span>${inline(t)}<span class="dot${t.priority === "high" && live(t) ? "" : " no"}" ${t.priority === "high" ? 'title="High priority"' : ""}></span></div>
        ${reviewing && carried(t) && opts.drag ? `<div class="t-carry nocopy">Still relevant? <button type="button" class="mini on" data-a="keep">Keep for today</button>${dpBtn("when", "", "Move to…", "mini")}<button type="button" class="mini" data-a="park">Park</button></div>` : ""}
        ${open ? detail(t) : ""}</li>`;
    }
    function detail(t) {
      const log = t.comments.map((c) => `<li><span class="muted small">${esc(c.at)}</span> ${esc(c.text)}</li>`).join("");
      // A set picker carries a ✕ that clears it in one click
      const CLEAR = { prio: "Clear the priority", est: "Clear the time", group: "Remove from the group" };
      const pick = (k, v) => `<span class="pick-wrap"><button type="button" class="pick${v ? " set" : ""}" data-pick="${k}" data-value="${esc(v)}">${esc(pickLabel[k](v))}</button>` +
        (v ? `<button type="button" class="pick-x" data-clear="${k}" aria-label="${CLEAR[k]}" title="${CLEAR[k]}">✕</button>` : "") + "</span>";
      const later = live(t) && t.day > S.today;
      return `<div class="t-detail">
        <div class="t-fields">
          <label class="fld fld-wide"><span>Title</span><input data-f="title" value="${esc(t.title)}"></label>
          <div class="fld"><span>Priority</span>${pick("prio", t.priority)}</div>
          <div class="fld"><span>Time</span>${pick("est", t.estimate ? String(t.estimate) : "")}</div>
          <div class="fld"><span>Group</span>${pick("group", groupOf(t.group) ? t.group : "")}</div>
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
      const box = $("#t-brief"); box.hidden = !sug.length;   // only when Mantis has something to suggest
      if (!sug.length) { box.innerHTML = ""; return; }
      const body = sug.map((s) => `<details class="sug"><summary><b>${esc(s.title)}</b>${s.who ? `<span class="muted small">${esc(s.who)}</span>` : ""}</summary>
          <div class="sug-body">${s.why ? `<p>${esc(s.why)}</p>` : ""}${s.say ? `<p><b>What to say:</b> ${esc(s.say)}</p>` : ""}
          ${(s.questions || []).length ? `<p><b>Questions to ask:</b></p><ul>${s.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>` : ""}
          ${s.source ? `<p class="muted small">From: ${esc(s.source)}</p>` : ""}
          <div class="t-acts"><button type="button" class="btn" data-s="${s.id}" data-sa="add">Add to today</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="later">Tomorrow</button>
          <button type="button" class="btn-line" data-s="${s.id}" data-sa="copy">Copy</button><button type="button" class="btn-line" data-s="${s.id}" data-sa="dismiss">Dismiss</button></div></div></details>`).join("");
      box.innerHTML = `<div class="blk-h"><h2>Mantis suggests</h2></div>${body}`;
    }

    // A group's header: a chevron and its name (click to collapse or expand), the count, and, while collapsed, what
    // its rows would have said (a high-priority dot, the soonest deadline). Drag it, or Alt+↑/↓, to move the group.
    const CHEV = '<svg class="tg-chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    function groupHead(g, items, shut) {
      const ts = items.map((x) => x.t), due = ts.map((t) => t.due).filter(Boolean).sort()[0], high = ts.some((t) => t.priority === "high");
      const sum = shut && due ? `<span class="t-meta${due < S.today ? " warn-text" : due === S.today ? " due-today" : ""}">${due < S.today ? "Overdue, " : "Due "}${nice(due)}</span>` : "";
      return `<li class="t-grp${shut ? " shut" : ""}" data-g="${esc(g.id)}" draggable="true" title="Drag, or Alt+↑/↓, to move the group">` +
        `<button type="button" class="tg-tog" aria-expanded="${!shut}" title="${shut ? "Show" : "Hide"} the tasks in this group">${CHEV}<span class="tg-n">${esc(g.name)}</span></button><span class="n">${ts.length}</span>${sum}` +
        (g.card && HREF[g.card] ? `<a class="tg-card" href="${jBase}${HREF[g.card]}">Open the card</a>` : "") +
        `<button type="button" class="tg-more" data-g="${esc(g.id)}" aria-label="Group options" title="Rename or remove">⋯</button>` +
        `<span class="dot${shut && high ? "" : " no"}"${shut && high ? ' title="Has a high-priority task"' : ""}></span></li>`;
    }
    // Moves glide (2026-10-31): a row that changes place slides there; one that leaves the screen or the list drifts
    // down and fades; one that arrives fades in. Reduced motion turns this off.
    const calm = matchMedia("(prefers-reduced-motion: reduce)");
    const unitKey = (el) => (el.classList.contains("t-grp") ? "g:" + el.dataset.g : "t:" + el.dataset.id);
    const snap = () => new Map($$("#t-list > .t-row, #t-list > .t-grp").map((el) => [unitKey(el), { el, r: el.getBoundingClientRect() }]));
    let folding = null;   // the group being collapsed or expanded: its rows simply go or fade in, nothing drifts over the list
    function glide(before) {
      const fold = folding; folding = null;
      if (calm.matches || !before.size) return;
      if (fold) {
        const h = headOf(fold), shut = h && h.classList.contains("shut");
        if (h) $(".tg-chev", h).animate([{ transform: `rotate(${shut ? 0 : -90}deg)` }, { transform: `rotate(${shut ? -90 : 0}deg)` }], { duration: 200, easing: "cubic-bezier(.23,1,.32,1)" });
      }
      const seen = (r) => r.bottom > 0 && r.top < innerHeight, EASE = "cubic-bezier(.23,1,.32,1)", now = new Set();
      const ghost = ({ el, r }) => {   // the old row, lifted out of the list, drifts down and fades
        el.classList.add("t-ghost"); el.classList.remove("open", "dragging", "drop-above", "drop-below");
        Object.assign(el.style, { left: r.left + scrollX + "px", top: r.top + scrollY + "px", width: r.width + "px", height: r.height + "px" });
        document.body.appendChild(el);
        el.animate([{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(28px)" }], { duration: 360, easing: EASE }).onfinish = () => el.remove();
      };
      $$("#t-list > .t-row, #t-list > .t-grp").forEach((el) => {
        const k = unitKey(el), was = before.get(k), r = el.getBoundingClientRect(); now.add(k);
        if (!was) return void el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 220, easing: "ease-out" });
        const dy = was.r.top - r.top; if (Math.abs(dy) < 1) return;
        if (seen(was.r) && seen(r)) el.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: 320, easing: EASE });
        else if (seen(was.r)) { if (!fold) ghost(was); }   // moved off screen: the place it left shows it going
        else if (seen(r)) el.animate([{ opacity: 0, transform: `translateY(${dy > 0 ? 16 : -16}px)` }, { opacity: 1, transform: "none" }], { duration: 320, easing: EASE });
      });
      if (!fold) before.forEach((v, k) => { if (!now.has(k) && seen(v.r)) ghost(v); });
    }
    const WORD = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve"];
    // The line under the heading (2026-10-31): only what changes what to do first, from the list itself
    // ("Three are high priority, one is overdue and one is blocked."); nothing when none of it applies
    function urgency(today) {
      const c = (f) => today.filter(f).length, w = (k) => (WORD[k] || String(k)).toLowerCase();
      const parts = [[c((t) => t.priority === "high"), "high priority"], [c((t) => t.due && t.due < S.today), "overdue"],
        [c((t) => t.due === S.today), "due today"], [c((t) => t.status === "blocked"), "blocked"]].filter(([k]) => k);
      if (!parts.length) return "";
      const said = parts.map(([k, what]) => `${w(k)} ${k === 1 ? "is" : "are"} ${what}`);
      const s = said.length > 1 ? said.slice(0, -1).join(", ") + " and " + said[said.length - 1] : said[0];
      return s[0].toUpperCase() + s.slice(1) + ".";
    }
    function draw() {
      dp.close();
      const before = snap();
      const d = new Date(S.today + "T12:00");
      $("#t-date").textContent = d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
      const today = S.tasks.filter(isToday);
      // A group with no open task left anywhere forgets where it was dragged; it ranks afresh if it fills again
      S.groups.forEach((g) => { if (pinned(g) && !S.tasks.some((t) => t.group === g.id && live(t))) g.pin = null; });
      const later = S.tasks.filter((t) => live(t) && t.day > S.today).sort((a, b) => a.day.localeCompare(b.day) || byOrder(a, b));
      const parked = S.tasks.filter((t) => t.status === "parked").sort(byOrder);
      const done = S.tasks.filter((t) => t.status === "done").sort((a, b) => (b.done_at || "").localeCompare(a.done_at || ""));
      const bin = S.tasks.filter((t) => t.status === "deleted").sort((a, b) => (b.deleted_at || "").localeCompare(a.deleted_at || ""));
      const n = today.length;
      $("#t-head").textContent = n ? `${WORD[n] || n} task${n === 1 ? "" : "s"} today` : "A clear day";
      $("#t-sum").textContent = urgency(today);
      // Tasks left over from earlier days: one line for all of them, not a question on every row
      const left = today.filter(carried);
      if (!left.length) reviewing = false;
      $("#t-carry").hidden = !left.length;
      $("#t-carry-t").textContent = reviewing ? "Decide on each one below." :
        `${WORD[left.length] || left.length} task${left.length === 1 ? "" : "s"} came over from ${left.every((t) => carriedDays(t) === 1) ? "yesterday" : "earlier days"}.`;
      $("[data-carry=review]").textContent = reviewing ? "Done" : "Review";
      $("[data-carry=keep]").hidden = reviewing;
      // Groups and ungrouped tasks rank together (see key). The five-row budget counts a collapsed group as one row,
      // and a group holding the open task stays expanded, as does every group while reviewing carry-overs.
      const units = layout(today), shut = (u) => u.g.collapsed && !reviewing && !u.items.some((x) => x.t.id === openId);
      const rows = units.reduce((s, u) => s + (!u.g ? 1 : shut(u) ? 1 : u.items.length), 0);
      let budget = showAll || reviewing ? Infinity : CAP, html = "", hidden = 0;
      for (const u of units) {
        if (!u.g) { if (budget-- > 0) html += row(u.t, { drag: true }); else hidden++; continue; }
        if (budget <= 0) { hidden += u.items.length; continue; }
        const s = shut(u); html += groupHead(u.g, u.items, s);
        if (s) { budget--; continue; }
        const some = u.items.slice(0, budget); budget -= some.length; hidden += u.items.length - some.length;
        html += some.map((x, i) => row(x.t, { drag: true, g: u.g.id, last: i === some.length - 1 })).join("");
      }
      tList.innerHTML = html || '<li class="empty">Nothing on today\'s list.</li>';
      glide(before);
      const more = $("#t-more"); more.hidden = rows <= CAP || reviewing; more.textContent = showAll ? "Show fewer" : `${hidden} more`;
      $("#t-sortp").hidden = !today.some(pinned) && !S.groups.some((g) => pinned(g) && units.some((u) => u.g === g));
      // The other lists sit behind one small row of tabs, each shown only when it has something in it
      let last = "";
      $("#t-sched").innerHTML = later.map((t) => (t.day !== last ? `<li class="t-day">${esc(dayName((last = t.day)))}</li>` : "") + row(t)).join("");
      $("#t-park").innerHTML = parked.map((t) => row(t)).join("");
      $("#t-done").innerHTML = done.map((t) => row(t)).join("");
      $("#t-bin").innerHTML = bin.map((t) => row(t)).join("");
      const counts = { sched: later.length, park: parked.length, done: done.length, bin: bin.length };
      if (otherList && !counts[otherList]) otherList = "";
      Object.entries(counts).forEach(([k, c]) => {
        $(`#t-${k}-n`).textContent = c; $(`[data-l="${k}"]`).hidden = !c;
        $(`[data-l="${k}"]`).classList.toggle("on", otherList === k); $(`[data-l="${k}"]`).setAttribute("aria-selected", String(otherList === k));
        $(`#t-${k}`).hidden = otherList !== k;
      });
      brief();
      if (focusNote) { const inp = document.querySelector(`.t-row[data-id="${focusNote}"] [data-c]`); if (inp) inp.focus(); focusNote = null; }
      if (focusRow) { const b = document.querySelector(`.t-row[data-id="${focusRow}"] .t-title`); if (b) b.focus({ preventScroll: true }); focusRow = null; }
    }
    $("#t-more").addEventListener("click", () => { showAll = !showAll; draw(); });
    $("#t-other").addEventListener("click", (e) => { const b = e.target.closest("[data-l]"); if (b) { otherList = otherList === b.dataset.l ? "" : b.dataset.l; draw(); } });
    $("#t-carry").addEventListener("click", (e) => {
      const b = e.target.closest("[data-carry]"); if (!b) return;
      if (b.dataset.carry === "review") { reviewing = !reviewing; return draw(); }
      const left = S.tasks.filter((t) => isToday(t) && carried(t)), before = left.map((t) => [t, t.day, t.remind_on]);
      left.forEach((t) => { t.day = S.today; t.remind_on = ""; }); change();
      toast(`Kept ${left.length === 1 ? "it" : "all " + left.length} for today.`, () => { before.forEach(([t, day, r]) => { t.day = day; t.remind_on = r; }); change(); });
    });
    $("#t-title").addEventListener("input", (e) => $("#t-add").classList.toggle("typing", !!e.target.value.trim()));

    // Adding: one quiet line of pickers under the title (Priority, Time, Today, Due, Ask, Group); Enter adds
    const addForm = $("#t-add"), addPicks = $$(".pick[data-pick]", addForm);
    const setPick = (b, v) => { b.dataset.value = v; b.textContent = pickLabel[b.dataset.pick](v); b.classList.toggle("set", !!v); };
    addForm.addEventListener("click", (e) => { const b = e.target.closest(".pick[data-pick]"); if (b) openPick(b, (v) => setPick(b, v), { back: $("#t-title") }); });
    const addWhen = $("#t-when"), addDue = $("#t-due");
    const labelAdd = () => {
      addWhen.textContent = dayName(addWhen.dataset.value); addWhen.classList.toggle("set", !!addWhen.dataset.value && addWhen.dataset.value !== S.today);
      addDue.textContent = addDue.dataset.value ? "Due " + nice(addDue.dataset.value) : "Due"; addDue.classList.toggle("set", !!addDue.dataset.value);
    };
    addWhen.addEventListener("dp-pick", labelAdd); addDue.addEventListener("dp-pick", labelAdd);
    addForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const title = $("#t-title").value.trim(); if (!title) { $("#t-title").focus(); return; }
      const t = { id: uid(), title, status: "todo", priority: $("#t-prio").dataset.value, estimate: +($("#t-est").dataset.value || 0), due: addDue.dataset.value,
        remind_on: "", day: S.today, contact: $("#t-contact").value.trim(), comments: [], created: S.today, done_at: "", order: 0, source: "", group: $("#t-grp").dataset.value };
      schedule(t, addWhen.dataset.value);   // a new task takes its default place
      S.tasks.push(t);
      e.target.reset(); e.target.classList.remove("typing"); addPicks.forEach((b) => setPick(b, ""));
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
      if (a === "park") return withUndo(t, "Parked. Find it under Parked.", () => { t.status = "parked"; t.pin = null; openId = null; });
      if (a === "block") { t.status = "blocked"; openId = t.id; focusNote = t.id; t.comments.push({ at: S.today, text: "Marked blocked." }); return change(); }
      if (a === "unblock") { t.status = "todo"; t.comments.push({ at: S.today, text: "Unblocked." }); settle(t); return change(); }
      if (a === "comment") { const inp = rowEl.querySelector("[data-c]"); if (!inp.value.trim()) return; t.comments.push({ at: S.today, text: inp.value.trim() }); settle(t); return change(); }
      if (a === "delete") return withUndo(t, `Deleted ${name}. It stays under Recently deleted for 7 days.`, () => { t.was = t.status; t.status = "deleted"; t.deleted_at = S.today; t.pin = null; openId = null; });
      if (a === "restore") return withUndo(t, `Restored ${name} to today.`, () => { t.status = t.was === "blocked" ? "blocked" : "todo"; t.deleted_at = ""; t.was = ""; schedule(t, S.today); });
      if (a === "restore-tomorrow") return withUndo(t, `Restored ${name} for tomorrow.`, () => { t.status = "todo"; t.deleted_at = ""; t.was = ""; schedule(t, tomorrow()); });
      if (a === "purge") { S.tasks = S.tasks.filter((x) => x !== t); change(); toast(`Deleted ${name} for good.`, () => { S.tasks.push(t); change(); }); }
    }
    document.addEventListener("dp-pick", (e) => {
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      if (e.target.dataset.kind === "due") { withUndo(t, e.detail ? `Due ${nice(e.detail)}.` : "Due date removed.", () => { t.due = e.detail; settle(t); }); return; }
      const v = e.detail;
      withUndo(t, !v || v <= S.today ? `${t.status === "parked" ? "Back on" : "On"} today's list.` : `Scheduled for ${dayName(v)}. It comes back to Today then.`, () => { schedule(t, v); settle(t); });
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
        toast(sb.dataset.sa === "later" ? "Added to tomorrow." : sb.dataset.sa === "add" ? "Added to today." : "Suggestion dismissed.",
          () => { S.dismissed = S.dismissed.filter((x) => x !== s.id); if (added) S.tasks = S.tasks.filter((x) => x !== added); change(); });
        return;
      }
      const r = e.target.closest(".t-row"); if (!r) return;
      const t = task(r.dataset.id); if (!t) return;
      const cx = e.target.closest("[data-clear]");   // the ✕ on a set picker
      if (cx) {
        const k = cx.dataset.clear, f = k === "prio" ? "priority" : k === "est" ? "estimate" : "group", g = groupOf(t.group);
        withUndo(t, k === "group" ? `Removed from “${g ? g.name : "the group"}”.` : k === "prio" ? "Priority cleared." : "Time cleared.",
          () => { t[f] = k === "est" ? 0 : ""; if (f === "group") t.pin = null; settle(t); });
        return;
      }
      const pk = e.target.closest(".pick[data-pick]");   // Priority, Time or Group in an open task
      if (pk) {
        // A place set by hand outranks priority, time and due date, so changing those keeps it; a new group is a
        // new list to rank in, so the task takes its default place there
        openPick(pk, (v) => {
          const k = pk.dataset.pick, f = k === "prio" ? "priority" : k === "est" ? "estimate" : "group", nv = k === "est" ? +v || 0 : v;
          if (t[f] !== nv) { t[f] = nv; if (f === "group") t.pin = null; } settle(t); change();
        });
        return;
      }
      if (e.target.classList.contains("t-check")) {
        // Done forgets where the task was dragged; reopened, it takes its default place
        if (e.target.checked) withUndo(t, "Done. Find it under Done.", () => { t.status = "done"; t.done_at = S.today; t.pin = null; openId = null; });
        else withUndo(t, "Reopened on today's list.", () => { t.status = "todo"; t.done_at = ""; t.pin = null; if (!t.day || t.day < S.today) t.day = S.today; });
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
      if (e.key === "Enter" && e.target.matches(".t-row [data-f]")) {   // Enter in Title or Ask saves and closes the task
        e.preventDefault();
        const t = task(e.target.closest(".t-row").dataset.id); if (!t) return;
        const k = e.target.dataset.f; t[k] = e.target.value.trim(); if (k === "title" && !t.title) t.title = "Untitled task";
        settle(t); change();
      }
      if (e.altKey && (e.key === "ArrowUp" || e.key === "ArrowDown")) {   // a task moves one place within its group, or within the list
        const r = document.activeElement && document.activeElement.closest("#t-list .t-row"); if (!r) return;
        e.preventDefault();
        const units = layout(S.tasks.filter(isToday)), g = units.find((u) => u.g && u.g.id === r.dataset.g), list = g ? g.items : units;
        const i = list.findIndex((u) => u.id === "t:" + r.dataset.id), j = i + (e.key === "ArrowUp" ? -1 : 1);
        if (i < 0 || j < 0 || j >= list.length) return;
        [list[i], list[j]] = [list[j], list[i]]; pinAll(list, list[j].o); change();
        const again = document.querySelector(`.t-row[data-id="${r.dataset.id}"] .t-title`); if (again) again.focus();
      }
    });

    // A group's chevron or name collapses or expands it (remembered); ⋯ renames it, or removes it after a
    // confirmation (its tasks stay, in no group, each in its default place); both offer Undo
    tList.addEventListener("click", (e) => {
      const tog = e.target.closest(".tg-tog");
      if (tog) { const g = groupOf(tog.closest(".t-grp").dataset.g); if (!g) return; g.collapsed = !g.collapsed; folding = g.id; change();
        const again = $(`#t-list .t-grp[data-g="${CSS.escape(g.id)}"] .tg-tog`); if (again) again.focus(); return; }
      const m = e.target.closest(".tg-more"); if (!m) return;
      const g = groupOf(m.dataset.g); if (!g) return;
      openPick(m, (v) => {
        if (v === "rename") return openPick(m, (n) => { if (!n.startsWith("name:")) return; const was = g.name; g.name = n.slice(5, 85); change();
          toast(`Renamed to “${g.name}”.`, () => { g.name = was; change(); }); }, { input: { value: g.name, placeholder: "Group name" } });
        if (v !== "remove") return;
        const members = S.tasks.filter((t) => t.group === g.id), n = members.length;
        // Cancel comes first and takes the focus, so a stray Enter or click keeps the group
        openPick(m, (ok) => {
          if (ok !== "yes") return;
          const at = S.groups.indexOf(g), pins = members.map((t) => t.pin);
          S.groups.splice(at, 1); members.forEach((t) => { t.group = ""; t.pin = null; }); change();
          toast(`Removed the group “${g.name}”. Its tasks stay on your list.`, () => { S.groups.splice(at, 0, g); members.forEach((t, i) => { t.group = g.id; t.pin = pins[i]; }); change(); });
        }, { ask: `Remove “${g.name}”? ${n === 1 ? "Its task stays" : n ? `Its ${n} tasks stay` : "Nothing else changes"}${n ? " on your list, in no group." : "."}`,
          items: [["no", "Cancel"], ["yes", "Remove the group"]] });
      }, { items: [["rename", "Rename"], ["remove", "Remove group…"]] });
    });

    // Drag and drop: a group lands above a header, below a group's last row, or beside an ungrouped task. A task
    // lands where taskSpot says, inside a group or out of it. What was dropped keeps that place (its pin), whatever
    // its priority, until it leaves Today; Reset to default order forgets every such place.
    // The drop applies exactly the spot the line showed (kept from the last dragover), so a release in the gap
    // between rows still lands where the line was.
    let dragId = null, dragG = null, spot = null;
    const clearMarks = () => $$("#t-list .drop-above, #t-list .drop-below").forEach((x) => x.classList.remove("drop-above", "drop-below", "drop-in"));
    const lastRow = () => { const all = $$("#t-list > .t-row, #t-list > .t-grp"); return all[all.length - 1]; };
    const GUTTER = 34;   // the rail column left of a group's rows (style.css .t-row.in-g)
    // Where a dragged task lands. Inside a group: above or below one of its rows, or first in it (a header's lower
    // half). Outside any group: beside an ungrouped row, above a group (a header's upper half), below a group (its
    // last row's lower half, pointer in the rail column at the left), or at the end (over "Add a task"). The line
    // says which: indented for inside, full width for outside.
    function taskSpot(e, el) {
      if (!el) return { into: "", unit: "", end: true, mark: lastRow(), cls: "drop-below" };
      const b = el.getBoundingClientRect(), y = (e.clientY - b.top) / b.height;
      if (el.classList.contains("t-grp")) return y < 0.5 ? { into: "", unit: "g:" + el.dataset.g, after: false, mark: el, cls: "drop-above" }
        : { into: el.dataset.g, unit: "", first: true, mark: el, cls: "drop-below drop-in" };
      if (el.dataset.g && el.classList.contains("g-last") && y >= 0.5 && e.clientX < b.left + GUTTER) return { into: "", unit: "g:" + el.dataset.g, after: true, mark: el, cls: "drop-below" };
      const after = y >= 0.5;
      return { into: el.dataset.g || "", unit: "t:" + el.dataset.id, after, mark: el, cls: (after ? "drop-below" : "drop-above") + (el.dataset.g ? " drop-in" : "") };
    }
    const headOf = (g) => $(`#t-list .t-grp[data-g="${CSS.escape(g)}"]`);
    const lower = (e, el) => { const b = el.getBoundingClientRect(); return e.clientY >= b.top + b.height / 2; };
    function groupSpot(e, el) {   // where a dragged group would land, and which element shows the line
      if (!el) return { id: "", end: true, mark: lastRow(), cls: "drop-below" };
      if (el.classList.contains("t-grp")) return { id: "g:" + el.dataset.g, after: false, mark: el, cls: "drop-above" };
      if (el.dataset.g) { const rs = $$("#t-list .t-row").filter((x) => x.dataset.g === el.dataset.g); return { id: "g:" + el.dataset.g, after: true, mark: rs[rs.length - 1] || headOf(el.dataset.g), cls: "drop-below" }; }
      const after = lower(e, el); return { id: "t:" + el.dataset.id, after, mark: el, cls: after ? "drop-below" : "drop-above" };
    }
    tList.addEventListener("dragstart", (e) => {
      spot = null;
      const h = e.target.closest(".t-grp");
      if (h) { dragG = h.dataset.g; h.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; return; }
      const r = e.target.closest(".t-row"); if (!r) return; dragId = r.dataset.id; r.classList.add("dragging"); e.dataTransfer.effectAllowed = "move";
    });
    tList.addEventListener("dragend", () => { $$("#t-list .dragging").forEach((x) => x.classList.remove("dragging")); clearMarks(); dragId = dragG = spot = null; });
    // The drop area is the list plus the "Add a task" line under it (the end of the list)
    const dropArea = tList.closest("section") || tList;
    dropArea.addEventListener("dragover", (e) => {
      if (dragG === null && !dragId) return;
      const el = e.target.closest("#t-list > .t-row, #t-list > .t-grp"), end = !el && e.target.closest("#t-add");
      if (!el && !end) { if (spot && tList.contains(e.target)) e.preventDefault(); return; }   // a gap between rows: keep the line
      const s = dragG !== null ? (el && el.dataset.g === dragG ? null : groupSpot(e, el)) : taskSpot(e, el);
      if (!s || !s.mark || (dragId && s.unit === "t:" + dragId)) { clearMarks(); spot = null; return; }   // its own row only offers "out of the group"
      e.preventDefault(); clearMarks(); s.mark.classList.add(...s.cls.split(" ")); spot = s;
    });
    dropArea.addEventListener("drop", (e) => {
      const s = spot; if (!s) return;
      e.preventDefault(); clearMarks(); spot = null;
      const units = layout(S.tasks.filter(isToday));
      if (dragG !== null) {
        const me = units.find((u) => u.id === "g:" + dragG); if (!me) return;
        const rest = units.filter((u) => u !== me), at = s.end ? rest.length : rest.findIndex((u) => u.id === s.id); if (at < 0) return;
        rest.splice(at + (s.after ? 1 : 0), 0, me); pinAll(rest, me.o); dragG = null; return change();
      }
      const moved = task(dragId); if (!moved) return;
      const scope = (gid) => (gid ? (units.find((u) => u.id === "g:" + gid) || { items: [] }).items : units);
      const from = groupOf(moved.group) ? moved.group : "", into = s.into;
      const src = scope(from), me = src.find((u) => u.id === "t:" + dragId); if (!me) return;
      src.splice(src.indexOf(me), 1);
      let gone = -1;   // its old group empties: the group's place is where "above" or "below" that group now means
      if (from && from !== into && !src.length) { gone = units.findIndex((u) => u.id === "g:" + from); units.splice(gone, 1); }
      const dst = scope(into), i = s.first || s.end ? -1 : dst.findIndex((u) => u.id === s.unit);
      dst.splice(s.first ? 0 : s.end ? dst.length : i < 0 ? (gone < 0 ? dst.length : gone) : i + (s.after ? 1 : 0), 0, me);
      moved.group = into;
      if (carried(moved)) moved.day = S.today;   // ranking a carry-over means it is today's work now
      // A task leaving or joining a group changes that group's rank, so the groups it left and joined (and a group it
      // was dropped beside) hold their places too: the list ends exactly as the drop line showed
      const hold = from !== into ? [from, into] : [];
      if (s.unit.startsWith("g:")) hold.push(s.unit.slice(2));
      hold.map(groupOf).filter(Boolean).forEach((g) => { if (!pinned(g) && units.some((u) => u.g === g)) g.pin = 0; });   // marked; pinAll sets the real place
      pinAll(dst, moved); pinAll(src, null); pinAll(units, null);   // other dragged items keep the places they show now
      dragId = null; change();
    });
    tList.addEventListener("keydown", (e) => {   // a focused group header: Alt+↑/↓ moves the whole group one place
      const h = e.target.closest(".t-grp"); if (!h || !e.altKey || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
      e.preventDefault();
      const units = layout(S.tasks.filter(isToday)), i = units.findIndex((u) => u.id === "g:" + h.dataset.g), j = i + (e.key === "ArrowUp" ? -1 : 1);
      if (i < 0 || j < 0 || j >= units.length) return;
      [units[i], units[j]] = [units[j], units[i]]; pinAll(units, units[j].o);
      change(); const again = headOf(h.dataset.g); if (again) $(".tg-tog", again).focus();
    });
    // Reset to default order: after a confirmation, forget every place the owner dragged a task or group to (Undo
    // puts them back). The ranking itself is the plain comparison in key(): no AI, nothing leaves the page.
    $("#t-sortp").addEventListener("click", (e) => {
      const all = [...S.tasks, ...S.groups].filter(pinned), n = all.length; if (!n) return;
      openPick(e.currentTarget, (ok) => {
        if (ok !== "yes") return;
        const was = all.map((o) => o.pin);
        all.forEach((o) => (o.pin = null)); change();
        toast("Back to the default order.", () => { all.forEach((o, i) => (o.pin = was[i])); change(); });
      }, { ask: `Forget the ${n === 1 ? "place" : n + " places"} you set by hand? Everything ranks by priority, then the sooner due date, then the shorter task.`,
        items: [["no", "Cancel"], ["yes", "Reset the order"]] });
    });

    if (!served) { $("#t-offline").hidden = false; $("#t-sum").textContent = ""; }
    else fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); S.groups = (S.groups || []).filter((g) => g.id); addWhen.dataset.today = addDue.dataset.today = S.today; labelAdd(); draw(); })
      .catch(() => { $("#t-offline").hidden = false; });
    // Another part of the page changed a task (a suggested deadline was accepted): reload the list.
    document.addEventListener("mantis:tasks-changed", () => fetch("api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => { Object.assign(S, j); draw(); }).catch(() => {}));
  }

  // ---- A feature or topic card: the owner's open tasks grouped under it on Today (2026-10-31) ----
  const ct = $("#card-tasks");
  if (ct && location.protocol.startsWith("http") && window.fetch) {
    const base = ($("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    fetch(base + "api/tasks", { cache: "no-store" }).then((r) => r.json()).then((j) => {
      const g = (j.groups || []).find((x) => x.card === ct.dataset.slug); if (!g) return;
      const ts = (j.tasks || []).filter((t) => t.group === g.id && (t.status === "todo" || t.status === "blocked")).sort((a, b) => a.order - b.order);
      if (!ts.length) return;
      const day = (d) => new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
      const when = (t) => t.status === "blocked" ? "Blocked" : t.day && t.day > j.today ? "From " + day(t.day) : t.due ? "Due " + day(t.due) : "On today's list";
      $("#card-tasks-b").innerHTML = ts.slice(0, 5).map((t) => `<a class="ri" href="${base}index.html"><span class="ri-v">${esc(t.title)}</span><span class="ri-s">${when(t)}</span></a>`).join("") +
        (ts.length > 5 ? `<a class="ri" href="${base}index.html"><span class="ri-s">${ts.length - 5} more on Today</span></a>` : "");
      ct.hidden = false;
    }).catch(() => {});
  }
