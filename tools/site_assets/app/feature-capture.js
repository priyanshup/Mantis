/* feature-capture.js: quick capture from anywhere (IMP-114 item 8). Press C when no field has focus: one line, three kinds.
   Task: added to Other tasks, saved by the page's own task sync. Follow-up: "Name: what to raise", POST api/followups. Note: a file in the inbox for the next pull, POST api/inbox.
   Enter saves, Esc closes, the arrow keys move between the kinds. Nothing is lost on a wrong kind: the box stays open until the save works. */
(() => {
  const KINDS = [["task", "Task", "What needs doing"], ["followup", "Follow-up", "Name: what to raise or chase"], ["note", "Note", "A thought for the next pull"]];
  let kind = "task";
  const typing = () => /INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || "") || !!(document.activeElement && document.activeElement.isContentEditable);

  const draw = () => {
    layer.innerHTML = `<div class="scrim"></div><div class="sheet capture" role="dialog" aria-label="Quick capture"><div class="hd2"><h2>Quick capture</h2><button class="ic" aria-label="Close" data-act="close-layer"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div>
      <div class="seg cap-kinds" aria-label="Kind">${KINDS.map(([k, label]) => `<button type="button" aria-pressed="${k === kind}" data-act="capture-kind" data-kind="${k}">${label}</button>`).join("")}</div>
      <input id="capin" class="field" autocomplete="off" aria-label="Capture" placeholder="${KINDS.find((x) => x[0] === kind)[2]}">
      <p class="muted cap-hint">Enter saves. Esc closes.</p></div>`;
    layer.querySelector(".scrim").onclick = close;
    const i = $("#capin"); if (i) i.focus();
  };

  const save = async () => {
    const box = $("#capin"), v = (box && box.value || "").trim();
    if (!v) { toast("Type something first"); return; }
    if (kind === "task") {
      const k = 2000 + ST.nid++;
      ST.newTasks.push({ k, t: v, p: "medium", due: "", g: "Other tasks", ask: "", n: "", est: 0, rem: "", src: "Added by you" });
      if (typeof rerenderPlan === "function" && $("#plan")) rerenderPlan();
      close();
      toast("Task added to Other tasks", () => { ST.edits[k] = Object.assign(ST.edits[k] || {}, { del: true }); if (typeof rerenderPlan === "function" && $("#plan")) rerenderPlan(); });
      return;
    }
    if (kind === "followup") {
      const m = v.match(/^([^:]{1,40}):\s*(.+)$/);
      if (!m) { toast("Write it as Name: what to raise"); return; }
      await Api.post("api/followups", { action: "add", person: m[1].trim(), topic: m[2].trim() });
      close(); toast(`Follow-up with ${m[1].trim()} added`); return;
    }
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
    await Api.post("api/inbox", { name: `note-${stamp}.md`, text: v + "\n" });
    LV.inboxN = (LV.inboxN || 0) + 1; close(); toast("Saved to the inbox for the next pull");
  };

  UI.action("capture-open", () => { kind = "task"; draw(); });
  UI.action("capture-kind", (el) => { kind = el.dataset.kind; const v = ($("#capin") || {}).value || ""; draw(); $("#capin").value = v; });
  UI.action("capture-save", () => save());

  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.id === "capin") { e.preventDefault(); save().catch((er) => toast(er.message)); return; }
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && e.target.dataset && e.target.dataset.act === "capture-kind") {
      e.preventDefault(); const i = KINDS.findIndex((x) => x[0] === kind), n = (i + (e.key === "ArrowRight" ? 1 : KINDS.length - 1)) % KINDS.length; kind = KINDS[n][0]; draw();
      const b = layer.querySelector(`[data-kind="${kind}"]`); if (b) b.focus(); return;
    }
    if (e.key.toLowerCase() !== "c" || e.ctrlKey || e.metaKey || e.altKey || typing() || layer.innerHTML) return;
    e.preventDefault(); kind = "task"; draw();
  });
})();
