const { JSDOM } = require("jsdom"); const base = "http://localhost:8000/";
(async () => { const dom = await JSDOM.fromURL(base, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true,
 beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, base).href, o); w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }); w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.scrollTo = () => {}; } });
 await new Promise(r => setTimeout(r, 2500)); const w = dom.window, d = w.document;
 const waiting = [...d.querySelectorAll("#main h2")].some(h => h.textContent === "Waiting on");
 w.location.hash = "#sources"; w.dispatchEvent(new w.HashChangeEvent("hashchange")); await new Promise(r => setTimeout(r, 500));
 const firstCol = [...d.querySelectorAll("#main .col")][0].querySelector("h2").textContent;
 console.log(JSON.stringify({ todayHasWaiting: waiting, sourcesFirstColumnStartsWith: firstCol, tabs: [...d.querySelectorAll("#nav button")].map(b => b.dataset.t) })); process.exit(0); })();
