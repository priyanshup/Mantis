/* v8 controls behaviour */
let CAL=null;
const closePops=()=>{ $$(".pop").forEach(p=>p.remove()); $$(".cb.open").forEach(c=>{ c.classList.remove("open"); c.querySelector("input").setAttribute("aria-expanded","false"); }); CAL=null; };
function placePop(pop,r,w){ pop.style.left=Math.max(8,Math.min(r.left,innerWidth-w-8))+scrollX+"px"; const below=innerHeight-r.bottom, h=pop.offsetHeight||300; pop.style.top=(below<h+16&&r.top>h+16?r.top-h-6:r.bottom+6)+scrollY+"px"; }
function openCombo(inp,all){ const kind=inp.dataset.combo, cb=inp.closest(".cb"); $$(".pop").forEach(p=>p.remove()); CAL=null; const r=inp.getBoundingClientRect(), pop=document.createElement("div");
  pop.className="pop cpop"; pop.dataset.for=inp.id; pop.style.width=r.width+"px"; pop.innerHTML=comboHtmlRows(comboRows(kind,inp.value,all),inp.value); document.body.appendChild(pop); placePop(pop,r,r.width); cb.classList.add("open"); inp.setAttribute("aria-expanded","true"); }
function refreshCombo(inp){ const pop=$(".cpop"); if(!pop) return openCombo(inp,false); pop.innerHTML=comboHtmlRows(comboRows(inp.dataset.combo,inp.value,false),inp.value); }
function pickCombo(inp,v){ inp.value=v; closePops(); inp.dispatchEvent(new Event("change",{bubbles:true})); }
function openCal(anchor,opt){ $$(".pop").forEach(p=>p.remove()); const v=opt.value||REAL.today, d=new Date(v+"T12:00:00"), pop=document.createElement("div"); pop.className="pop calpop"; pop.setAttribute("role","dialog"); pop.setAttribute("aria-label","Pick a date");
  CAL={y:d.getFullYear(),m:d.getMonth(),sel:opt.value||"",onPick:opt.onPick,anchor}; pop.innerHTML=calHtml(CAL.y,CAL.m,CAL.sel); document.body.appendChild(pop); placePop(pop,anchor.getBoundingClientRect(),312); }
function calGo(n){ CAL.m+=n; if(CAL.m<0){ CAL.m=11; CAL.y--; } if(CAL.m>11){ CAL.m=0; CAL.y++; } const pop=$(".calpop"); pop.innerHTML=calHtml(CAL.y,CAL.m,CAL.sel); const g=pop.querySelector(".calg"); g.classList.add("swap"); }
function calPick(iso){ const cb=CAL.onPick; closePops(); cb(iso); }

/* the controls open on click or focus; capture phase so the page-level click handler does not close them */
document.addEventListener("click",e=>{ const t=e.target, inp=t.closest&&t.closest("[data-combo]"), db=t.closest&&t.closest("[data-date]");
  if(inp){ e.stopImmediatePropagation(); if(!$(".cpop")||$(".cpop").dataset.for!==inp.id) openCombo(inp,true); return; }
  if(db){ e.stopImmediatePropagation(); if($(".calpop")&&CAL&&CAL.anchor===db){ closePops(); return; } openCal(db,{value:db.dataset.v,onPick:iso=>setDate(db,iso)}); return; } },true);
document.addEventListener("focusin",e=>{ const inp=e.target.closest&&e.target.closest("[data-combo]"); if(inp&&(!$(".cpop")||$(".cpop").dataset.for!==inp.id)) openCombo(inp,true); });
document.addEventListener("input",e=>{ const el=e.target; if(el.dataset&&el.dataset.combo) refreshCombo(el); if(el.hasAttribute&&el.hasAttribute("data-grow")) growEl(el); });
document.addEventListener("mousedown",e=>{ if(e.target.closest&&e.target.closest(".cpop")) e.preventDefault(); });
document.addEventListener("keydown",e=>{ const inp=e.target.closest&&e.target.closest("[data-combo]"); if(!inp) return; const pop=$(".cpop"); if(!pop){ if(e.key==="ArrowDown"){ e.preventDefault(); openCombo(inp,true); } return; }
  const o=$$("button",pop); let i=o.findIndex(x=>x.classList.contains("sel"));
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){ e.preventDefault(); o.forEach(x=>x.classList.remove("sel")); i=e.key==="ArrowDown"?Math.min(i+1,o.length-1):Math.max(i-1,0); if(o[i]){ o[i].classList.add("sel"); o[i].scrollIntoView({block:"nearest"}); } }
  else if(e.key==="Enter"){ e.preventDefault(); e.stopImmediatePropagation(); const t=o[Math.max(i,0)]; if(t) pickCombo(inp,t.dataset.cv); else closePops(); }
  else if(e.key==="Escape"||e.key==="Tab"){ if(e.key==="Escape") e.stopPropagation(); closePops(); } },true);
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("[data-cv]")){ const pop=b.closest(".cpop"), inp=pop&&document.getElementById(pop.dataset.for); if(inp) pickCombo(inp,b.dataset.cv); return; }
  if(b=t.closest("[data-cn]")){ if(CAL) calGo(+b.dataset.cn); return; }
  if(b=t.closest("[data-cd]")){ if(CAL) calPick(b.dataset.cd); return; }
  if(b=t.closest("[data-cq]")){ if(CAL) calPick(b.dataset.cq==="x"?"":addDays(+b.dataset.cq)); return; } });
addEventListener("scroll",e=>{ if(e.target.nodeType===1&&e.target.closest(".pop")) return; if(CAL||$(".cpop")) closePops(); },true);
