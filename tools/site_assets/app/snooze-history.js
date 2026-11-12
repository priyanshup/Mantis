/* v12: snooze to tomorrow, history with snoozed tasks, week uses all tasks */
var ALLT_RAW=false;
const ARROW='<svg viewBox="0 0 24 24"><path d="M5 12h13M13 6l6 6-6 6"/></svg>';
function allTasksW(){ ALLT_RAW=true; const t=allTasks(); ALLT_RAW=false; return t; }
function histHtml(){ const d=[...ST.done].filter(k=>taskByK(k)), s=EXTRA.sugg.map((x,i)=>[x,i]).filter(([x,i])=>ST.gone.has("s"+i)&&!ST.added.some(a=>a.k===900+i));
  const sn=allTasksW().filter(x=>x.snz); if(!d.length&&!s.length&&!sn.length) return "";
  const label=[d.length?`Done today ${d.length}`:"",sn.length?`Moved to tomorrow ${sn.length}`:"",s.length?`Dismissed ${s.length}`:""].filter(Boolean).join(" · ");
  return `<div class="hist"><button class="gh hh" data-hh><span class="nm">${label}</span>${CHEV}</button><div class="acc"><div class="in"><ul class="rows">${d.map(k=>`<li class="trow done"><button class="ck" aria-pressed="true" data-restore="${k}" aria-label="Bring back">${CK}</button><span class="t clamp">${esc(taskByK(k).t)}</span><span class="when">Bring back</span></li>`).join("")}${sn.map(x=>`<li class="trow"><span></span><span class="t clamp">${esc(x.t)}</span><button class="link" data-unsnz="${x.k}">Bring back</button></li>`).join("")}${s.map(([x,i])=>`<li class="trow"><span></span><span class="t clamp">${esc(x.t)}</span><button class="link" data-restores="${i}">Bring back</button></li>`).join("")}</ul></div></div></div>`; }
