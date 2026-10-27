  // ---- Questions page (IMP-007, MANTIS-IMP-094): To answer / Waiting on others / Closed automatically, then the filters ----
  const oi = $("#f-oi");
  if (oi) {
    const who = $("#oi-who");   // who can answer (IMP-046): combines with the chips
    const qs = $("#q-scope");
    let cur = "all", scope = "you";
    const apply = (v) => {
      cur = v;
      $$("button", oi).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      const w = who && scope === "others" ? who.value : "";
      $$("details.oi").forEach((d) => (d.hidden = !((v === "all" || d.dataset.kind === v || (v === "names" && /^(name|term)$/.test(d.dataset.kind)) || (v === "potential" && !/^(Open|Unconfirmed)$/.test(d.dataset.status)) || (v === "priority" && /^(Critical|High)$/.test(d.dataset.priority)) || (v === "possible" && d.dataset.status === "Unconfirmed"))
        && d.dataset.scope === scope && (!w || d.dataset.ask === w))));
      $$(".oi-group").forEach((g) => {   // hide empty topics; the count shows what the filter leaves
        const n = $$("details.oi", g).filter((d) => !d.hidden).length;
        g.hidden = !n; $(".oi-n", g).textContent = n;
      });
      const empty = $("#q-empty");
      if (empty) empty.hidden = scope === "closed" || $$("#oi-flat details.oi").some((d) => !d.hidden);
    };
    const setScope = (s) => {
      scope = s;
      $$("button", qs).forEach((b) => { b.classList.toggle("on", b.dataset.v === s); b.setAttribute("aria-selected", String(b.dataset.v === s)); });
      $("#q-closed").hidden = s !== "closed"; $("#q-lists").hidden = s === "closed"; $("#q-tools").hidden = s === "closed";
      if (who) who.hidden = s !== "others";
      apply(cur);
    };
    if (qs) qs.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) setScope(b.dataset.v); });
    oi.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) apply(b.dataset.v); });
    if (who) who.addEventListener("change", () => apply(cur));
    // A link to one question opens the side it is on; #who= goes to Waiting on others
    const linked = location.hash.startsWith("#k=") && $(`#oi-flat details.oi[data-k="${CSS.escape(location.hash.slice(3))}"]`);
    setScope(linked ? linked.dataset.scope : location.hash.startsWith("#who=") ? "others" : location.hash === "#closed" ? "closed" : "you");
    // One list (each question once) or By topic (grouped; a question linked to several topics repeats there)
    const view = $("#oi-view");
    const setView = (v) => {
      $$("button", view).forEach((b) => b.classList.toggle("on", b.dataset.v === v));
      $("#oi-flat").hidden = v !== "flat"; $("#oi-topics").hidden = v !== "topic"; $("#oi-topics-bar").hidden = v !== "topic";
      const n = $$(".oi-group").filter((g) => !g.hidden).length; $("#oi-topics-n").textContent = `${n} topic${n === 1 ? "" : "s"}`;
      store.set("mantis-oi-view", { v });
    };
    view.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) setView(b.dataset.v); });
    const ex = $("#oi-expand"), groups = () => $$(".oi-group").filter((g) => !g.hidden);
    const label = () => (ex.textContent = groups().every((g) => g.open) ? "Collapse all" : "Expand all");
    ex.addEventListener("click", () => { const open = !groups().every((g) => g.open); groups().forEach((g) => (g.open = open)); label(); });
    $$(".oi-group").forEach((g) => g.addEventListener("toggle", label));
    setView(location.hash.length > 1 ? "flat" : (store.get("mantis-oi-view").v || "flat"));   // a link to one question always uses the list
    $$("[data-goto-filter]").forEach((gf) => gf.addEventListener("click", () => { apply(gf.dataset.gotoFilter); oi.scrollIntoView({ block: "start" }); }));
    if (location.hash === "#waiting") apply("potential");
    if (location.hash === "#possible") apply("possible");
    if (location.hash.startsWith("#who=") && who) { who.value = decodeURIComponent(location.hash.slice(5)); apply("all"); }
    if (location.hash.startsWith("#k=")) {   // a link from What's new: open that question in the one-list view
      const q = $(`#oi-flat details.oi[data-k="${CSS.escape(location.hash.slice(3))}"]`);
      if (q) { q.open = true; requestAnimationFrame(() => q.scrollIntoView({ block: "center" })); q.classList.add("hl"); }
    }
    const target = location.hash && document.getElementById(location.hash.slice(1));
    if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView({ block: "center" }); }
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

