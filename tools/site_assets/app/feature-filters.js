/* feature-filters.js: add, edit, test and remove what a pull reads from Jira and Confluence (the Sources tab). Saved through POST api/filters. */
(() => {
  const TYPES = [["jira", "Jira search"], ["confluence", "Confluence page or folder"]];
  const find = (id) => ((((window.__LIVE || {}).filters || {}).filters) || []).find((f) => f.id === id);
  const fields = (f = {}) => [
    { name: "label", label: "Name", required: true, value: f.label || "", placeholder: "Secondary features", wide: true },
    { name: "type", label: "Reads from", type: "select", options: TYPES, value: f.type || "jira", wide: true },
    { name: "value", label: "What to read", type: "textarea", required: true, value: f.value || "", wide: true, placeholder: "project = CUD AND component = Secondary", hint: "Jira: a JQL search. Confluence: a page or folder address or its number." },
  ];
  const apply = async (res) => { await Live.refresh(["filters"], { filters: res }); };
  const save = (v, f) => Api.post("api/filters", f ? { action: "set", id: f.id, label: v.label, value: v.value, type: v.type } : { action: "add", label: v.label, value: v.value, type: v.type, active: true }).then(apply).then(() => toast(f ? "Filter saved." : "Filter added. The next pull uses it."));
  const test = async () => {
    const d = UI.current(), v = d.values(); if (!v.value) { d.say("Say what to read first."); return; }
    d.say("Checking…"); const r = await Api.post("api/filters", { action: "test", id: "", type: v.type, value: v.value });
    d.say(`Matches ${r.count} item${r.count === 1 ? "" : "s"} right now.${(r.sample || []).length ? " For example: " + r.sample.slice(0, 2).join("; ") : ""}`);
  };
  UI.action("filter-new", () => { UI.dialog({ title: "New filter", intro: "A pull reads everything this matches and tells you what is new or changed.", fields: fields(), submit: "Add filter", onSubmit: (v) => save(v), extra: `<button type="button" class="link" data-act="filter-test">Check it</button>` }); });
  UI.action("filter-edit", (el) => {
    const f = find(el.dataset.fid); if (!f) return;
    UI.dialog({ title: "Edit filter", fields: fields(f), submit: "Save", onSubmit: (v) => save(v, f),
      extra: `<button type="button" class="link" data-act="filter-test" data-fid="${esc(f.id)}">Check it</button><button type="button" class="link danger" data-act="filter-remove" data-fid="${esc(f.id)}">Remove</button>` });
  });
  UI.action("filter-test", () => test().catch((er) => UI.current() && UI.current().say(er.message)));
  UI.action("filter-remove", (el) => {
    const f = find(el.dataset.fid); if (!f) return;
    UI.confirm({ title: `Remove ${f.label}?`, text: "Pulls stop reading it. What it already brought in stays.", yes: "Remove filter",
      onYes: async () => { await apply(await Api.post("api/filters", { action: "remove", id: f.id })); toast("Filter removed."); } });
  });
})();
