/* platform.js: what every feature builds on. A feature never fetches, builds a dialog or binds a click by itself.
   Api       requests that fail with a sentence the owner can read.
   UI.action a button carries data-act="name"; the feature registers UI.action("name", handler). An unregistered name says so.
   UI.dialog a form in a sheet: fields, validation, a busy state, and the server's error shown inside it.
   Live      re-read some of the server's data after a save, rebuild the screens' data, and redraw the current tab. */
const Api = (() => {
  const call = async (path, opts) => {
    let r;
    try { r = await fetch(path, opts); } catch (e) { throw new Error("Could not reach Mantis. Open it at http://localhost:8000."); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || `That did not work (${r.status}).`);
    return j;
  };
  return { get: (p) => call(p, { cache: "no-store" }), post: (p, body) => call(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }) };
})();

Object.assign(UI, (() => {
  const actions = {};
  const action = (name, fn) => { actions[name] = fn; };
  document.addEventListener("click", (e) => {
    const el = e.target.closest && e.target.closest("[data-act]"); if (!el || el.disabled) return;
    const fn = actions[el.dataset.act];
    if (!fn) { console.warn(`No action registered for data-act="${el.dataset.act}"`); toast("That control is not connected yet."); return; }
    e.preventDefault(); e.stopPropagation();
    Promise.resolve(fn(el, e)).catch((er) => toast((er && er.message) || String(er)));
  }, true);

  /* ---- dialog ---- */
  let open = null;
  const closeDialog = () => { if (!open) return; const { prev } = open; document.getElementById("layer").innerHTML = ""; open = null; if (prev && prev.focus) prev.focus(); };
  const labelOf = (f, v) => ((f.options || []).find((o) => String(o[0]) === String(v)) || [v, v])[1];
  const chip = (f, v) => `<span class="mchip" data-v="${esc(v)}">${esc(labelOf(f, v))}<button type="button" class="mx" data-dlg-rm aria-label="Remove ${esc(labelOf(f, v))}">×</button></span>`;
  const control = (id, f) => {
    const v = f.value ?? "", name = `name="${f.name}" id="${id}-${f.name}"`;
    if (f.type === "select") return `<select class="field" ${name}>${f.options.map(([val, lab]) => `<option value="${esc(val)}"${String(val) === String(v) ? " selected" : ""}>${esc(lab)}</option>`).join("")}</select>`;
    if (f.type === "textarea") return `<textarea class="field" ${name} rows="3" placeholder="${esc(f.placeholder || "")}">${esc(v)}</textarea>`;
    if (f.type === "checks") return `<div class="checks">${f.options.map(([val, lab]) => `<label class="chk"><input type="checkbox" name="${f.name}" value="${esc(val)}"${(v || []).includes(val) ? " checked" : ""}><span>${esc(lab)}</span></label>`).join("")}</div>`;
    if (f.type === "multi") return `<div class="multi" data-multi="${f.name}"><div class="chips-in">${(v || []).map((x) => chip(f, x)).join("")}<input class="multi-in" list="${id}-${f.name}-l" placeholder="${esc(f.placeholder || "Type and press Enter")}" autocomplete="off" aria-label="${esc(f.label)}"></div><datalist id="${id}-${f.name}-l">${(f.options || []).map((o) => `<option value="${esc(o[1])}">`).join("")}</datalist></div>`;
    return `<input class="field" ${name} type="${f.type || "text"}" value="${esc(v)}" placeholder="${esc(f.placeholder || "")}"${f.required ? " required" : ""} autocomplete="off">`;
  };
  const field = (id, f) => `<div class="dlg-f${f.wide ? " wide" : ""}"><label class="lbl" for="${id}-${f.name}">${esc(f.label)}${f.required ? " *" : ""}</label>${control(id, f)}${f.hint ? `<small class="hint">${esc(f.hint)}</small>` : ""}</div>`;
  const read = (form, fields) => {
    const out = {};
    fields.forEach((f) => {
      if (f.type === "checks") out[f.name] = [...form.querySelectorAll(`input[name="${f.name}"]:checked`)].map((x) => x.value);
      else if (f.type === "multi") {
        const box = form.querySelector(`[data-multi="${f.name}"]`), typed = box.querySelector(".multi-in").value.trim(), vals = [...box.querySelectorAll(".mchip")].map((c) => c.dataset.v);
        if (typed) { const hit = (f.options || []).find((o) => o[1].toLowerCase() === typed.toLowerCase()); const v = hit ? hit[0] : (f.free === false ? null : typed); if (v && !vals.includes(v)) vals.push(v); }
        out[f.name] = vals;
      } else out[f.name] = (form.elements[f.name].value || "").trim();
    });
    return out;
  };
  const dialog = ({ title, intro = "", fields = [], submit = "Save", extra = "", onSubmit }) => {
    closeDialog();
    const id = "dlg" + Date.now().toString(36), prev = document.activeElement;
    document.getElementById("layer").innerHTML = `<div class="scrim" data-dlg-close></div><form class="sheet dlg" role="dialog" aria-modal="true" aria-labelledby="${id}-t" novalidate>
      <h2 id="${id}-t">${esc(title)}</h2>${intro ? `<p class="muted u-mb12">${esc(intro)}</p>` : ""}<div class="dlg-grid">${fields.map((f) => field(id, f)).join("")}</div>
      <p class="dlg-err" role="alert" hidden></p><div class="acts"><button class="btn2" type="submit">${esc(submit)}</button><button class="link" type="button" data-dlg-close>Cancel</button>${extra}</div></form>`;
    const form = document.querySelector("#layer form.dlg"), err = form.querySelector(".dlg-err"), go = form.querySelector("[type=submit]");
    const say = (m) => { err.textContent = m; err.hidden = !m; };
    open = { prev, form, fields, say };
    const addTyped = (box) => {
      const f = fields.find((x) => x.name === box.dataset.multi), inp = box.querySelector(".multi-in"), t = inp.value.trim().replace(/,$/, ""); if (!t) return;
      const hit = (f.options || []).find((o) => o[1].toLowerCase() === t.toLowerCase()), v = hit ? hit[0] : (f.free === false ? null : t);
      inp.value = ""; if (v === null) { say(`"${t}" is not in the list.`); return; }
      if (![...box.querySelectorAll(".mchip")].some((c) => c.dataset.v === String(v))) inp.insertAdjacentHTML("beforebegin", chip(f, v));
    };
    form.addEventListener("keydown", (e) => {
      if (e.target.classList.contains("multi-in") && (e.key === "Enter" || e.key === ",")) { e.preventDefault(); addTyped(e.target.closest("[data-multi]")); return; }
      if (e.key === "Escape") { e.stopPropagation(); closeDialog(); return; }
      if (e.key === "Tab") { const f = [...form.querySelectorAll("input,select,textarea,button")].filter((x) => !x.disabled && x.offsetParent !== null || x === document.activeElement); if (!f.length) return; const a = f[0], z = f[f.length - 1]; if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); } else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); } }
    });
    form.addEventListener("change", (e) => { if (e.target.classList.contains("multi-in")) addTyped(e.target.closest("[data-multi]")); });
    form.addEventListener("click", (e) => { const rm = e.target.closest("[data-dlg-rm]"); if (rm) { rm.closest(".mchip").remove(); return; } if (e.target.closest("[data-dlg-close]")) closeDialog(); });
    document.querySelector("#layer .scrim").addEventListener("click", closeDialog);
    form.addEventListener("submit", async (e) => {
      e.preventDefault(); say("");
      const v = read(form, fields), miss = fields.find((f) => f.required && (Array.isArray(v[f.name]) ? !v[f.name].length : !v[f.name]));
      if (miss) { say(`${miss.label} is needed.`); const el = form.querySelector(`[name="${miss.name}"], [data-multi="${miss.name}"] input`); if (el) el.focus(); return; }
      go.disabled = true; const label = go.textContent; go.textContent = "Saving…";
      try { await onSubmit(v); closeDialog(); } catch (er) { say(er.message || "That did not work."); go.disabled = false; go.textContent = label; }
    });
    const first = form.querySelector("input:not([type=checkbox]),select,textarea"); if (first) first.focus();
    return { values: () => read(form, fields), say };
  };
  const values = () => (open ? read(open.form, open.fields) : null);
  const current = () => (open ? { say: open.say, values } : null);   // the dialog on screen, for buttons inside it
  const confirm = ({ title, text, yes = "Delete", onYes }) => dialog({ title, intro: text, submit: yes, onSubmit: onYes });
  /* hover intent: show something after a short delay only if the pointer is still on the same element, and take it away the moment it
     is not (a pending delay is cancelled on leave, and a redrawn element is noticed). Used by the meeting preview. */
  const hoverIntent = (selector, { delay = 250, show, hide }) => {
    let timer = 0, watch = 0, cur = null;
    const stop = () => { clearTimeout(timer); clearInterval(watch); if (cur) { const el = cur; cur = null; hide(el); } };
    document.addEventListener("mouseover", (e) => {
      const el = e.target.closest && e.target.closest(selector); if (el && el === cur) return;
      stop(); if (!el || !matchMedia("(hover: hover)").matches) return;
      timer = setTimeout(() => {
        if (!el.isConnected || !el.matches(":hover")) return;
        cur = el; show(el);
        watch = setInterval(() => { if (!cur || !cur.isConnected || !cur.matches(":hover")) stop(); }, 120);
      }, delay);
    });
    ["scroll", "wheel", "click", "keydown", "dragstart"].forEach((n) => addEventListener(n, stop, { capture: true, passive: true }));
    document.addEventListener("mouseleave", stop); addEventListener("blur", stop);
    return stop;
  };

  /* screens run code after they are drawn: UI.onShow("meetings", fn). The shell calls UI.shown(name) once the markup is in place. */
  const shows = {};
  const onShow = (name, fn) => { (shows[name] = shows[name] || []).push(fn); };
  const shown = (name) => (shows[name] || []).forEach((fn) => { try { fn(); } catch (e) { console.error(`onShow ${name}:`, e); } });
  return { action, dialog, confirm, closeDialog, current, hoverIntent, onShow, shown };
})());

/* ---- Live: re-read data after a save ---- */
const Live = (() => {
  const ENDPOINTS = { extra: "api/extra", growth: "api/growth", filters: "api/filters", tasks: "api/tasks", brief: "api/pull-brief", pending: "api/answers/pending" };
  const hooks = [];
  const onRefresh = (fn) => hooks.push(fn);
  const refresh = async (parts = ["extra"], known = {}, { redraw = true } = {}) => {
    const got = {};
    await Promise.all(parts.map(async (p) => { got[p] = known[p] || await Api.get(ENDPOINTS[p]); }));
    Object.assign(window.__LIVE, got);
    window.rebuildLive();
    hooks.forEach((fn) => fn(parts));
    if (redraw) show((location.hash || "#today").slice(1));
  };
  return { refresh, onRefresh };
})();
