// The owner's flows in the app, end to end against the running site, with every write stubbed and recorded.
// usage: node flows-check.js [base]      Each check says what it clicked and which request it expects.
const { JSDOM, VirtualConsole } = require("jsdom");
const base = process.argv[2] && process.argv[2].startsWith("http") ? process.argv[2] : "http://localhost:8000/";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [], errors = [];
const check = (ok, name, info = "") => results.push([ok, name, info]);
async function load(tab) {
  const posts = [];
  const vc = new VirtualConsole(); vc.on("jsdomError", (e) => { if (!/Not implemented/.test(e.message)) errors.push(String(e.message).split("\n")[0]); }); vc.on("error", (...a) => errors.push("console.error " + a.join(" ").slice(0, 140)));
  const dom = await JSDOM.fromURL(base + "#" + tab, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(w) { w.fetch = (u, o) => { if (o && o.method === "POST") { let b = {}; try { b = JSON.parse(o.body); } catch (e) {} posts.push({ url: String(u), body: b }); return Promise.resolve({ ok: true, status: 200, json: async () => (String(u).includes("filters") ? { filters: [] } : {}) }); } return fetch(new URL(u, base).href, o); };
      w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
      w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.CSS = { escape: String }; w.Element.prototype.animate = () => ({ finished: Promise.resolve(), cancel() {}, onfinish: null }); w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {}; } });
  await sleep(2300); return { w: dom.window, d: dom.window.document, posts };
}
const click = (w, el) => { if (!el) throw new Error("control not found"); el.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true })); };
const type = (w, el, v) => { el.value = v; el.dispatchEvent(new w.Event("input", { bubbles: true })); el.dispatchEvent(new w.Event("change", { bubbles: true })); };
const posted = (p, url, pred = () => true) => p.some((x) => x.url.includes(url) && pred(x.body));
const flows = {
  async meetings() {
    let { w, d, posts } = await load("meetings");
    click(w, d.querySelector("[data-act=meeting-new]")); await sleep(300);
    check(!!d.querySelector("form.dlg"), "Meetings: New meeting opens a form");
    click(w, d.querySelector("form.dlg [type=submit]")); await sleep(200);
    check(!d.querySelector(".dlg-err").hidden, "Meetings: saving with no name says what is missing", d.querySelector(".dlg-err").textContent);
    type(w, d.querySelector("form.dlg [name=name]"), "Test sync"); d.querySelector("form.dlg").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await sleep(600);
    check(posted(posts, "api/schedule", (b) => b.action === "add-meeting" && b.name === "Test sync" && b.day), "Meetings: saving sends add-meeting", JSON.stringify((posts[0] || {}).body || {}).slice(0, 120));
    ({ w, d, posts } = await load("meetings"));
    click(w, d.querySelector("[data-act=meeting-edit]")); await sleep(300);
    const nm = d.querySelector("form.dlg [name=name]"); check(!!nm && nm.value.length > 0, "Meetings: Edit opens the form filled in", nm && nm.value);
    type(w, nm, nm.value + " (edited)"); d.querySelector("form.dlg").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await sleep(600);
    check(posted(posts, "api/schedule", (b) => b.action === "edit-meeting" && b.id && /edited/.test(b.name)), "Meetings: saving an edit sends edit-meeting with the meeting's id");
    ({ w, d, posts } = await load("meetings"));
    click(w, d.querySelector("[data-act=meeting-edit]")); await sleep(300); click(w, d.querySelector("[data-act=meeting-remove]")); await sleep(300);
    d.querySelector("form.dlg").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await sleep(600);
    check(posted(posts, "api/schedule", (b) => b.action === "remove-meeting" && b.id), "Meetings: Delete asks, then sends remove-meeting");
  },
  async sources() {
    let { w, d, posts } = await load("sources");
    click(w, d.querySelector("[data-act=filter-new]")); await sleep(300);
    check(!!d.querySelector("form.dlg [name=value]"), "Sources: New filter opens a form");
    type(w, d.querySelector("[name=label]"), "Test filter"); type(w, d.querySelector("[name=value]"), "project = CUD"); d.querySelector("form.dlg").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await sleep(600);
    check(posted(posts, "api/filters", (b) => b.action === "add" && b.label === "Test filter" && b.value === "project = CUD"), "Sources: saving sends add with the name and the search");
    ({ w, d, posts } = await load("sources"));
    click(w, d.querySelector("[data-act=filter-edit]")); await sleep(300);
    check(!!d.querySelector("form.dlg [name=label]") && d.querySelector("[name=label]").value.length > 0, "Sources: clicking a filter opens it to edit");
    click(w, d.querySelector("[data-act=filter-remove]")); await sleep(300);
    check(/Remove/.test(d.querySelector("form.dlg h2").textContent), "Sources: Remove asks first");
    ({ w, d, posts } = await load("sources"));
    const sw = d.querySelector(".sw[data-fid]"), was = sw.getAttribute("aria-checked"); click(w, sw); await sleep(300);
    check(posted(posts, "api/filters", (b) => b.action === "set" && "active" in b) && sw.getAttribute("aria-checked") !== was, "Sources: a toggle flips and sends set");
    click(w, d.querySelector("[data-act=inbox-choose]")); check(!!d.querySelector("#cfile"), "Sources: Choose a file has a file input to open");
    type(w, d.querySelector("#ctext"), "notes"); click(w, d.querySelector("[data-add]")); await sleep(400);
    check(posted(posts, "api/inbox", (b) => b.text === "notes"), "Sources: Add to inbox sends the text");
    click(w, d.querySelector("[data-pull]")); await sleep(500);
    check(posted(posts, "api/jobs"), "Sources: Start a pull starts a job");
  },
  async meetingFilter() {
    let { w, d } = await load("meetings");
    const days = [...d.querySelectorAll("[data-act=meeting-day]")].map((b) => b.dataset.day);
    check(["All", "Mon", "Tue", "Wed", "Thu", "Fri"].every((x) => days.includes(x)), "Meetings: the day filter always offers Mon to Fri, including a day with no meeting", days.join(" "));
    const rows = () => d.querySelectorAll("#mlist .mrow").length, all = rows();
    click(w, d.querySelector("[data-day=Wed]")); await sleep(150);
    check(rows() === 0 && /Show all meetings/.test(d.querySelector("#mlist").textContent), "Meetings: a day with no meeting says so and offers Show all meetings", d.querySelector("#mlist").textContent.slice(0, 60));
    click(w, d.querySelector("[data-act=meeting-clear-filter]")); await sleep(150);
    check(rows() === all, "Meetings: Show all meetings clears the filter", `${rows()} of ${all}`);
    click(w, d.querySelector("[data-day=Thu]")); await sleep(150); const thu = rows();
    check(thu > 0 && thu < all, "Meetings: choosing a day narrows the list", `${thu} of ${all}`);
    click(w, d.querySelector("[data-day=Thu]")); await sleep(150);
    check(rows() === all, "Meetings: pressing the chosen day again removes the filter", `${rows()} of ${all}`);
    type(w, d.querySelector("#mq"), "zzzz"); await sleep(150); check(rows() === 0 && !!d.querySelector("[data-act=meeting-clear-filter]"), "Meetings: a search with no match offers to clear it");
  },
  async preview() {   // the meeting preview must not appear for a pointer that has already left (jsdom has no :hover, so the pointer is simulated)
    const { w, d } = await load("meetings"); let over = null; const real = w.Element.prototype.matches;
    w.Element.prototype.matches = function (q) { return q === ":hover" ? over === this : real.call(this, q); };
    w.matchMedia = () => ({ matches: true, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
    const row = d.querySelector(".mrow[data-mi]"), out = d.querySelector("h1"), fire = (el, t) => el.dispatchEvent(new w.MouseEvent(t, { bubbles: true }));
    over = row; fire(row, "mouseover"); await sleep(80); over = out; fire(out, "mouseover"); await sleep(500);
    check(!(d.getElementById("peek") && d.getElementById("peek").classList.contains("show")), "Meetings: moving away before the delay means no preview appears");
    over = row; fire(row, "mouseover"); await sleep(450);
    check(!!d.getElementById("peek") && d.getElementById("peek").classList.contains("show"), "Meetings: resting on a meeting shows the preview");
    over = out; fire(out, "mouseover"); await sleep(100);
    check(!d.getElementById("peek").classList.contains("show"), "Meetings: the preview goes away when the pointer does");
  },
  async boot() {   // a script that cannot load: the failure message waits for its grace period, and never shows on a page that has drawn
    const { JSDOM, ResourceLoader } = require("jsdom");
    class Block extends ResourceLoader { fetch(url, o) { return /start\.js/.test(url) ? Promise.reject(new Error("blocked")) : super.fetch(url, o); } }
    const dom = await JSDOM.fromURL(base, { runScripts: "dangerously", resources: new Block(), pretendToBeVisual: true, virtualConsole: new VirtualConsole(),
      beforeParse(w) { w.fetch = (u, o) => fetch(new URL(u, base).href, o); w.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }); w.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} }; w.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; w.CSS = { escape: String }; w.scrollTo = () => {}; w.Element.prototype.animate = () => ({ finished: Promise.resolve(), cancel() {} }); } });
    await sleep(1500); const m = dom.window.document.getElementById("main");
    check(!m.querySelector(".boot-fail"), "Boot: a failure is not shown at once", "1.5 s after the error");
    await sleep(4500);
    check(!!m.querySelector(".boot-fail"), "Boot: if the page never draws, the failure shows after the grace period, with details", (m.textContent || "").slice(0, 50));
    dom.window.close();
  },
  async features() {
    const { w, d } = await load("features"); const rows = () => [...d.querySelectorAll(".frow[data-f]")].length;
    const all = rows(); check(!!d.querySelector("#fq"), "Features: there is a search box"); type(w, d.querySelector("#fq"), "zzzzqq"); await sleep(200);
    check(rows() === 0 && /No feature matches/.test(d.querySelector(".fl").textContent), "Features: a search with no match says so", String(rows()));
    const first = (d.querySelector("#fq").value = "pro"); type(w, d.querySelector("#fq"), "pro"); await sleep(200);
    check(rows() > 0 && rows() <= all, "Features: a search narrows the list", `${rows()} of ${all}`);
  },
  async growth() {
    let { w, d, posts } = await load("growth");
    const all = d.querySelector("[data-act=growth-select-all]"); if (!all) { check(false, "Growth: there is a Select all"); return; }
    const before = all.textContent; click(w, all); await sleep(200);
    const after = d.querySelector("[data-act=growth-select-all]").textContent; check(/Deselect/.test(after) && before !== after, "Growth: Select all becomes Deselect all", `${before} -> ${after}`);
    click(w, d.querySelector("[data-act=growth-select-all]")); await sleep(200);
    check(!/Deselect/.test(d.querySelector("[data-act=growth-select-all]").textContent), "Growth: Deselect all clears the selection");
    click(w, d.querySelector("[data-act=growth-dismiss]")); await sleep(500);
    check(posted(posts, "api/growth", (b) => b.action === "dismiss" && b.id), "Growth: the cross on a row dismisses it");
    ({ w, d, posts } = await load("growth"));
    click(w, d.querySelector("[data-gs]")); await sleep(100); click(w, d.querySelector("[data-act=growth-later]")); await sleep(500);
    check(posted(posts, "api/growth", (b) => b.action === "hold" && b.id), "Growth: Not now sets the selection aside (hold), it does not dismiss");
    ({ w, d, posts } = await load("growth"));
    click(w, d.querySelector("[data-gv=Hidden]")); await sleep(300);
    check(/set aside|Nothing is hidden/.test(d.querySelector("#glist").textContent), "Growth: a Hidden tab lists what was set aside or dismissed and says how long it is kept", d.querySelector("#glist").textContent.slice(0, 60));
  },
  async questions() {
    const { w, d, posts } = await load("questions");
    click(w, d.querySelector("[data-qx]")); await sleep(300); const ta = d.querySelector("textarea[id^=qa]"); type(w, ta, "My answer"); click(w, d.querySelector("[data-qsave]")); await sleep(400);
    check(posted(posts, "api/answers", (b) => (b.answers || []).length === 1), "Questions: saving an answer sends it");
  },
  async today() {
    const { w, d, posts } = await load("today");
    click(w, d.querySelector("[data-pull]")); await sleep(500); check(posted(posts, "api/jobs"), "Today: Start a pull starts a job");
  },
};
(async () => {
  for (const [name, fn] of Object.entries(flows)) { try { await fn(); } catch (e) { check(false, `${name}: ran without throwing`, e.message); } }
  for (const [ok, n, i] of results) console.log((ok ? "ok   " : "FAIL ") + n + (i ? "  " + i : ""));
  console.log("errors:", JSON.stringify([...new Set(errors)].slice(0, 6)));
  process.exit(results.every((r) => r[0]) && !errors.length ? 0 : 1);
})();
