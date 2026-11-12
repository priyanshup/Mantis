// Click through the main interactions after load and report any script error. Writes nothing to the server (fetch POST is stubbed).
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2] || "http://localhost:8000/"; const errors = []; const vc = new VirtualConsole();
vc.on("jsdomError", (e) => errors.push(String(e.message).split("\n")[0] + " @ " + String((e.detail && e.detail.stack) || "").split("\n").slice(1, 3).join(" | ")));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const dom = await JSDOM.fromURL(base, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => (o && o.method === "POST") ? Promise.resolve({ ok: true, json: async () => ({}) }) : fetch(new URL(u, base).href, o);
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.CSS = { escape: (s) => String(s) }; w.scrollTo = () => {}; w.Element.prototype.animate = () => ({ finished: Promise.resolve(), cancel() {}, onfinish: null }); w.HTMLElement.prototype.scrollIntoView = () => {}; } });
  const w = dom.window, d = w.document; await sleep(2500);
  const seen = new Set(); const snap = () => d.querySelectorAll("*").forEach((el) => { el.classList.forEach((c) => seen.add("." + c)); if (el.id) seen.add("#" + el.id); });
  const steps = []; const step = async (name, fn) => { const before = errors.length; try { await fn(); } catch (e) { errors.push(name + ": " + e.message); } await sleep(350); snap(); steps.push(`${name}: ${errors.length === before ? "ok" : "ERRORS"}`); };
  const click = (el) => el && el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true }));
  await step("tick first task", () => click(d.querySelector("#main .ck")));
  await step("open command palette", () => { click(d.querySelector("#b-find")); });
  await step("close palette (Esc)", () => d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true })));
  await step("toggle theme", () => { click(d.querySelector("#b-theme")); if (!d.documentElement.dataset.theme) throw new Error("theme not set"); });
  await step("toggle theme back", () => click(d.querySelector("#b-theme")));
  for (const t of ["meetings", "features", "questions", "sources", "growth", "promotions", "today"]) {
    await step("tab " + t, () => { w.location.hash = "#" + t; w.dispatchEvent(new w.HashChangeEvent("hashchange")); });
    await step("  click first control on " + t, () => { const b = d.querySelector("#main button:not(.ck)"); click(b); });
  }
  await step("palette: type a query and list results", async () => { click(d.querySelector("#b-find")); await sleep(200); const i = d.querySelector("#cmdq"); if (!i) throw new Error("no palette input"); i.value = "a"; i.dispatchEvent(new w.Event("input", { bubbles: true })); await sleep(200); const n = d.querySelectorAll(".srch li").length; if (!n) throw new Error("palette lists nothing"); d.dispatchEvent(new w.KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
  await step("questions: expand first, regroup by feature and meeting", async () => { w.location.hash = "#questions"; w.dispatchEvent(new w.HashChangeEvent("hashchange")); await sleep(400); click(d.querySelector("[data-qx]")); for (const g of ["Feature", "Meeting", "Who"]) { click(d.querySelector(`[data-qg="${g}"]`)); await sleep(150); } if (!d.querySelector("#ql .qr")) throw new Error("no questions listed"); });
  await step("people panel lists people", async () => { click(d.querySelector("#b-people")); await sleep(300); const i = d.querySelector("#pq"); if (!i) throw new Error("no people search"); if (!d.querySelectorAll("#pl li").length) throw new Error("no people"); i.value = "a"; i.dispatchEvent(new w.Event("input", { bubbles: true })); await sleep(150); });
  await step("features tab lists followed features", async () => { w.location.hash = "#features"; w.dispatchEvent(new w.HashChangeEvent("hashchange")); await sleep(400); if (!d.querySelectorAll("#main .frow").length) throw new Error("no feature rows"); });
  await step("feature page: every tab has cards", async () => { w.eval('ST.curF = (FEATS[0] || {}).slug'); w.location.hash = "#promotions"; w.dispatchEvent(new w.HashChangeEvent("hashchange")); await sleep(400);
    for (const t of ["Overview", "Epic and stories", "Pages", "Overview"]) { click(d.querySelector(`[data-ft="${t}"]`)); await sleep(250); if (!d.querySelector("#fbody .card")) throw new Error("no cards on " + t); } });
  await step("meetings: open a meeting, filter by day", async () => { w.location.hash = "#meetings"; w.dispatchEvent(new w.HashChangeEvent("hashchange")); await sleep(400); click(d.querySelector(".mrow")); click(d.querySelector("[data-mday]:not([aria-pressed='true'])")); await sleep(200); if (!d.querySelector("#mdet")) throw new Error("no meeting detail"); });
  await step("open people panel", () => click(d.querySelector("#b-people")));
  await step("open menu", () => click(d.querySelector("#b-menu")));
  console.log(steps.join("\n")); console.log("errors:", JSON.stringify([...new Set(errors)].slice(0, 8), null, 1)); if (process.env.SEEN_OUT) require("fs").writeFileSync(process.env.SEEN_OUT, JSON.stringify([...seen])); process.exit(0);
})();
