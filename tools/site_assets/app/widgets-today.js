/* widgets-today.js: the widgets on Today. Each returns what goes inside its card; layout.json decides where it sits. */
UI.widget("today.plan", (P) => planInner(P));
UI.widget("today.changes", () => changesInner());
UI.widget("today.next", () => LV.nextCard);
UI.widget("today.week", () => weekInner());
UI.widget("today.waiting", () => UI.cardHead("Waiting on", { hint: "Longest wait first" })
  + `<ul class="rows">${Object.entries(WANT).slice(0, 3).map(([n, w]) => `<li><span class="t"><button class="nmlink" data-who="${esc(n)}">${n}</button><small>${w.items.length} things, ${w.since}</small></span><button class="link" data-chase="${esc(n)}">Copy chase</button></li>`).join("")}</ul>${LV.moreWaitingHtml}`);

S.today = () => {
  const P = planData(), over = P.over;
  const sentence = ST.mode === "empty" ? "No tasks for today. Next meeting tomorrow at 09:30." : `${over ? `<button class="lnk" data-showover>${over} ${over === 1 ? "task is" : "tasks are"} overdue.</button> ` : ""}${LV.nextLine}`;
  return `<div class="screen">${UI.head(greeting(), { rise: true, sub: LV.dateLong, mono: true, headline: `<p class="headline">${sentence}</p>`, action: '<button class="btn" data-pull>Start a pull</button>' })}
  ${UI.place("today", P)}
  <p class="foot mono">${LV.footer}</p></div>`;
};
