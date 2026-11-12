/* sync: Confluence sync: copy only the changed sections. */
Mantis.define("sync", ["core", "jobs"], (m_core, m_jobs) => {
  const { $, copyText, copyHtml, toast } = m_core;
  const { jobsOn, jBase } = m_jobs;
  // ---- Confluence sync (MANTIS-IMP-019): copy only the sections that changed; remember what is in Confluence ----
  document.addEventListener("click", async (e) => {
    const cf = e.target.closest(".copy-field");   // Jira fields (IMP-045): Summary as text, the others formatted
    if (cf) {
      e.preventDefault(); e.stopPropagation();
      const src = $(`.jf-src[data-f="${CSS.escape(cf.dataset.f)}"]`, cf.closest(".jira"));
      if (cf.dataset.f === "Summary") copyText(src.textContent.trim()); else copyHtml(src);
      return;
    }
    const cs = e.target.closest(".copy-sec");
    if (cs) { e.preventDefault(); e.stopPropagation(); copyHtml($(".sync-body", cs.closest(".sync-sec"))); return; }
    const pb = e.target.closest("[data-publish]");
    if (!pb) return;
    e.preventDefault(); e.stopPropagation();
    if (!jobsOn) { toast("Open Mantis from http://localhost:8000 to use this."); return; }
    try {
      const r = await fetch(jBase + "api/published", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ path: pb.dataset.publish }) });
      const j = await r.json();
      const to = pb.dataset.to || "Confluence";
      toast(r.ok ? `Remembered as the version in ${to}. Next time only changed ${to === "Jira" ? "fields" : "sections"} show.` : (j.error || "That didn't work."));
    } catch (err) { toast("The Mantis server isn't running."); }
  });
});
