// Smoke test: load the live site in jsdom, visit each tab, report console errors and what rendered.
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2] || "http://localhost:8000/";
const tabs = (process.argv[3] || "today,meetings,features,questions,sources,growth").split(",");
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", (e) => errors.push("jsdomError: " + String(e.message).split("\n")[0]));
vc.on("error", (...a) => errors.push("console.error: " + a.join(" ").slice(0, 200)));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const dom = await JSDOM.fromURL(base, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(win) { win.fetch = (u, o) => fetch(new URL(u, base).href, o); win.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }); } });
  const w = dom.window;
  w.matchMedia = w.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
  w.IntersectionObserver = w.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };
  w.ResizeObserver = w.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
  w.scrollTo = () => {}; w.Element.prototype.scrollIntoView = () => {}; w.Element.prototype.animate = w.Element.prototype.animate || (() => ({ finished: Promise.resolve(), cancel() {}, onfinish: null }));
  await sleep(2500);
  const out = {};
  for (const t of tabs) {
    w.location.hash = "#" + t; w.dispatchEvent(new w.HashChangeEvent("hashchange"));
    await sleep(500);
    const m = w.document.getElementById("main");
    out[t] = { elements: m.querySelectorAll("*").length, text: m.textContent.replace(/\s+/g, " ").trim().length, inline_style: m.querySelectorAll("[style]").length, h: (m.querySelector("h1,h2") || {}).textContent };
  }
  console.log(JSON.stringify({ tabs: out, nav: [...w.document.querySelectorAll("#nav a")].map((a) => a.textContent.trim()), errors: [...new Set(errors)].slice(0, 15) }, null, 1));
  w.close(); process.exit(0);
})().catch((e) => { console.log("FAIL", e.message); process.exit(1); });
