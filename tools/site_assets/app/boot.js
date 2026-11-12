/* boot.js: the app loader. It fetches the live data, runs the scripts in order, and decides when to say something went wrong.
   Rule: a failure is shown only when the app is not up, and only after a short grace period, so a recoverable error in one script
   never flashes a message over a page that is about to draw. The page shows a quiet skeleton while it loads. */
(async function () {
  const main = () => document.getElementById("main");
  const GRACE = 2500, DEADLINE = 10000;   // ms: wait this long after an error, and give up on a page that has not drawn by then
  const errors = [];
  let failTimer = 0;
  const ready = () => !!window.__appReady;
  const note = (what) => { const m = String((what && what.message) || what || "error").slice(0, 200); errors.push(m); console.error("Mantis:", what); };
  const showFailure = () => {
    failTimer = 0; if (ready() || !main()) return;
    const esc = (s) => s.replace(/[<&>]/g, "");
    main().removeAttribute("aria-busy");
    main().innerHTML = `<div class="boot-fail" role="alert"><h2>Mantis could not open this page</h2><p class="muted">Open it at http://localhost:8000. If it is running, reload the page.</p><p><a class="btn2" href="index.html">Reload</a></p>${errors.length ? `<details class="muted"><summary>Details</summary><pre>${esc([...new Set(errors)].slice(0, 4).join("\n"))}</pre></details>` : ""}</div>`;
  };
  const failSoon = (ms) => { if (!failTimer && !ready()) failTimer = setTimeout(showFailure, ms); };
  addEventListener("error", (e) => { note(e.error || e.message); failSoon(GRACE); });
  addEventListener("unhandledrejection", (e) => { note(e.reason); failSoon(GRACE); });
  setTimeout(() => failSoon(0), DEADLINE);

  const get = (u) => fetch(u, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [tasks, extra, growth, filters, brief, pending, stat] = await Promise.all([
    get("api/tasks"), get("api/extra"), get("api/growth"), get("api/filters"), get("api/pull-brief"), get("api/answers/pending"), get("assets/app/static.json"),
  ]);
  window.__LIVE = { tasks, extra, growth, filters, brief, pending, stat, served: !!tasks };
  const load = (src) => new Promise((ok, bad) => { const s = document.createElement("script"); s.src = "assets/app/" + src; s.async = false; s.onload = ok; s.onerror = () => bad(new Error("Could not load " + src)); document.body.appendChild(s); });
  try { for (const f of ["data-stub.js", ...window.APP_SCRIPTS]) await load(f); }
  catch (e) { note(e); failSoon(GRACE); }
})();
