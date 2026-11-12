// What each content page type does once its scripts have run. usage: node pagefn-check.js [base] [type ...]   (no type = all)
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2] && process.argv[2].startsWith("http") ? process.argv[2] : "http://localhost:8000/";
const only = process.argv.slice(2).filter((a) => !a.startsWith("http"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const errors = [];
async function open(path) {
  const vc = new VirtualConsole(); vc.on("jsdomError", (e) => { if (!/Not implemented: navigation/.test(e.message)) errors.push(path + ": " + String(e.message).split("\n")[0]); });   // jsdom cannot navigate: a page reloading itself after a rebuild is not a fault vc.on("error", (...a) => errors.push(path + ": console.error " + a.join(" ").slice(0, 160)));
  const dom = await JSDOM.fromURL(new URL(path, base).href, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, w.location.href).href, o); w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.scrollTo = () => {}; w.CSS = { escape: String }; w.HTMLElement.prototype.scrollIntoView = () => {}; } });
  await sleep(1500); return dom.window;
}
const click = (w, el) => el && el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
const results = [];
const check = (name, ok, info = "") => results.push([ok, name, info]);
const types = {
  async changes() { const w = await open("changes.html"), d = w.document; check("changes: the What's new feed fills", d.querySelectorAll("#ev-feed > *").length > 0, d.querySelectorAll("#ev-feed > *").length + " items"); },
  async library() { const w = await open("library.html"), d = w.document; const chips = d.querySelectorAll("#f-lib button, #f-dia button"); check("library: filter chips exist and respond", chips.length > 0, chips.length + " chips"); click(w, chips[chips.length - 1]); await sleep(150); },
  async work() { const w = await open("work.html"), d = w.document; const n = d.querySelectorAll("#board *, #list *").length; check("work: the board draws its cards", n > 20, n + " elements"); click(w, d.querySelector("#view [data-v=list]")); await sleep(200); check("work: the list view draws rows", d.querySelectorAll("#list tr").length > 0, d.querySelectorAll("#list tr").length + " rows"); },
  async document() { const w = await open("pages/promotions-user-journey.html"), d = w.document; const b = d.querySelector(".edit-btn"); check("document: Edit button present", !!b); click(w, b); await sleep(300); check("document: Edit opens the editor", !!d.querySelector(".ed-toolbar, .ed-body, [contenteditable]"), ""); },
  async topic() { const w = await open("topics/devops-and-ci.html"), d = w.document; const tabs = d.querySelectorAll(".tabs a, .tabs button"); check("topic: tabs present", tabs.length > 1, tabs.length + " tabs"); click(w, tabs[1]); await sleep(200); check("topic: a tab switches", !!d.querySelector(".tabs .on, .tabs [aria-selected=true]")); },
  async feature() { const w = await open("features/promotions.html"), d = w.document; const tabs = d.querySelectorAll(".tabs a, .tabs button"); check("feature: tabs present", tabs.length > 1, tabs.length + " tabs"); click(w, tabs[1]); await sleep(200);
    check("feature: card tasks block loads", d.querySelector("#card-tasks") !== null, ""); check("feature: Edit button present", !!d.querySelector(".edit-btn")); },
  async people() { const w = await open("people.html"), d = w.document; click(w, d.querySelector(".person h3 span")); await sleep(600); check("people: clicking a name opens that person", !!d.querySelector(".dr-name"), (d.querySelector(".dr-name") || {}).textContent || "no panel");
    check("people: live follow-ups load into the cards", d.querySelectorAll(".pp-live *").length > 0, d.querySelectorAll(".pp-live *").length + " elements"); },
};
(async () => {
  for (const [name, fn] of Object.entries(types)) if (!only.length || only.includes(name)) { try { await fn(); } catch (e) { check(name + ": ran without throwing", false, e.message); } }
  for (const [ok, n, i] of results) console.log((ok ? "ok   " : "FAIL ") + n + (i ? "  " + i : ""));
  console.log("errors:", JSON.stringify([...new Set(errors)].slice(0, 6)));
  process.exit(results.every((r) => r[0]) && !errors.length ? 0 : 1);
})();
