  // ---- Growth (2026-11-04): opportunities to step up, what came of them, learnings and recognition ----
  // Live data from tools/serve.py (GET/POST /api/growth, tools/growth.py). Mantis only proposes; an entry counts once
  // the owner takes or confirms it, and a contribution is done only with a line saying what changed.
  const gAdd = $("#g-add");
  if (gAdd) {
    let G = null, menuG = null;
    const opened = new Set(), more = { wait: false, doing: false, done: false };
    const CAP = { wait: 3, doing: 5, done: 5 };
    const CARDS_G = JSON.parse(gAdd.dataset.cards || "[]");
    const KIND = [["contribution", "Contribution"], ["learning", "Learning"], ["recognition", "Recognition"]];
    const month = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { month: "short", year: "numeric" }) : "";
    const nice = (d) => d ? new Date(d + "T12:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" }) : "";
    const areaName = (k) => ((G.framework.areas || []).find((a) => a.key === k) || {}).name || "";
    const areasOf = (i) => i.areas.map(areaName).filter(Boolean).join(", ");
    const cardName = (s) => ((CARDS_G.find((c) => c[0] === s) || [])[1] || "").replace(/\s*\([^)]*\)\s*$/, "");
    const first = (n) => (n || "").split(" ")[0];

    async function post(body, msg, undo) {
      try { G = await api("api/growth", body); paint(); if (msg) toast(msg, undo); return G.result; }
      catch (e) { toast(e.message); return null; }
    }

    // ---- The quiet pickers on the add line and in an entry: one short menu, the same look as Today's ----
    function closeG() { if (menuG) { menuG.remove(); menuG = null; } }
    function pickG(btn, items, onPick) {
      if (menuG && menuG.owner === btn) return closeG();
      closeG();
      const cur = btn.dataset.value || "", r = btn.getBoundingClientRect();
      menuG = document.createElement("div"); menuG.className = "pickmenu"; menuG.setAttribute("role", "menu"); menuG.owner = btn;
      menuG.style.left = Math.max(8, Math.min(r.left, innerWidth - 300)) + scrollX + "px"; menuG.style.top = r.bottom + scrollY + 6 + "px";
      const search = items.length > 8;
      const row = ([v, l, sub]) => `<button type="button" role="menuitemradio" aria-checked="${v === cur}" class="pm-i${v === cur ? " on" : ""}" data-v="${esc(v)}"><span>${esc(l)}</span>${sub ? `<span class="pm-s">${esc(sub)}</span>` : ""}</button>`;
      const list = (q = "") => items.filter(([, l]) => !q || l.toLowerCase().includes(q.toLowerCase())).slice(0, 12).map(row).join("") || '<p class="pm-h">Nothing matches</p>';
      menuG.innerHTML = (search ? '<input class="pm-q" placeholder="Find a feature" aria-label="Find a feature">' : "") + `<div class="pm-list">${list()}</div>`;
      document.body.appendChild(menuG);
      const q = $(".pm-q", menuG);
      if (q) { q.focus(); q.addEventListener("input", () => { $(".pm-list", menuG).innerHTML = list(q.value); }); }
      else { const f = $(".pm-i.on", menuG) || $(".pm-i", menuG); if (f) f.focus(); }
      menuG.addEventListener("click", (e) => { e.stopPropagation(); const b = e.target.closest(".pm-i"); if (!b) return; closeG(); onPick(b.dataset.v); btn.focus(); });
      menuG.addEventListener("keydown", (e) => {
        const all = $$(".pm-i", menuG), i = all.indexOf(document.activeElement);
        if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); const n = all[Math.max(0, Math.min(all.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)))]; if (n) n.focus(); }
        else if (e.key === "Enter" && e.target === q) { e.preventDefault(); const b = $(".pm-i", menuG); if (b) b.click(); }
        else if (e.key === "Escape") { e.stopPropagation(); closeG(); btn.focus(); }
      });
    }
    document.addEventListener("click", (e) => { if (menuG && !e.composedPath().includes(menuG) && !e.target.closest("[data-gpick]")) closeG(); });
    const areaItems = () => [["", "No strength"], ...(G.framework.areas || []).map((a) => [a.key, a.name, ""])];
    const cardItems = () => [["", "No feature"], ...CARDS_G.map(([s, t, f]) => [s, t.replace(/\s*\([^)]*\)\s*$/, ""), f ? "Following" : ""])];
    const label = { kind: (v) => (KIND.find((k) => k[0] === v) || KIND[0])[1], area: (v) => areaName(v) || "Strength", card: (v) => cardName(v) || "Feature" };
    function setG(btn, v) {
      btn.dataset.value = v; btn.textContent = label[btn.dataset.gpick](v); btn.classList.toggle("set", !!v && btn.dataset.gpick !== "kind");
      if (btn.dataset.gpick === "kind") {   // recognition is someone's words; a learning is something learned
        $("#g-said").hidden = v !== "recognition";
        $("#g-title").placeholder = v === "recognition" ? "Their words, as they said them" : v === "learning" ? "What you learned, and where you used it" : "What did you spot, do or learn?";
      }
    }

    // ---- The add line: the page's one main action ----
    $("#g-title").addEventListener("input", (e) => gAdd.classList.toggle("typing", !!e.target.value.trim()));
    gAdd.addEventListener("click", (e) => {
      const b = e.target.closest("[data-gpick]"); if (!b || !G) return;
      pickG(b, b.dataset.gpick === "kind" ? KIND : b.dataset.gpick === "area" ? areaItems() : cardItems(), (v) => setG(b, v));
    });
    gAdd.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = $("#g-title").value.trim(); if (!title) return;
      const v = (k) => $(`[data-gpick="${k}"]`, gAdd).dataset.value;
      const kind = v("kind"), item = { title, kind, areas: v("area") ? [v("area")] : [], card: v("card"), said_by: $("#g-said").value.trim() };
      const r = await post({ action: "add", item }, kind === "contribution" ? "Noted. It's under Doing; mark it done when something changes because of it." : kind === "learning" ? "Learning saved." : "Recognition saved, in their words.");
      if (!r) return;
      gAdd.reset(); gAdd.classList.remove("typing"); $$("[data-gpick]", gAdd).forEach((b) => setG(b, b.dataset.gpick === "kind" ? "contribution" : ""));
      $("#g-title").focus();
    });

    // ---- Rows ----
    const stepLine = (s) => `<li class="g-step${s.status === "done" ? " is-done" : ""}"><span class="pm" aria-hidden="true">${s.status === "done" ? "✓" : "○"}</span>` +
      `<span>${esc(s.title)}</span><span class="t-meta">${s.status === "done" ? "Done" : s.status === "deleted" ? "Deleted" : s.day ? nice(s.day) : "No date"}</span></li>`;
    const facts = (i) => [
      i.why && `<p><span class="g-k">Why</span>${esc(i.why)}</p>`,
      i.outcome && !(i.past && i.state === "proposed" && i.kind === "contribution") && `<p><span class="g-k">${i.state === "done" ? "What changed" : "Result so far"}</span>${esc(i.outcome)}</p>`,
      i.evidence && `<p><span class="g-k">Evidence</span>${/^https?:\/\//.test(i.evidence) ? `<a href="${esc(i.evidence)}" target="_blank" rel="noopener">${esc(i.evidence.replace(/^https?:\/\//, "").slice(0, 60))}</a>` : esc(i.evidence)}</p>`,
      i.seen_by.length && `<p><span class="g-k">Seen by</span>${esc(i.seen_by.join(", "))}</p>`,
      i.card && `<p><span class="g-k">Feature</span>${esc(cardName(i.card) || i.card)}</p>`,
      i.source && `<p><span class="g-k">From</span>${esc(i.source)}</p>`].filter(Boolean).join("");
    const strengthPick = (i) => `<button type="button" class="pick${i.areas[0] ? " set" : ""}" data-gpick="area" data-gid="${esc(i.id)}" data-value="${esc(i.areas[0] || "")}">${esc(areaName(i.areas[0]) || "Strength")}</button>`;
    function row(i, sub, body) {
      return `<details class="g-row" data-id="${esc(i.id)}"${opened.has(i.id) ? " open" : ""}><summary><span class="pm" aria-hidden="true"></span>` +
        `<span class="g-t">${esc(i.title)}</span><span class="t-meta g-m">${esc(sub)}</span></summary><div class="g-d">${body}</div></details>`;
    }
    function waitRow(i) {
      const body = facts(i) + (i.past && i.kind !== "contribution"
        ? `<div class="g-acts">${strengthPick(i)}<button type="button" class="mini on" data-g="confirm">Yes, add it</button><button type="button" class="mini" data-g="dismiss">Not right</button></div>`
        : i.past
        ? `<label class="g-f"><span>What changed because of it (your words)</span><input type="text" data-f="outcome" value="${esc(i.outcome)}" maxlength="800"></label>` +
          `<div class="g-acts">${strengthPick(i)}<button type="button" class="mini on" data-g="confirm">Yes, add it</button><button type="button" class="mini" data-g="dismiss">Not mine</button></div>`
        : `<div class="g-acts">${strengthPick(i)}<button type="button" class="mini on" data-g="take">Take it on</button><button type="button" class="mini" data-g="dismiss">Not now</button></div>`);
      return row(i, i.past ? `Past work · ${areasOf(i) || "no strength"}` : areasOf(i) || "Opportunity", body);
    }
    function doingRow(i) {
      const open = i.steps.filter((s) => s.status === "todo" || s.status === "blocked");
      const steps = i.steps.length ? `<ul class="g-steps">${i.steps.map(stepLine).join("")}</ul>` : "";
      const body = facts(i) + steps +
        `<form class="g-stepf" data-g="step"><input type="text" placeholder="Add a step to today's list" aria-label="Add a step to today's list" maxlength="300"><button type="submit" class="mini">Add</button></form>` +
        `<form class="g-donef" data-g="done" hidden><label class="g-f"><span>What changed because of it?</span><input type="text" data-f="outcome" required maxlength="800" placeholder="The result, in a line: what is better, faster or decided now"></label>` +
        `<label class="g-f"><span>Evidence (a link), optional</span><input type="text" data-f="evidence" maxlength="500" placeholder="Confluence page, Jira ticket, message"></label>` +
        `<label class="g-f"><span>Who saw it, optional</span><input type="text" data-f="seen_by" maxlength="300" placeholder="Names, separated by commas"></label>` +
        `<div class="g-acts"><button type="submit" class="mini on">Save as done</button><button type="button" class="linkish" data-g="cancel">Cancel</button></div></form>` +
        `<div class="g-acts g-main">${strengthPick(i)}<button type="button" class="mini on" data-g="open-done">Mark done</button><button type="button" class="linkish g-quiet" data-g="drop">Let it go</button></div>`;
      return row(i, [areasOf(i), open[0] ? "Next: " + open[0].title : ""].filter(Boolean).join(" · ") || "No step yet", body);
    }
    function doneRow(i) {
      const mgr = first(G.framework.manager) || "your manager";
      const body = facts(i) + `<div class="g-acts">${strengthPick(i)}<button type="button" class="mini${i.shared ? " on" : ""}" data-g="shared" aria-pressed="${!!i.shared}">${i.shared ? `${esc(mgr)} knows (${esc(nice(i.shared))})` : `Told ${esc(mgr)}`}</button>` +
        `<button type="button" class="linkish g-quiet" data-g="reopen">Reopen</button><button type="button" class="linkish g-quiet" data-g="delete">Remove</button></div>`;
      return row(i, [areasOf(i), month(i.done_at), i.shared ? "Shared" : ""].filter(Boolean).join(" · "), body);
    }
    function list(key, items, draw, empty) {
      const box = $(`#g-${key}-b`), btn = $(`#g-${key}-more`);
      const shown = more[key] ? items : items.slice(0, CAP[key]);
      box.innerHTML = shown.map(draw).join("") || (empty ? `<p class="muted g-empty">${empty}</p>` : "");
      btn.hidden = items.length <= CAP[key]; btn.textContent = more[key] ? "Show fewer" : `${items.length - CAP[key]} more`;
    }

    // ---- The side column: strengths the role asks for, then recognition and learnings ----
    function paintSide() {
      const cov = G.coverage, areas = G.framework.areas || [];
      $("#g-cov-n").textContent = "Done entries in the last 12 months, by what the role asks for.";
      $("#g-cov-b").innerHTML = areas.map((a) => {
        const c = cov[a.key] || { n: 0, thin: true };
        const quotes = (a.quotes || []).map(([src, q]) => `<li>“${esc(q)}” <span class="t-meta">${src === "JD" ? "Your JD" : "Job ads"}</span></li>`).join("");
        return `<details class="g-cov"><summary><span class="g-cov-t">${esc(a.name)}</span><span class="t-meta">${c.n ? c.n : c.thin ? "thin" : ""}</span></summary>` +
          `<div class="g-cov-d"><p>${esc(a.means)}</p><ul>${quotes}</ul></div></details>`;
      }).join("");
      const done = G.items.filter((i) => i.state === "done");
      const rec = done.filter((i) => i.kind === "recognition").sort((a, b) => (b.done_at > a.done_at ? 1 : -1));
      const learn = done.filter((i) => i.kind === "learning").sort((a, b) => (b.done_at > a.done_at ? 1 : -1));
      $("#g-rec").hidden = !rec.length; $("#g-learn").hidden = !learn.length;
      const side = (i, sub) => `<div class="ri g-side" data-id="${esc(i.id)}"><span class="ri-v">${esc(i.title)}</span><span class="ri-s">${esc(sub)}</span>` +
        `<button type="button" class="linkish g-quiet" data-g="delete" aria-label="Remove">Remove</button></div>`;
      $("#g-rec-b").innerHTML = rec.slice(0, 3).map((i) => side(i, [i.said_by, nice(i.done_at)].filter(Boolean).join(", "))).join("");
      $("#g-learn-b").innerHTML = learn.slice(0, 3).map((i) => side(i, [areasOf(i), month(i.done_at)].filter(Boolean).join(" · "))).join("");
    }

    // ---- The appraisal record: what the review asks for (outcome, contribution, impact), grouped by strength ----
    function paintRecord() {
      const r = G.record;
      const line = (i) => `<li><b>${esc(i.title)}</b> (${esc(month(i.done_at))}). ${esc(i.outcome)}` + (i.evidence ? ` Evidence: ${esc(i.evidence)}.` : "") + (i.seen_by.length ? ` Seen by ${esc(i.seen_by.join(", "))}.` : "") + "</li>";
      const secs = r.sections.map((s) => `<h3>${esc(s.name)}</h3><p class="muted small">${esc(s.means)}</p><ul>${s.items.map(line).join("")}</ul>`).join("");
      const rec = r.recognition.length ? `<h3>Recognition</h3><ul>${r.recognition.map((i) => `<li>${esc(i.title)} (${esc([i.said_by, nice(i.done_at)].filter(Boolean).join(", "))})</li>`).join("")}</ul>` : "";
      const lrn = r.learnings.length ? `<h3>Learnings</h3><ul>${r.learnings.map((i) => `<li>${esc(i.title)}${i.outcome ? ". " + esc(i.outcome) : ""} (${esc(month(i.done_at))})</li>`).join("")}</ul>` : "";
      $("#g-record-b").innerHTML = secs || rec || lrn
        ? `<button type="button" class="btn-line copy-sec nocopy">Copy</button><h2 class="nocopy g-rec-h">Contributions toward ${esc(r.role)}, since ${esc(month(r.since))}</h2>${secs}${rec}${lrn}`
        : '<p class="muted">Nothing done yet. Each contribution you mark done, with what changed, lands here grouped by strength, ready to paste into your review.</p>';
    }

    function paint() {
      const fw = G.framework, items = G.items;
      const wait = items.filter((i) => i.state === "proposed");
      const doing = items.filter((i) => i.state === "open");
      const done = items.filter((i) => i.state === "done" && i.kind === "contribution").sort((a, b) => (b.done_at > a.done_at ? 1 : -1));
      // The one line that says where to look next: the thinnest strength (none done in 90 days), else the review
      const thin = (fw.areas || []).filter((a) => (G.coverage[a.key] || {}).thin);
      $("#g-goal").textContent = fw.role ? `Toward ${fw.role}` : "";
      $("#g-lead").textContent = !items.length ? "Note what you spot, do and learn. Mantis keeps the proof, grouped by what the role asks for, for your review."
        : thin.length && thin.length < (fw.areas || []).length ? `No recent evidence yet for ${thin.slice(0, 2).map((a) => a.name).join(" or ")}. Year-end review: ${fw.review.year_end || "not set"}.`
        : `Year-end review: ${fw.review.year_end || "not set"}; mid-year ${fw.review.mid_year || "not set"}.`;
      $("#g-wait").hidden = !wait.length;
      list("wait", wait, waitRow);
      list("doing", doing, doingRow, "Nothing in progress. Note an opportunity above, or take one Mantis proposes.");
      list("done", done, doneRow, "Nothing done yet.");
      paintSide(); paintRecord();
    }

    // ---- Actions ----
    document.addEventListener("toggle", (e) => {
      const d = e.target; if (!d.matches || !d.matches(".g-row")) return;
      d.open ? opened.add(d.dataset.id) : opened.delete(d.dataset.id);
    }, true);
    $$("#g-wait-more, #g-doing-more, #g-done-more").forEach((b) => b.addEventListener("click", () => { const k = b.id.split("-")[1]; more[k] = !more[k]; paint(); }));
    document.addEventListener("click", async (e) => {
      const pk = e.target.closest("[data-gid][data-gpick]");
      if (pk) { pickG(pk, areaItems(), (v) => post({ action: "update", id: pk.dataset.gid, fields: { areas: v ? [v] : [] } })); return; }
      const b = e.target.closest("button[data-g]"); if (!b) return;
      const host = b.closest("[data-id]"); if (!host || !host.closest(".today-grid")) return;
      const id = host.dataset.id, it = G.items.find((x) => x.id === id), act = b.dataset.g;
      if (act === "open-done") { $(".g-donef", host).hidden = false; $(".g-main", host).hidden = true; $(".g-donef input", host).focus(); return; }
      if (act === "cancel") { $(".g-donef", host).hidden = true; $(".g-main", host).hidden = false; return; }
      if (act === "take") return post({ action: "take", id }, "Taken on. It's under Doing; add a step to put it on Today.", () => post({ action: "restore", item: it }));
      if (act === "confirm") { const o = $('[data-f="outcome"]', host), v = o ? o.value.trim() : ""; return post({ action: "confirm", id, outcome: v }, "Added to Done.", () => post({ action: "restore", item: it })); }
      if (act === "dismiss") return post({ action: "dismiss", id }, "Gone. Mantis won't propose it again.", () => post({ action: "restore", item: it }));
      if (act === "drop") return post({ action: "drop", id }, "Let go.", () => post({ action: "reopen", id }));
      if (act === "reopen") return post({ action: "reopen", id }, "Back under Doing.", () => post({ action: "restore", item: it }));
      if (act === "shared") return post({ action: "shared", id }, it.shared ? "Marked not shared." : "Marked as shared.");
      if (act === "delete") return post({ action: "delete", id }, "Removed.", () => post({ action: "restore", item: it }));
    });
    document.addEventListener("submit", async (e) => {
      const f = e.target.closest("form[data-g]"); if (!f || !f.closest(".today-grid")) return;
      e.preventDefault();
      const host = f.closest("[data-id]"), id = host.dataset.id, it = G.items.find((x) => x.id === id);
      if (f.dataset.g === "step") {
        const v = $("input", f).value.trim(); if (!v) return;
        opened.add(id);
        return post({ action: "step", id, title: v }, "On today's list, in the Growth group.");
      }
      const val = (k) => $(`[data-f="${k}"]`, f).value.trim();
      opened.delete(id);
      post({ action: "done", id, outcome: val("outcome"), evidence: val("evidence"), seen_by: val("seen_by") }, "Done, with the proof. It's in your appraisal record.", () => post({ action: "restore", item: it }));
    });

    (async () => {
      try { G = await api("api/growth"); paint(); }
      catch (e) { $("#g-offline").hidden = false; $("#g-doing-b").innerHTML = ""; }
    })();
  }

