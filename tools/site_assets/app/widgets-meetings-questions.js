/* widgets-meetings-questions.js: the widgets on Meetings and Questions, and the two screens. layout.json decides where each one sits. */
const DAY_NAME = { Mon: "Monday", Tue: "Tuesday", Wed: "Wednesday", Thu: "Thursday", Fri: "Friday" };
const meetFilter = () => ({ day: ST.mday || "All", q: (ST.mq || "").trim().toLowerCase() });
const meetShown = (m) => { const f = meetFilter(); return (f.day === "All" || m.d === f.day) && (!f.q || `${m.n} ${m.why} ${(m.w || []).join(" ")}`.toLowerCase().includes(f.q)); };
const meetRow = (m, i, cur) => `<button class="mrow" data-mi="${i}" aria-pressed="${i === cur}"><span class="dy">${m.d}</span><span class="tm">${m.t}</span><span class="nm">${esc(m.n)}<small>${m.w.length} ${m.w.length === 1 ? "person" : "people"}${m.ag.length ? " · " + (m.ag.length + m.more) + " to raise" : ""}</small></span>${m.ag.length ? '<span class="pip"></span>' : ""}</button>`;
function meetChips() {   // Mon to Fri are always there, so a day with no meeting is a choice that says so instead of a missing button
  const f = meetFilter();
  const chip = (d, n) => `<button type="button" class="chipf${n === 0 ? " none" : ""}" data-act="meeting-day" data-day="${d}" aria-pressed="${f.day === d}"${n === 0 ? ` aria-label="${DAY_NAME[d]}, no meetings"` : ""}>${d}</button>`;
  return chip("All", -1) + WEEK.map((d) => chip(d, MEET.filter((m) => m.d === d).length)).join("");
}
function meetListHtml(cur) {
  if (!MEET.length) return UI.empty("No regular meetings yet. Add one with New meeting.");
  const f = meetFilter(), rows = MEET.map((m, i) => [m, i]).filter(([m]) => meetShown(m));
  if (!rows.length) {
    const why = f.q ? `No meeting matches "${esc(ST.mq.trim())}"${f.day !== "All" ? ` on ${DAY_NAME[f.day]}` : ""}.` : `No meetings on ${DAY_NAME[f.day]} this week.`;
    return `<p class="mnone">${why} <button type="button" class="link" data-act="meeting-clear-filter">Show all meetings</button></p>`;
  }
  return WEEK.filter((d) => f.day === "All" || d === f.day).map((d) => {
    const ms = rows.filter(([m]) => m.d === d);
    if (!ms.length && f.day !== "All") return "";
    return `<div class="day-l cap ${d === TODAY_D ? "today" : "muted"}">${d} ${DATES[d].split(" ")[0]}</div>${ms.length ? ms.map(([m, i]) => meetRow(m, i, cur)).join("") : `<p class="muted u-note">No meetings.</p>`}`;
  }).join("");
}
UI.widget("meetings.filter", () => `<div class="mfilter" id="mfilter"><div class="mchips" id="mchips">${meetChips()}</div><input type="search" id="mq" class="mq" placeholder="Search meetings" aria-label="Search meetings" value="${esc(ST.mq || "")}"></div>`);
UI.widget("meetings.list", ({ cur }) => meetListHtml(cur));
UI.widget("meetings.detail", ({ cur }) => (MEET[cur] ? meetDetail(cur) : UI.empty("No meeting is open. Pick one, or add the first with New meeting.")));

S.meetings = () => {
  const cur = MEET.findIndex((m) => m.next);
  return `<div class="screen">${UI.head("Meetings", { sub: "This week's meetings. Open one to prepare or add takeaways.", action: '<button class="btn" data-act="meeting-new">New meeting</button>' })}${UI.place("meetings", { cur })}</div>`;
};

UI.widget("questions.list", () => `<div class="stickybar"><div class="picker">${Object.keys(QF).map((k) => `<button class="pick ${QOPT[k][0] === QF[k] ? "" : "set"}" data-pk="${k}">${esc(QF[k])}</button>`).join("")}</div><div class="seg u-mt8">${["Who", "Feature", "Meeting"].map((g) => `<button data-qg="${g}" aria-pressed="${ST.qGroup === g}">Group by ${g.toLowerCase()}</button>`).join("")}</div></div><div id="ql">${qList()}</div>`);
UI.widget("questions.answerbar", () => sbarHtml());

S.questions = () => `<div class="screen">${UI.head("Questions", { sub: "Open a question for context. Answers go to the inbox and are read on the next pull.", headline: `<p class="headline">${LV.qHead}</p>` })}${UI.place("questions", null)}</div>`;
