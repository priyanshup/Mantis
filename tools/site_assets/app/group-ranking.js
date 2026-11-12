/* v15: a group ranks by its most urgent task; the order is recomputed when priorities change, not when tasks are ticked off */
Object.assign(ST,{rankDirty:true,gsnap:null});
function groupMeta(){ const t=allTasks(), rank={high:0,medium:1,low:2,none:3}, m={}; t.forEach(x=>(m[x.g]=m[x.g]||[]).push(x));
  const gs=Object.entries(m).map(([name,items])=>{ const lv=items.filter(x=>!ST.done.has(x.k)); return {name,items,over:lv.filter(x=>x.due&&x.due<REAL.today).length,hi:lv.filter(x=>x.p==="high").length,top:lv.length?Math.min(...lv.map(x=>rank[x.p]===undefined?3:rank[x.p])):9}; });
  return {t,rank,gs}; }
const groupCmp=mode=>mode==="due"?(a,b)=>(a.items[0].due||"9").localeCompare(b.items[0].due||"9")
  :mode==="priority"?(a,b)=>a.top-b.top||b.hi-a.hi||b.items.length-a.items.length
  :(a,b)=>(b.over>0)-(a.over>0)||a.top-b.top||b.over-a.over||b.hi-a.hi||b.items.length-a.items.length;
const computedOrder=mode=>groupMeta().gs.sort(groupCmp(mode)).filter(g=>g.items.some(x=>!ST.done.has(x.k))).map(g=>g.name);
function planData(){ const {t,rank,gs}=groupMeta(), so=ST.sort;
  const byPri=(a,b)=>rank[a.p]-rank[b.p]||(a.due||"9").localeCompare(b.due||"9"), byDue=(a,b)=>(a.due||"9").localeCompare(b.due||"9")||rank[a.p]-rank[b.p];
  if(ST.flat){ const items=t.slice().sort(so==="due"?byDue:byPri); if(so==="mine"&&ST.manual&&ST.manual.items.__flat){ const o=ST.manual.items.__flat, ix=k=>{ const i=o.indexOf(k); return i<0?-1:i; }; items.sort((a,b)=>ix(a.k)-ix(b.k)); }
    const lv=items.filter(x=>!ST.done.has(x.k)); return {names:[...new Set(t.map(x=>x.g).filter(Boolean))],gs:[{name:"__flat",items,over:lv.filter(x=>x.due&&x.due<REAL.today).length,hi:lv.filter(x=>x.p==="high").length,top:0}],n:t.length,over:t.filter(x=>x.due&&x.due<REAL.today&&!ST.done.has(x.k)).length}; }
  gs.forEach(g=>g.items.sort(so==="due"?byDue:byPri));
  if(so==="mine"&&ST.manual){ const gi=n=>{ const i=ST.manual.groups.indexOf(n); return i<0?99:i; }; gs.sort((a,b)=>gi(a.name)-gi(b.name)); gs.forEach(g=>{ const o=ST.manual.items[g.name]; if(o){ const ix=k=>{ const i=o.indexOf(k); return i<0?-1:i; }; g.items.sort((a,b)=>ix(a.k)-ix(b.k)); } }); }
  else { const cmp=groupCmp(so), computed=[...gs].sort(cmp).map(g=>g.name);
    if(!ST.gsnap||ST.gsnap.mode!==so||ST.rankDirty){ ST.gsnap={mode:so,order:computed}; ST.rankDirty=false; }
    const ord=ST.gsnap.order; gs.sort((a,b)=>{ const ia=ord.indexOf(a.name), ib=ord.indexOf(b.name); return (ia<0?999:ia)-(ib<0?999:ib)||computed.indexOf(a.name)-computed.indexOf(b.name); }); }
  return {gs,n:t.length,over:t.filter(x=>x.due&&x.due<REAL.today&&!ST.done.has(x.k)).length}; }
