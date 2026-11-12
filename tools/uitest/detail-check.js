// Detail pages: the side panel opens a person and the library, a feature page loads its sections. usage: node detail-check.js [base]
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2] || "http://localhost:8000/";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];
async function open(path, pre) {
  const vc = new VirtualConsole(); vc.on("jsdomError", (e) => { if (!/Not implemented: navigation/.test(e.message)) errors.push(path + ": " + String(e.message).split("\n")[0]); });   // jsdom cannot navigate: a page reloading itself after a rebuild is not a fault
  const dom = await JSDOM.fromURL(new URL(path, base).href, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, w.location.href).href, o); w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.scrollTo = () => {}; w.CSS = { escape: String }; w.HTMLElement.prototype.scrollIntoView = () => {}; } });
  await sleep(1500); return dom.window;
}
const click = (w, el) => el && el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
(async () => {
  const res = [];
  let w = await open("people.html"); let d = w.document;
  const first = d.querySelector(".person [data-person], .person h3 span, [data-person]:not(.pp-add)");
  const name = first ? first.textContent.trim() : "";
  click(w, d.querySelector(".person h3 span") || first); await sleep(700);
  const toast = (d.getElementById("toast") || {}).textContent || "";
  res.push(["people page: clicking a name opens that person", !!d.querySelector(".dr-name") && !/not in the people file/.test(toast), `${name} -> ${(d.querySelector(".dr-name") || {}).textContent || "no panel"} ${toast.trim()}`]);
  w = await open("people.html"); d = w.document; click(w, d.querySelector("[data-dopen=\"people\"]")); await sleep(700);
  res.push(["people list opens", !!d.querySelector(".dr-list .dr-row"), String(d.querySelectorAll(".dr-row").length) + " rows"]);
  w = await open("library.html"); d = w.document; res.push(["library page loads items", d.body.textContent.length > 500, String(d.body.textContent.length)]);
  // pages on the new shell: the header, the search box, the theme switch and a loaded module set (pass page paths as extra arguments)
  for (const path of process.argv.slice(3)) {
    w = await open(path); d = w.document;
    const links = d.querySelectorAll(".top nav a").length;
    click(w, d.querySelector("#kbar")); await sleep(300); const palOpen = d.getElementById("palette") && !d.getElementById("palette").hidden;
    const before = d.documentElement.dataset.theme; click(w, d.querySelector("#theme")); await sleep(200); const themed = d.documentElement.dataset.theme !== before;
    res.push([`new shell ${path}: header, search box and theme switch work`, links >= 6 && !!palOpen && themed, `nav links ${links}, palette ${palOpen ? "opens" : "stays shut"}, theme ${themed ? "switches" : "does not switch"}`]);
  }
  for (const [n, ok, info] of res) console.log((ok ? "ok   " : "FAIL ") + n + "  " + info);
  console.log("errors:", JSON.stringify([...new Set(errors)].slice(0, 6)));
  process.exit(res.every((r) => r[1]) && !errors.length ? 0 : 1);
})();
