/* v15 behaviour: groups reorder when priorities change, and can be ranked as a whole */
function toast(msg,undo,label){ let t=$("#toast"); if(!t){ t=document.createElement("div"); t.id="toast"; t.className="toast"; t.setAttribute("role","status"); document.body.appendChild(t); }
  t.innerHTML=`<span>${esc(msg)}</span>${undo?`<button class="tu">${esc(label||"Undo")}</button>`:""}`; if(undo) t.querySelector(".tu").onclick=()=>{ undo(); t.classList.remove("show"); };
  t.classList.remove("show"); void t.offsetWidth; t.classList.add("show"); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove("show"),4200); }
const visibleOrder=()=>planData().gs.filter(g=>g.items.some(x=>!ST.done.has(x.k))).map(g=>g.name);
function markMoved(name,dir){ const g=$(`#plan .grp[data-name="${CSS.escape(name)}"]`); if(!g) return; const nm=g.querySelector(".gh .nm"); if(!nm) return; g.querySelectorAll(".mv").forEach(x=>x.remove());
  nm.insertAdjacentHTML("afterend",`<span class="mv">${dir<0?"↑ Moved up":"↓ Moved down"}</span>`); setTimeout(()=>{ const m=g.querySelector(".mv"); if(m) m.classList.add("out"); setTimeout(()=>m&&m.remove(),400); },2800); }
/* after something changed a group's priority: reorder it (Mantis order) or suggest it (your own order) */
function afterPriorityChange(before,name){ if(!name) return; const after=visibleOrder(), bi=before.indexOf(name), ai=after.indexOf(name);
  if(ST.sort!=="mine"){ if(bi>=0&&ai>=0&&ai!==bi) markMoved(name,ai<bi?-1:1); return; }
  const comp=computedOrder("mantis"), ci=comp.indexOf(name); if(ci>=0&&ai>=0&&ci<ai) toast(`${name} now ranks higher in Mantis order.`,()=>{ initManual(); const arr=ST.manual.groups; arr.splice(arr.indexOf(name),1); arr.splice(Math.max(0,Math.min(ci,arr.length)),0,name); rerenderPlan(); },"Move up"); }
const _add2=addTask; addTask=function(){ const g=ST.addf.g, before=visibleOrder(); ST.rankDirty=true; _add2();
  if(ST.sort==="mine"&&ST.manual){ const x=ST.newTasks[ST.newTasks.length-1]; if(x){ const a=ST.manual.items[x.g]||(ST.manual.items[x.g]=[]); if(!a.includes(x.k)) a.unshift(x.k); if(!ST.manual.groups.includes(x.g)) ST.manual.groups.push(x.g); rerenderPlan(); const r=$(`#plan .trow[data-k="${x.k}"]`); if(r){ r.classList.add("flash"); setTimeout(()=>r.classList.remove("flash"),1900); r.scrollIntoView({block:"nearest",behavior:REDUCED?"auto":"smooth"}); } } }
  afterPriorityChange(before,g); };
const _sv2=saveTask; saveTask=function(f){ const k=+f.dataset.k, t=allTasks().find(x=>x.k===k), before=visibleOrder(); ST.rankDirty=true; _sv2(f); const nt=allTasks().find(x=>x.k===k); afterPriorityChange(before,nt&&nt.g); };
const _mv2=moveTaskTo; moveTaskTo=function(k,g,tk,b){ const before=visibleOrder(); ST.rankDirty=true; _mv2(k,g,tk,b); afterPriorityChange(before,g); };
/* the sort menu always reorders from scratch */
const _ps=openSort; openSort=function(b){ ST.rankDirty=true; _ps(b); };

/* ranking whole groups: handle, menu, keyboard */
function moveGroup(name,dir,top){ initManual(); const vis=visibleOrder(), arr=ST.manual.groups, i=vis.indexOf(name); if(i<0) return; let j=top?0:i+dir; if(j<0||j>=vis.length||j===i) return;
  arr.splice(arr.indexOf(name),1); const ref=vis[j]; const at=arr.indexOf(ref); arr.splice(top?at:(dir>0?at+1:at),0,name); ST.sort="mine"; rerenderPlan(); const h=$(`#plan .grp[data-name="${CSS.escape(name)}"] .gh`); if(h&&top!==true) h.focus({preventScroll:true}); }
document.addEventListener("dragstart",e=>{ const grip=e.target.closest&&e.target.closest(".ggrip"); if(!grip) return; const grp=grip.closest(".grp"); ST.drag={t:"grp",g:grp.dataset.name}; grp.classList.add("dragging"); e.dataTransfer.effectAllowed="move"; e.dataTransfer.setData("text/plain","group"); try{ e.dataTransfer.setDragImage(grp.querySelector(".gh"),24,24); }catch(x){} });
document.addEventListener("keydown",e=>{ const gh=document.activeElement&&document.activeElement.closest&&document.activeElement.closest("#plan .grp > .gh"); if(!gh||!e.altKey||(e.key!=="ArrowUp"&&e.key!=="ArrowDown")) return; e.preventDefault(); moveGroup(gh.closest(".grp").dataset.name,e.key==="ArrowUp"?-1:1); });
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("[data-gmenu]")){ $$(".pop").forEach(p=>p.remove()); const r=b.getBoundingClientRect(), pop=document.createElement("div"); pop.className="pop"; pop.setAttribute("role","menu"); pop.dataset.g=b.dataset.gmenu; const vis=visibleOrder(), i=vis.indexOf(b.dataset.gmenu);
    pop.innerHTML=(i>0?`<button role="menuitem" data-gm="top">Move to top</button><button role="menuitem" data-gm="up">Move up</button>`:"")+(i>=0&&i<vis.length-1?`<button role="menuitem" data-gm="down">Move down</button>`:"")+(ST.manual?`<button role="menuitem" data-gm="reset">Back to Mantis order</button>`:"");
    pop.style.left=(Math.max(8,r.right-200)+scrollX)+"px"; pop.style.top=(r.bottom+scrollY+6)+"px"; document.body.appendChild(pop); return; }
  if(b=t.closest("[data-gm]")){ const p=b.closest(".pop"), name=p.dataset.g, a=b.dataset.gm; p.remove(); if(a==="reset"){ ST.manual=null; ST.sort="mantis"; ST.rankDirty=true; rerenderPlan(); toast("Back to Mantis order"); } else moveGroup(name,a==="up"?-1:1,a==="top"); } });
