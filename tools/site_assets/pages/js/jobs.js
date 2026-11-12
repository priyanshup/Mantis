/* jobs: buttons that run background jobs. */
Mantis.define("jobs", ["core", "busy"], (m_core, m_busy) => {
  const { $, $$, esc, toast } = m_core;
  const { busy } = m_busy;
  // ---- Jobs: buttons that run work in the background (MANTIS-IMP-034/035), through tools/serve.py ----
  // Any element with data-job="<type>" (and optional data-arg) starts that job. A small glass panel in
  // the corner shows it running, then the result for a few seconds; "needs you" results stay until closed.
  // The page reloads by itself when the job's rebuild lands, so the panel re-opens from the server's state.
  const jobsOn = location.protocol.startsWith("http") && window.fetch;
  const jBase = document.documentElement.dataset.base || "";
  const SEEN = "mantis-jobs-seen";
  let jPoll = null, jState = null;
  const getJState = () => jState;   // other modules read the job state through this
  const seen = () => { try { return JSON.parse(sessionStorage.getItem(SEEN) || "[]"); } catch (e) { return []; } };
  const markSeen = (id) => { try { sessionStorage.setItem(SEEN, JSON.stringify([...seen(), id].slice(-30))); } catch (e) {} };
  function hud() {
    let h = $("#jobhud");
    if (!h) { h = document.createElement("div"); h.id = "jobhud"; h.className = "nocopy"; h.setAttribute("role", "status"); h.setAttribute("aria-live", "polite"); document.body.appendChild(h); }
    return h;
  }
  const since = (iso) => { const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000)); return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`; };
  function showJobs(st) {
    jState = st;
    const h = hud(), active = st.active || [];
    $$("[data-job]").forEach((b) => {   // a button whose job is waiting or running is busy
      const busy = active.some((j) => j.type === b.dataset.job && (j.arg || "") === (b.dataset.arg || ""));
      b.disabled = busy; b.classList.toggle("busy", busy);
    });
    paintInbox(st);
    document.body.classList.toggle("job-running", active.length > 0); busy();
    if (active.length) {
      const j = active[0], more = active.length - 1;
      h.className = "nocopy show run";
      h.innerHTML = `<span class="jh-scan" aria-hidden="true"><i></i></span><div class="jh-t"><b>${esc(j.label)}</b><span>${j.state === "queued" ? "Waiting to start" : "Working… " + since(j.started || j.created)}${more ? ` · ${more} more waiting` : ""}</span></div>`;
      return true;
    }
    const fresh = (st.jobs || []).find((j) => j.ended && !seen().includes(j.id) && Date.now() - new Date(j.ended).getTime() < 5 * 60 * 1000 && mine().includes(j.id));
    if (fresh) {
      const needs = (fresh.needs_you || []).length, ok = fresh.state === "done";
      const first = (fresh.summary || "").split("\n").find((l) => l.trim()) || "";
      h.className = `nocopy show ${ok ? "ok" : needs ? "needs" : "bad"}`;
      h.innerHTML = `<span class="jh-ico" aria-hidden="true">${ok ? "✓" : needs ? "!" : "×"}</span><div class="jh-t"><b>${esc(fresh.label)} · ${ok ? "done" : needs ? `needs you (${needs})` : "stopped"}</b><span>${esc(first.replace(/^[-*•]\s*/, ""))}</span>` +
        `<a href="${jBase}${fresh.type === "pull" ? "index.html#pull-box" : "sources.html#jobs"}">${fresh.type === "pull" ? "See the brief" : "Details"}</a></div><button type="button" class="jh-x" aria-label="Close">✕</button>`;
      $(".jh-x", h).addEventListener("click", () => { markSeen(fresh.id); h.className = "nocopy"; });
      if (ok) setTimeout(() => { markSeen(fresh.id); h.classList.remove("show"); }, 6500);
      return false;
    }
    h.className = "nocopy";
    return false;
  }
  const MINE = "mantis-jobs-mine";   // jobs started from this browser, so another tab's result is not shown twice
  const mine = () => { try { return JSON.parse(localStorage.getItem(MINE) || "[]"); } catch (e) { return []; } };
  const addMine = (id) => { try { localStorage.setItem(MINE, JSON.stringify([...mine(), id].slice(-30))); } catch (e) {} };
  async function pollJobs() {
    try {
      const st = await (await fetch(jBase + "api/jobs", { cache: "no-store" })).json();
      const running = showJobs(st);
      clearTimeout(jPoll);
      if (running) jPoll = setTimeout(pollJobs, 2500);
    } catch (e) { /* server not running: the buttons say so when pressed */ }
  }
  async function startJob(type, arg, label) {
    if (!jobsOn) { toast("Open Mantis from http://localhost:8000 to use this button."); return; }
    try {
      const r = await fetch(jBase + "api/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type, arg: arg || "" }) });
      const j = await r.json();
      if (!r.ok) { toast(j.error || "Could not start that."); return; }
      addMine(j.job.id); showJobs(j); pollJobs();
    } catch (e) { toast("The Mantis server isn't running. Start it with Open Mantis.cmd."); }
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-job]");
    if (!b || b.disabled) return;
    e.preventDefault();
    if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
    const src = b.dataset.argFrom ? $(b.dataset.argFrom) : null;
    if (src && !src.value.trim()) { src.focus(); return; }   // nothing typed yet (the Ask box): do not start an empty job
    startJob(b.dataset.job, b.dataset.arg || (src ? src.value.trim() : ""), b.textContent.trim());
    if (src && src.tagName === "INPUT") src.value = "";
  });
  document.addEventListener("keydown", (e) => {   // Enter in the Ask box asks
    if (e.key === "Enter" && e.target.id === "ask-q") { e.preventDefault(); const b = $("#ask-go"); if (b) b.click(); }
  });
  // Questions: the answers you submitted wait for the next pull; Sources: the job list
  function paintInbox(st) {
    $$(".answers-strip").forEach((s) => { s.hidden = !(st.inbox || {}).answers; });
    const jl = $("#job-list");
    if (jl) {
      const icon = { done: "✓", "needs-you": "!", failed: "×", running: "…", queued: "…" };
      const name = { done: "Done", "needs-you": "Needs you", failed: "Stopped", running: "Running", queued: "Waiting" };
      // Real usage per Claude job (IMP-056): tokens and the list-price value; a subscription is not billed per token
      const tok = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? Math.round(n / 1e3) + "k" : String(n);
      const total = (u) => u ? u.input + u.output + u.cache_read + u.cache_write : 0;
      const use = (j) => j.usage ? ` · ${tok(total(j.usage))} tokens · $${j.usage.cost_usd.toFixed(2)}` : "";
      const useBody = (u) => u ? `<p class="muted small jr-use">${u.turns} turns · ${tok(u.cache_read)} re-read from cache · ${tok(u.cache_write + u.input)} new input · ${tok(u.output)} written · ` +
        `${Math.round(u.seconds / 60) || "<1"} min${u.model ? " · " + esc(u.model) : ""} · $${u.cost_usd.toFixed(2)} at list price</p>` : "";
      jl.innerHTML = (st.jobs || []).map((j) => `<details class="job-row jr-${j.state}"><summary><span class="jr-ico">${icon[j.state] || ""}</span><b>${esc(j.label)}</b>` +
        `<span class="muted small">${name[j.state] || j.state} · ${new Date(j.created).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}${j.kind === "claude" ? " · used Claude" + use(j) : " · free"}</span></summary>` +
        `<div class="jr-body">${esc(j.summary || "").replace(/\n/g, "<br>")}${(j.needs_you || []).length ? `<p><b>Needs you:</b></p><ul>${j.needs_you.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}${useBody(j.usage)}</div></details>`).join("") ||
        '<p class="empty">No jobs yet. Buttons across the site start them.</p>';
      const week = (st.jobs || []).filter((j) => j.usage && Date.now() - new Date(j.created) < 7 * 864e5);
      const wk = week.length ? ` · last 7 days: ${week.length} measured job${week.length === 1 ? "" : "s"}, ${tok(week.reduce((s, j) => s + total(j.usage), 0))} tokens, $${week.reduce((s, j) => s + j.usage.cost_usd, 0).toFixed(2)} at list price` : "";
      const q = $("#job-quota"); if (q) q.textContent = `${st.claude_today} of ${st.cap} Claude jobs used today${wk}${st.agent ? "" : " · Claude Code not found on this machine"}`;
    }
  }
  if (jobsOn) pollJobs();
  return { startJob, jobsOn, jBase, getJState };
});
