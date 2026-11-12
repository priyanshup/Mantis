/* v9: rest-of-the-week agenda, calendar with meeting and due dots, type-to-filter pickers */
const WKD=["Mon","Tue","Wed","Thu","Fri"];

function calHtml(y,m,sel){ const start=(new Date(y,m,1).getDay()+6)%7, cells=[], due={}; allTasks().forEach(x=>{ if(x.due&&!ST.done.has(x.k)) due[x.due]=(due[x.due]||0)+1; });
  for(let i=0;i<42;i++){ const d=new Date(y,m,1-start+i), v=iso(d), mc=MEET.filter(x=>x.d===DOW[d.getDay()]).length, tc=due[v]||0, cls=[d.getMonth()!==m?"out":"",v===REAL.today?"today":"",v===sel?"sel":""].join(" ");
    const dots=Array.from({length:Math.min(mc,3)},()=>"<i></i>").join("")+Array.from({length:Math.min(tc,2)},()=>'<i class="t"></i>').join("");
    const label=`${fmtLong(v)}${mc?`, ${mc} ${mc===1?"meeting":"meetings"}`:""}${tc?`, ${tc} ${tc===1?"task":"tasks"} due`:""}`;
    cells.push(`<button type="button" data-cd="${v}" class="${cls}" aria-label="${label}"><span>${d.getDate()}</span><span class="cd">${dots}</span></button>`); }
  return `<div class="calh"><button type="button" data-cn="-1" aria-label="Previous month"><svg class="u-t-rotate90deg chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button><b>${MONTHS_LONG[m]} ${y}</b><button type="button" data-cn="1" aria-label="Next month"><svg class="u-t-rotaten90deg chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg></button></div>
  <div class="calw">${["Mo","Tu","We","Th","Fr","Sa","Su"].map(x=>`<span>${x}</span>`).join("")}</div><div class="calg">${cells.join("")}</div>
  <div class="callg"><span><i></i>Meeting</span><span><i class="t"></i>Task due</span></div>
  <div class="calf"><button type="button" data-cq="0">Today</button><button type="button" data-cq="1">Tomorrow</button><button type="button" data-cq="7">Next week</button><button type="button" data-cq="x">Clear</button></div>`; }

const pickRows=(k,q)=>{ const ql=q.trim().toLowerCase(), rows=QOPT[k].filter(o=>!ql||o.toLowerCase().includes(ql)); return rows.map((o,i)=>`<button role="menuitem" data-po="${esc(o)}" class="${i===0&&ql?"sel":""} ${o===QF[k]?"cur":""}">${esc(o)}</button>`).join("")||`<p class="u-p-8-10 zero">No match.</p>`; };
