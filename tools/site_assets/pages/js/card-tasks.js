/* card-tasks: the owner's open tasks on a feature or topic card. */
Mantis.define("card-tasks", ["core"], (m_core) => {
  const { $, esc } = m_core;
  // ---- A feature or topic card: the owner's open tasks grouped under it on Today (2026-10-31) ----
  const ct = $("#card-tasks");
  if (ct && location.protocol.startsWith("http") && window.fetch) {
    const base = document.documentElement.dataset.base || "";
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
});
