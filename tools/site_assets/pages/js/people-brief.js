/* people-brief: the brief and handover links shown under a person, and the viewer that opens one. */
Mantis.define("people-brief", ["core", "jobs", "people-live"], (m_core, m_jobs, m_live) => {
  const { $, $$, esc, toast, copyHtml } = m_core;
  const { jBase, getJState } = m_jobs;
  const { X, xOn, dShort, loadX } = m_live;
  function briefLinks(forName, kind) {
    const bs = ((X.d || {}).briefs || []).filter((b) => (!forName || b.for === forName) && (!kind || b.kind === kind)).slice(0, 4);
    // the date shows once: a title that already carries it ("Weekly sync, 26 Oct") gets no second date
    const dated = (t, d) => { const x = new Date(d + "T12:00"), day = String(x.getDate()), mon = x.toLocaleDateString("en-GB", { month: "short" });
      return new RegExp(`\\b${day} ${mon}\\b|\\b${mon} ${day}\\b`, "i").test(t); };
    return bs.map((b) => { const t = b.title || b.for;
      return `<button type="button" class="chip" data-brief="${b.id}">${((k) => t.toLowerCase().startsWith(k.toLowerCase()) ? esc(t) : esc(k) + " · " + esc(t))({ handover: "Handover", status: "Status", answer: "Answer" }[b.kind] || "Brief")}${dated(t, b.date) ? "" : " · " + dShort(b.date)}</button>`; }).join("");
  }
  // Brief viewer: every bullet expands to its background, source and card
  async function openBrief(id) {
    let b;
    try { b = await (await fetch(jBase + "api/brief?id=" + encodeURIComponent(id), { cache: "no-store" })).json(); } catch (e) { return; }
    if (!b || !b.sections) { toast("That brief is gone."); return; }
    const m = document.createElement("div"); m.className = "modal-wrap";
    m.innerHTML = `<div class="modal brief-modal" role="dialog" aria-label="${esc(b.title)}"><div class="bm-h"><div><p class="hello">${{ handover: "Handover", status: "Status update", answer: "Ask Mantis" }[b.kind] || "Meeting brief"} · ${dShort(b.date)}</p><h2>${esc(b.title)}</h2></div>` +
      `<span class="bar-btns"><button type="button" class="btn-line" data-bcopy>Copy</button><button type="button" class="mini icon" data-bclose aria-label="Close">✕</button></span></div>` +
      `<div class="bm-body">${b.sections.map((s) => `<h3>${esc(s.name)}</h3><ul class="bb-list">${s.bullets.map((x) => `<li><details class="bb"><summary>${esc(x.text)}</summary><div class="bb-d">${x.detail ? `<p>${esc(x.detail)}</p>` : ""}` +
        `${x.source || x.card ? `<p class="muted small">${x.source ? "From: " + esc(x.source) : ""}${x.card ? ` · <a href="${jBase}features/${esc(x.card)}.html">open the card</a>` : ""}</p>` : ""}` +
        `${x.followup ? `<span class="fu-acts" data-fu="${esc(x.followup)}"><button type="button" class="mini" data-fa="raised">Raised today</button><button type="button" class="mini on" data-fa="done">Done</button></span>` : ""}</div></details></li>`).join("")}</ul>`).join("")}</div></div>`;
    document.body.appendChild(m);
    const close = () => m.remove();
    m.addEventListener("click", (e) => { if (e.target === m || e.target.closest("[data-bclose]")) close(); });
    document.addEventListener("keydown", function k(e) { if (e.key === "Escape") { close(); document.removeEventListener("keydown", k); } });
    $("[data-bcopy]", m).addEventListener("click", () => { $$("details.bb", m).forEach((x) => (x.open = true)); copyHtml($(".bm-body", m)); });
  }
  if (xOn) {
    document.addEventListener("click", (e) => { const br = e.target.closest("[data-brief]"); if (br) openBrief(br.dataset.brief); });
    // A finished brief or handover job: refresh the lists so the new brief appears
    let lastDone = "";
    setInterval(() => { const jState = getJState(); if (!jState) return; const j = (jState.jobs || []).find((x) => ["meeting-brief", "handover"].includes(x.type) && x.ended); if (j && j.id !== lastDone) { if (lastDone) loadX(); lastDone = j.id; } }, 3000);
  }
  return { briefLinks, openBrief };
});
