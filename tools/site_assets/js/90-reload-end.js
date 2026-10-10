  // ---- Live reload when served by tools/serve.py ----
  if (location.protocol.startsWith("http") && window.fetch) {
    const base = (document.querySelector("link[rel=stylesheet]").getAttribute("href") || "").replace("assets/style.css", "");
    let ver = null;
    setInterval(() => fetch(base + "version.txt", { cache: "no-store" }).then((r) => r.text()).then((v) => {
      if (ver && v !== ver) location.reload(); ver = v;
    }).catch(() => {}), 2000);
  }
})();
