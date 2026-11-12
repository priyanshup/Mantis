/* widgets-growth.js: the widgets on Growth, and the screen. layout.json decides where each one sits. */
const FOLD = '<button class="link" data-fold>Collapse</button>';
UI.widget("growth.proposals", (L) => UI.cardHead("Proposals and your record", { action: FOLD })
  + `<div class="acc open fold"><div class="in"><div class="seg" id="gtabs">${[["Proposed", L.prop.length], ["In progress", L.prog.length], ["Done", L.done.length], ["Hidden", L.hidden]].map(([n, c]) => `<button data-gv="${n}" aria-pressed="${ST.gv === n}">${n}<span class="m">${c}</span></button>`).join("")}</div><div id="glist">${gListHtml()}</div></div></div>`);
UI.widget("growth.add", () => UI.cardHead("Add your own", { action: FOLD })
  + `<div class="acc open fold"><div class="in"><p class="hint u-mb10">A win, a step or something to learn</p><div id="gform">${gFormHtml()}</div></div></div>`);
UI.widget("growth.evidence", () => UI.cardHead("Where the evidence sits", { hint: "items per area" })
  + `<div class="areas">${AREAS.map((a, i) => `<div class="area"><span>${a.name}</span><div class="tr"><i style="width:${a.n / Math.max(1, ...AREAS.map((x) => x.n)) * 100}%;animation-delay:${i * 60}ms"></i></div><span class="c">${a.n}</span></div>`).join("")}</div>`);

S.growth = () => {
  const L = gLists();
  return `<div class="screen">${UI.head("Growth", { sub: "Proposals from Mantis, and your own entries.", headline: `<p class="headline" id="ghead">${gHead()}</p>` })}
  ${UI.place("growth", L)}</div>`;
};
