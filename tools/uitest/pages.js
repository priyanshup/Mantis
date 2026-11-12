// Load each static page in jsdom; report script errors and a size fingerprint. usage: node pages.js base path1 path2 ...
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2]; const paths = process.argv.slice(3);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const out = {};
  for (const p of paths) {
    const errors = [];
    const vc = new VirtualConsole();
    vc.on("jsdomError", (e) => errors.push(String(e.message).split("\n")[0].slice(0, 160)));
    vc.on("error", (...a) => errors.push("console.error: " + a.join(" ").slice(0, 160)));
    try {
      const dom = await JSDOM.fromURL(new URL(p, base).href, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
        beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, w.location.href).href, o); w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
          w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.scrollTo = () => {}; } });
      await sleep(1500);
      const d = dom.window.document;
      out[p] = { title: d.title, elements: d.body.querySelectorAll("*").length, text: d.body.textContent.replace(/\s+/g, " ").length, errors: [...new Set(errors)].slice(0, 6) };
      dom.window.close();
    } catch (e) { out[p] = { fail: String(e.message).slice(0, 120) }; }
  }
  console.log(JSON.stringify(out, null, 1)); process.exit(0);
})();
