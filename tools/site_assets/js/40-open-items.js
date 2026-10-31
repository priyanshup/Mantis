  // ---- Questions page (IMP-007, 2026-10-31 redesign): For you / Waiting / Answered, grouped by who can answer ----
  const oi = $("#f-oi");
  if (oi) {
    const qs = $("#q-scope");
    let cur = "all", scope = "you";
    const match = (d, v) => v === "all" || d.dataset.kind === v || (v === "potential" && !/^(Open|Unconfirmed)$/.test(d.dataset.status)) || (v === "possible" && d.dataset.status === "Unconfirmed");
    const apply = (v) => {
      cur = v;
      $$("[data-v]", oi).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      // "Filter" like the Features page; a narrowed list names what it shows
      $("#f-oi-l").textContent = v === "all" ? "Filter" : "Filter · " + ($(`[data-v="${v}"]`, oi) || {}).textContent;
      $$("details.oi").forEach((d) => (d.hidden = !(match(d, v) && d.dataset.scope === scope)));
      $$(".q-grp").forEach((g) => {   // a person with nothing left under the filter drops out; the count shows what is left
        const n = $$("details.oi", g).filter((d) => !d.hidden).length;
        g.hidden = g.dataset.scope !== scope || !n; $(".oi-n", g).textContent = n;
      });
      $("#q-empty").hidden = scope === "closed" || $$("details.oi").some((d) => !d.hidden);
    };
    const setScope = (s) => {
      scope = s;
      $$("button", qs).forEach((b) => { b.classList.toggle("on", b.dataset.v === s); b.setAttribute("aria-selected", String(b.dataset.v === s)); });
      const t = $('[data-v="tidy"]', qs); if (t) t.hidden = s !== "tidy";
      $("#q-closed").hidden = s !== "closed"; $("#q-lists").hidden = s === "closed"; $("#f-oi-pop").hidden = s === "closed" || s === "tidy";
      $("#q-focus").hidden = s !== "you";
      apply(cur);
    };
    qs.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) setScope(b.dataset.v); });
    oi.addEventListener("click", (e) => { const b = e.target.closest("[data-v]"); if (b) { apply(b.dataset.v); $("#f-oi-pop").open = false; } });
    const h = location.hash;
    const linked = h.startsWith("#k=") ? $(`details.oi[data-k="${CSS.escape(h.slice(3))}"]`) : h.length > 1 && /^#[A-Z]/.test(h) ? document.getElementById(h.slice(1)) : null;
    setScope(linked && linked.dataset.scope ? linked.dataset.scope : h === "#closed" ? "closed" : h === "#tidy" ? "tidy" : h.startsWith("#who=") ? "others" : "you");
    if (h === "#waiting") apply("potential");
    if (h === "#possible") apply("possible");
    if (linked && linked.tagName === "DETAILS") { linked.open = true; linked.classList.add("hl"); requestAnimationFrame(() => linked.scrollIntoView({ block: "center" })); }

    // Answer one by one (Superhuman-style triage): one question at a time, 1-3 pick the verdict, J and K move
    const fb = $("#q-focusbar"), lists = $("#q-lists");
    let fi = -1;
    const pool = () => $$("details.oi").filter((d) => d.dataset.scope === scope && match(d, cur));
    const show = (i) => {
      const p = pool(); if (!p.length) return leave();
      fi = (i + p.length) % p.length;
      p.forEach((d, n) => { d.classList.toggle("focus", n === fi); d.open = n === fi; });
      const d = p[fi]; d.scrollIntoView({ block: "start" }); const ta = $("textarea", d); if (ta) ta.blur();
    };
    const enter = () => { lists.classList.add("focusing"); fb.hidden = false; document.body.classList.add("q-focus"); show(0); };
    const leave = () => { lists.classList.remove("focusing"); fb.hidden = true; document.body.classList.remove("q-focus"); $$("details.oi.focus").forEach((d) => { d.classList.remove("focus"); d.open = false; }); fi = -1; };
    $("#q-focus").addEventListener("click", enter);
    $("#q-unfocus").addEventListener("click", leave);
    $("#q-prev").addEventListener("click", () => show(fi - 1));
    $("#q-next").addEventListener("click", () => show(fi + 1));
    document.addEventListener("keydown", (e) => {
      if (fi < 0 || /input|textarea|select/i.test(document.activeElement.tagName)) return;
      const d = pool()[fi]; if (!d) return;
      if (e.key === "j" || e.key === "J") { e.preventDefault(); show(fi + 1); }
      else if (e.key === "k" || e.key === "K") { e.preventDefault(); show(fi - 1); }
      else if (e.key === "Escape") leave();
      else if (/^[1-9]$/.test(e.key)) { const b = $$(".verdict button", d)[+e.key - 1]; if (b) { e.preventDefault(); b.click(); } }
    });
  }

  // ---- Answering open items: drafts kept in the browser, submitted to the inbox via tools/serve.py ----
  const bar = $("#answer-bar");
  if (bar) {
    const KEY = "mantis-answers";
    const drafts = store.get(KEY);
    const LABEL = { answers: "Answers it", partly: "Partly answers it", someone: "Someone else must answer", same: "Same thing", different: "Different things" };
    const ready = (d) => d && d.verdict && (/^(same|different|real|changed|notconflict|later)$/.test(d.verdict) || (d.answer || "").trim() || (d.who || "").trim());
    const forms = $$(".answer");
    function paint(box) {
      const d = drafts[box.dataset.id] || {};
      $$(".verdict button", box).forEach((b) => b.classList.toggle("on", b.dataset.v === d.verdict));
      $(".who", box).hidden = d.verdict !== "someone";
      const ta = $("textarea", box);   // "Not decided yet" asks when it will be decided instead of for an answer
      if (!ta.dataset.ph) ta.dataset.ph = ta.placeholder;
      ta.placeholder = d.verdict === "later" && ta.dataset.phLater ? ta.dataset.phLater : ta.dataset.ph;
      $(".answer-discard", box).hidden = !(d.answer || d.who || d.verdict);
      const sum = box.closest("details").querySelector("summary");
      let tag = sum.querySelector(".draft-tag");
      const has = (d.answer || d.who || d.verdict) && !box.classList.contains("sent");
      if (has && !tag) { tag = document.createElement("span"); tag.className = "tag draft-tag"; sum.appendChild(tag); }
      if (tag) { if (has) tag.textContent = ready(d) ? "Draft answer" : "Draft: choose an option"; else tag.remove(); }
    }
    function count() {
      const ids = Object.keys(drafts).filter((k) => ready(drafts[k]));
      const half = Object.keys(drafts).filter((k) => !ready(drafts[k]) && (drafts[k].answer || drafts[k].who)).length;
      bar.hidden = !ids.length && !half;
      $("#answer-count").textContent = `${ids.length} answer${ids.length === 1 ? "" : "s"} ready` + (half ? ` · ${half} still need an option chosen` : "");
      $("#answer-submit").disabled = !ids.length;
    }
    const save = () => { store.set(KEY, drafts); count(); };
    forms.forEach((box) => {
      const id = box.dataset.id, d = drafts[id];
      if (d) { $("textarea", box).value = d.answer || ""; $(".who", box).value = d.who || ""; }
      const twins = () => forms.filter((f) => f.dataset.id === id);   // the same question listed under several topics
      const upd = (k, v) => {
        drafts[id] = { ...(drafts[id] || {}), topic: box.dataset.topic, [k]: v };
        twins().forEach((f) => { if (f !== box) { $("textarea", f).value = drafts[id].answer || ""; $(".who", f).value = drafts[id].who || ""; } paint(f); });
        save();
      };
      $(".verdict", box).addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) upd("verdict", b.dataset.v); });
      $("textarea", box).addEventListener("input", (e) => upd("answer", e.target.value));
      $(".who", box).addEventListener("input", (e) => upd("who", e.target.value));
      $(".answer-discard", box).addEventListener("click", () => {   // cancel this one answer, leave the others
        delete drafts[id]; twins().forEach((f) => { $("textarea", f).value = ""; $(".who", f).value = ""; paint(f); }); save();
        toast("Answer discarded.");
      });
      paint(box);
    });
    count();
    function markSent(ids) {
      ids.forEach((id) => {
        forms.filter((f) => f.dataset.id === id).forEach((box) => {
        box.classList.add("sent"); $(".answer-form", box).hidden = true; $(".answer-sent", box).hidden = false;
        const sum = box.closest("details").querySelector("summary");
        if (!sum.querySelector(".sent-tag")) { const t = document.createElement("span"); t.className = "pill w-jira sent-tag"; t.textContent = "Answer sent"; sum.appendChild(t); }
        paint(box);
        });
      });
    }
    const served = location.protocol.startsWith("http") && window.fetch;
    if (served) fetch("api/answers/pending", { cache: "no-store" }).then((r) => r.json()).then((j) => markSent(j.pending || [])).catch(() => {});
    document.addEventListener("click", (e) => {   // one-click: accept the likely answer as a draft, submit with the rest
      const q = e.target.closest(".quick-confirm"); if (!q) return;
      const boxes = forms.filter((f) => f.dataset.id === q.dataset.q); if (!boxes.length) return;
      drafts[q.dataset.q] = { topic: boxes[0].dataset.topic, verdict: "answers", answer: "Confirmed: the likely answer is right." };
      boxes.forEach((b) => { $("textarea", b).value = drafts[q.dataset.q].answer; paint(b); }); save();
      q.textContent = "✓ Confirmed (submit below)"; q.disabled = true;
      toast("Confirmed as a draft. Press Submit answers when you are done.");
    });
    $("#answer-clear").addEventListener("click", () => {
      if (!confirm("Clear all draft answers on this page?")) return;
      Object.keys(drafts).forEach((k) => delete drafts[k]);
      forms.forEach((b) => { $("textarea", b).value = ""; $(".who", b).value = ""; paint(b); });
      save();
    });
    $("#answer-submit").addEventListener("click", async () => {
      const ids = Object.keys(drafts).filter((k) => ready(drafts[k]));
      const answers = ids.map((id) => ({ id, ...drafts[id] }));
      const asText = () => answers.map((a) => `## ${a.id}: ${a.topic}\n- Verdict: ${LABEL[a.verdict]}\n` + (a.who ? `- Who to ask: ${a.who}\n` : "") + `- Answer: ${a.answer || ""}`).join("\n\n");
      let r, j;
      try {
        if (!served) throw new Error("offline");
        r = await fetch("api/answers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answers }) });
        j = await r.json();
      } catch (e) {   // only a failed connection means the server is down
        await copyText("Owner answers to open items:\n\n" + asText());
        toast("The site server isn't running, so your answers were copied instead. Paste them into Claude Code.");
        return;
      }
      if (!r.ok) { toast(j.error || "The answers could not be saved. Your drafts are still here."); return; }
      ids.forEach((k) => delete drafts[k]); save(); markSent(j.pending || ids);
      toast(`Saved ${j.saved} answer${j.saved === 1 ? "" : "s"}. The next pull records ${j.saved === 1 ? "it" : "them"}: press Pull now when you are ready.`); if (typeof pollJobs === "function") pollJobs();
    });
  }

