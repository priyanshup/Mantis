/* people-live: the live data behind People, follow-ups and briefs (GET /api/extra), and the one way to change it. */
Mantis.define("people-live", ["jobs", "core"], (m_jobs, m_core) => {
  const { jobsOn, jBase } = m_jobs;
  const { $, toast, bus } = m_core;
  // Live data from tools/serve.py (GET /api/extra), changed through POST /api/followups. Whoever shows it listens
  // for "people:data" and draws; this module draws nothing.
  const X = { d: null };
  const xOn = jobsOn;   // live data is loaded where a page shows it, or when the People panel opens
  const xHere = () => $(".people-grid");
  const dShort = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : "";
  const ago = (d) => { const n = Math.round((Date.now() - new Date(d + "T12:00").getTime()) / 864e5); return n <= 0 ? "today" : n === 1 ? "1 day" : `${n} days`; };
  const first = (n) => String(n || "").split(" ")[0];
  async function xPost(path, body, msg) {
    try {
      const r = await fetch(jBase + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json();
      if (!r.ok) { toast(j.error || "That didn't work."); return null; }
      X.d = j; bus.emit("people:data", j); if (msg) toast(msg); return j;
    } catch (e) { toast("The Mantis server isn't running."); return null; }
  }
  async function loadX() {
    try { X.d = await (await fetch(jBase + "api/extra", { cache: "no-store" })).json(); bus.emit("people:data", X.d); } catch (e) {}
  }
  return { X, xOn, xHere, dShort, ago, first, xPost, loadX };
});
