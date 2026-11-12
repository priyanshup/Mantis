/* drafts: Draft a message to whoever can answer. */
Mantis.define("drafts", ["core"], (m_core) => {
  const { $, toast, esc, $$, copyText } = m_core;
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
  return { draftData };
});
