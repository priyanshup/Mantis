/* v9 behaviour */
const _rc2=refreshCounts; refreshCounts=function(){ _rc2(); const w=$("#week"); if(w) w.innerHTML=weekInner(); };
const _rr2=rerenderPlan; rerenderPlan=function(o){ _rr2(o); const w=$("#week"); if(w) w.innerHTML=weekInner(); };
const _allTab=allTab; allTab=function(tab){ const s=_allTab(tab), i=s.indexOf("</div>")+6; return s.slice(0,i)+'<div class="dscroll">'+s.slice(i)+'</div>'; };
document.addEventListener("input",e=>{ const el=e.target; if(el.dataset&&el.dataset.pf!==undefined){ const o=$(".popopts"); if(o) o.innerHTML=pickRows(o.dataset.k,el.value); } });
document.addEventListener("keydown",e=>{ const el=e.target; if(!(el.dataset&&el.dataset.pf!==undefined)) return; const o=$$(".popopts button"); let i=o.findIndex(x=>x.classList.contains("sel"));
  if(e.key==="ArrowDown"||e.key==="ArrowUp"){ e.preventDefault(); o.forEach(x=>x.classList.remove("sel")); i=e.key==="ArrowDown"?Math.min(i+1,o.length-1):Math.max(i-1,0); if(o[i]){ o[i].classList.add("sel"); o[i].scrollIntoView({block:"nearest"}); } }
  else if(e.key==="Enter"){ e.preventDefault(); const t=o[Math.max(i,0)]; if(t) t.click(); } });
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(t.closest("[data-po]")) setTimeout(closePops,0);
  if(b=t.closest("[data-gomeet]")){ MEET.forEach(m=>delete m.next); MEET[+b.dataset.gomeet].next=true; go("meetings"); return; }
  if(b=t.closest("[data-agtask]")){ openTask(+b.dataset.agtask); return; } });
const brand=$(".brand"); if(brand) brand.addEventListener("click",e=>{ if(location.hash==="#today"||!location.hash){ e.preventDefault(); scrollTo({top:0,behavior:REDUCED?"auto":"smooth"}); } });

function openPick(btn,k){ closePops(); const r=btn.getBoundingClientRect(), pop=document.createElement("div"); pop.className="pop gpop"; pop.dataset.k=k; pop.setAttribute("role","menu"); const many=QOPT[k].length>4;
  pop.innerHTML=(many?`<input class="field" data-pf placeholder="Type to filter" autocomplete="off">`:"")+`<div class="gopts popopts" data-k="${k}">${pickRows(k,"")}</div>`; pop.style.width=Math.max(240,r.width)+"px"; document.body.appendChild(pop); placePop(pop,r,Math.max(240,r.width)); const i=pop.querySelector("input"); if(i) i.focus(); }
