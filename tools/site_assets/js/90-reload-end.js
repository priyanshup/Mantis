  // ---- Live reload when served by tools/serve.py: checks only while the tab is visible ----
  if (location.protocol.startsWith("http") && window.fetch) {
    const base = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    let ver = null;
    const check = () => fetch(base + "version.txt", { cache: "no-store" }).then((r) => r.text()).then((v) => {
      if (ver && v !== ver) location.reload(); ver = v;
    }).catch(() => {});
    setInterval(() => { if (document.visibilityState === "visible") check(); }, 3000);
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") check(); });
    check();
  }
})();
