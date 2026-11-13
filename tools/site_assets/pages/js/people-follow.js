/* people-follow: follow-up rows, their buttons, and the People page's per-person lists. */
Mantis.define("people-follow", ["core", "jobs", "people-live", "people-brief"], (m_core, m_jobs, m_live, m_brief) => {
  const { $, $$, esc } = m_core;
  const { jBase } = m_jobs;
  const { xOn, xHere, xPost, loadX, dShort, ago, first } = m_live;
  const { briefLinks } = m_brief;
  const bus = m_core.bus;
  function fuRow(f) {
    return `<li class="fu" data-fu="${f.id}"><div class="fu-t"><span class="pill ${f.kind === "wait" ? "w-review" : "w-jira"} plain">${f.kind === "wait" ? "Waiting" : "Raise"}</span><b>${esc(f.topic)}</b>` +
      `<span class="muted small">open ${ago(f.created)}${f.raised.length ? ` · raised ${f.raised.length}×, last ${dShort(f.raised[f.raised.length - 1])}` : ""}${f.chase ? ` · chase ${dShort(f.chase)}` : ""}</span></div>` +
      (f.detail ? `<p class="muted small fu-d">${esc(f.detail)}</p>` : "") +
      `<span class="fu-acts"><button type="button" class="mini" data-fa="raised" title="You brought it up today; it stays open">Raised today</button><button type="button" class="mini on" data-fa="done">Done</button><button type="button" class="mini icon" data-fa="delete" aria-label="Remove" title="Remove">✕</button></span></li>`;
  }
  const stepRow = (s) => `<li class="fu step"><div class="fu-t"><span class="pill s-none plain">Step</span><span>${esc(s.step)}</span><a class="muted small" href="${jBase}features/${s.card}.html">${esc(s.card_title)}</a><span class="muted small">${esc(s.status || "open")}${s.due ? ` · due ${dShort(s.due)}` : ""}</span></div></li>`;
  // People page: counts and lists per person
  function paintPeople(d) {
    $$(".person").forEach((card) => {
      const name = card.dataset.name, g = (d.followups || {})[name] || { items: [], steps: [] };
      const ms = (d.meetings || []).filter((m) => (m.attendees || []).some((a) => a.toLowerCase() === name.toLowerCase() || first(name).toLowerCase() === a.toLowerCase()));
      const n = g.items.length + g.steps.length, badge = $(".pp-n", card);
      badge.hidden = !n; badge.textContent = n ? `${n} open` : "";
      $(".pp-live", card).innerHTML = (ms.length ? `<p class="muted small">Meets you: ${ms.map((m) => `${esc(m.name)} (${esc(m.day)}${m.next ? ", next " + dShort(m.next) : ""})`).join("; ")}</p>` : "") +
        (n ? `<ul class="fu-list">${g.items.map(fuRow).join("")}${g.steps.map(stepRow).join("")}</ul>` : "") +
        (briefLinks(name) ? `<div class="chips">${briefLinks(name)}</div>` : "");
    });
  }
  bus.on("people:data", paintPeople);
  if (xOn) {
    document.addEventListener("click", (e) => {
      const fb = e.target.closest("[data-fa]");
      if (fb) { const id = fb.closest("[data-fu]").dataset.fu; xPost("api/followups", { action: fb.dataset.fa, id }, { raised: "Noted: raised today. It stays open until done.", done: "Closed.", delete: "Removed." }[fb.dataset.fa]); return; }
      const pa = e.target.closest(".pp-add");
      if (pa) { const t = prompt(`Follow-up with ${pa.dataset.person}: what do you want to raise or chase?`); if (t) xPost("api/followups", { action: "add", person: pa.dataset.person, topic: t }, "Follow-up added."); }
    });
    const pf = $("#pp-filter");
    if (pf) pf.addEventListener("input", () => { const q = pf.value.toLowerCase(); $$(".person").forEach((c) => { c.hidden = q && !c.textContent.toLowerCase().includes(q); }); });
    if (location.hash && !location.hash.includes("=")) setTimeout(() => { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView({ block: "center" }); }, 300);
    if (xHere()) loadX();
  }
  return { fuRow, stepRow };
});
