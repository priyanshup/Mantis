/* v10: full week view, plain copy, sources on topics */
const greeting=()=>{ const h=new Date().getHours(); return h<12?"Good morning":h<18?"Good afternoon":"Good evening"; };
const nowMin=()=>{ const d=new Date(); return d.getHours()*60+d.getMinutes(); };
function dayStats(i){ const date=EXTRA.week[i].d;
  if(date===REAL.today){ return {done:ST.done.size,total:planData().n}; }
  const due=allTasksW().filter(x=>x.due===date), done=due.filter(x=>ST.done.has(x.k)).length+EXTRA.week[i].done; return {done,total:due.length+EXTRA.week[i].done}; }
function weekInner(){ const days=WKD.map((d,i)=>{ const date=EXTRA.week[i].d, isT=date===REAL.today, past=date<REAL.today, st=dayStats(i);
    const ms=MEET.map((m,idx)=>({m,idx})).filter(x=>x.m.d===d).sort((a,b)=>a.m.t.localeCompare(b.m.t)), ts=allTasksW().filter(x=>x.due===date&&!ST.done.has(x.k));
    const items=[...ms.map(({m,idx})=>({k:"m",m,idx})),...ts.map(x=>({k:"t",x}))];
    const li=it=>it.k==="m"?`<li><button class="wdm ${it.m.next?"nx":""}" data-gomeet="${it.idx}" title="Open the brief"><span class="when">${it.m.t}</span><span class="t clamp">${esc(it.m.n)}</span>${it.m.ag.length?'<i class="bp" title="Brief ready"></i>':"<i></i>"}</button></li>`
      :`<li><button class="wdm tk" data-agtask="${it.x.k}"><span class="when">Due</span><span class="t clamp">${esc(it.x.t)}</span><i></i></button></li>`;
    const shown=items.slice(0,3), rest=items.slice(3);
    const tl=ms.map(({m})=>{ const [h,mm]=m.t.split(":"), p=((+h*60+ +mm)-480)/600*100; return `<i style="left:${Math.max(0,Math.min(93,p)).toFixed(1)}%" title="${m.t}  ${esc(m.n)}"></i>`; }).join(""), nowp=isT?(nowMin()-480)/600*100:-1, pct=st.total?Math.round(st.done/st.total*100):0;
    return `<article class="wd ${isT?"today":""} ${past?"past":""}"><header class="wdh"><div class="wdd"><span class="dn">${d}</span><span class="dd">${9+i}</span></div><div class="wdt">${st.total?`<span class="mono">${st.done}/${st.total}</span><i class="pb"><b style="width:${pct}%"></b></i><small>tasks</small>`:`<small>no tasks</small>`}</div></header>
      <div class="tl" aria-hidden="true">${tl}${nowp>0&&nowp<100?`<em class="nowm" style="left:${nowp.toFixed(1)}%"></em>`:""}</div>
      ${items.length?`<ul class="wdl">${shown.map(li).join("")}</ul>${rest.length?`<div class="acc more-acc"><div class="in"><ul class="wdl">${rest.map(li).join("")}</ul></div></div><button class="more" data-more>+${rest.length} more</button>`:""}`:`<p class="free">Free</p>`}</article>`; }).join("");
  return `<div class="card-h"><h2>This week</h2><a class="link" href="#meetings">Open Meetings</a></div><p class="u-m-n6-0-6 hint">Each dark bar marks when a meeting starts, from 08:00 to 18:00. The faint line is noon.</p><div class="wkb">${days}</div>`; }

const TSRC=["Weekly sync, 6 Nov","Jira and Confluence changes, 5 Nov","Jira ticket, 4 and 5 Nov","Jira changes, 5 Nov","Handover notes, 6 Nov"];

