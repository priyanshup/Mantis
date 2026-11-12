/* v14 behaviour: how the plan settles after you tick, add, move or snooze a task */
const leaveT={};
function glideRows(first){ if(REDUCED) return; $$("#plan .trow[data-k]").forEach(li=>{ const l=li.getBoundingClientRect(); if(l.height<=0) return; const f=first[li.dataset.k];
  if(!f){ li.animate([{opacity:0,transform:"translateY(12px)"},{opacity:1,transform:"none"}],{duration:440,easing:"cubic-bezier(.32,.72,0,1)"}); return; }
  const dx=f.left-l.left, dy=f.top-l.top; if(Math.abs(dx)>=1||Math.abs(dy)>=1) li.animate([{transform:`translate(${dx}px,${dy}px)`},{transform:"none"}],{duration:440,easing:"cubic-bezier(.32,.72,0,1)"}); }); }
const rowRects=()=>{ const r={}; $$("#plan .trow[data-k]").forEach(li=>{ const b=li.getBoundingClientRect(); if(b.height>0) r[li.dataset.k]=b; }); return r; };
/* a group always shows up to five tasks; the next ones move up from behind "more" */
function refillGroups(){ const plan=$("#plan"); if(!plan) return; const P=planData(), first=rowRects(); let changed=false;
  P.gs.forEach((g,gi)=>{ const el=plan.querySelector(`.grp[data-name="${CSS.escape(g.name)}"]`); if(!el||el.dataset.leaving) return; const live=g.items.filter(x=>!ST.done.has(x.k)).length, want=Math.min(live,5);
    const have=$$(".trow[data-k]",el).filter(li=>!li.closest(".more-acc")&&!li.classList.contains("done")&&!li.dataset.gone).length; if(have<want){ el.outerHTML=grpHtml(g,gi); changed=true; } });
  if(changed){ glideRows(first); lightRing($("#plan .grp.open")); } }
/* if the open group is gone, open the next one, unless you closed things yourself */
function autoOpen(){ const plan=$("#plan"); if(!plan||ST.userClosed||plan.querySelector(".grp.open")) return; const g=plan.querySelector(".grp:not([data-leaving])"); if(!g) return;
  g.classList.add("open"); g.querySelector(".gh").setAttribute("aria-expanded","true"); ST.openName=g.dataset.name; lightRing(g); }
function ensureAllDone(){ const box=$("#groups"); if(!box||box.querySelector(".grp:not([data-leaving])")||box.querySelector(".alldone")) return; const h=box.querySelector(".hist"); (h?h:box.querySelector(".dropz")||box).insertAdjacentHTML(h?"beforebegin":"beforebegin",allDoneHtml()); }
function settle(){ refreshHist(); refillGroups(); autoOpen(); ensureAllDone(); }
/* completing: tick now, stay for a moment so you can change your mind, then leave and let the rest move up */
function doneTask(k){ ST.done.add(k);
  $$(`.trow[data-k="${k}"]`).forEach(li=>{ li.classList.add("done"); const c=li.querySelector(".ck"); c&&c.setAttribute("aria-pressed","true"); });
  $$(`.tick[data-k="${k}"]`).forEach(t=>{ t.classList.add("done"); burst(t); });
  refreshCounts(); const P=planData(), left=P.n-ST.done.size, li=$(`#plan .trow[data-k="${k}"]`), g=li&&li.closest(".grp"), gl=g?P.gs[+g.dataset.g].items.filter(x=>!ST.done.has(x.k)).length:1;
  toast(left===0?"All tasks done.":gl===0?`${g.querySelector(".nm").textContent} done. ${left} left.`:`${left} left.`,()=>restoreTask(k));
  clearTimeout(leaveT[k]); leaveT[k]=setTimeout(()=>leaveRow(k),950); }
function leaveRow(k){ if(!ST.done.has(k)) return; const li=$(`#plan .trow[data-k="${k}"]`); if(!li){ settle(); return; }
  li.dataset.gone="1"; const had=li.contains(document.activeElement), sib=li.nextElementSibling||li.previousElementSibling, first=rowRects();
  collapse(li,()=>{ li.remove(); settle(); if(had&&sib){ const c=sib.querySelector(".ck"); c&&c.focus({preventScroll:true}); } }); }
function restoreTask(k){ ST.done.delete(k); clearTimeout(leaveT[k]); const li=$(`#plan .trow[data-k="${k}"]`);
  if(li&&!li.dataset.gone&&!li.closest("[data-leaving]")){ $$(`.trow[data-k="${k}"]`).forEach(r=>{ r.classList.remove("done"); const c=r.querySelector(".ck"); c&&c.setAttribute("aria-pressed","false"); }); $$(`.tick[data-k="${k}"]`).forEach(t=>t.classList.remove("done")); refreshCounts(); }
  else rerenderPlan();
  $$(`.drawer .trow[data-k="${k}"]`).forEach(r=>{ r.classList.remove("done"); const c=r.querySelector(".ck"); c&&c.setAttribute("aria-pressed","false"); }); toast("Restored"); }
/* where a task lands, it shows: its group opens, expands if needed, and scrolls into view */
const _add=addTask; addTask=function(){ if(ST.addf) ST.expanded.add(ST.addf.g); ST.userClosed=false; _add(); const r=$("#plan .trow.flash"); if(r) r.scrollIntoView({block:"nearest",behavior:REDUCED?"auto":"smooth"}); };
const _mv=moveTaskTo; moveTaskTo=function(k,g,tk,b){ ST.expanded.add(g); ST.userClosed=false; _mv(k,g,tk,b); };
const _sv=saveTask; saveTask=function(f){ const k=+f.dataset.k; _sv(f); const e=ST.edits[k]; if(e&&e.g&&!$(".drawer")){ ST.expanded.add(e.g); ST.userClosed=false; rerenderPlan(); } };
/* remember what you opened or closed on purpose */
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("#plan .grp > .gh")){ const g=b.closest(".grp"); if(g.classList.contains("open")){ ST.openName=g.dataset.name; ST.userClosed=false; } else { ST.openName=null; ST.userClosed=true; } return; }
  if(b=t.closest("[data-more]")) return;
  if(b=t.closest("[data-addfocus]")){ const i=$("#addin"); if(i){ i.focus(); i.scrollIntoView({block:"center",behavior:REDUCED?"auto":"smooth"}); } } });
/* a panel is open: the page behind stays still */
new MutationObserver(()=>document.documentElement.classList.toggle("locked",!!layer.querySelector(".drawer,.sheet,.srch"))).observe(layer,{childList:true});
