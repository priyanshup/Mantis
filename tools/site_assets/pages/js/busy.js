/* busy: an orange sweep along the header while a request is slow. */
Mantis.define("busy", ["core"], (m_core) => {
  const { $ } = m_core;
  // ---- Something is on its way: an orange sweep along the header's bottom edge (2026-10-31). It shows for any
  // request slower than 150 ms and while a background job runs; the page's own reload check never trips it.
  const busyEl = $("#busy");
  let inflight = 0, busyT = null;
  const busy = () => busyEl && busyEl.classList.toggle("on", inflight > 0 || document.body.classList.contains("job-running"));
  if (busyEl && window.fetch) {
    const f0 = window.fetch.bind(window);
    window.fetch = (u, ...rest) => {
      if (String(u).includes("version.txt")) return f0(u, ...rest);
      inflight++; clearTimeout(busyT); busyT = setTimeout(busy, 150);
      return f0(u, ...rest).finally(() => { inflight--; clearTimeout(busyT); busy(); });
    };
  }
  return { busy };
});
