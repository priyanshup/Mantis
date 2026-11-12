/* v5 behaviour: ranking, groups leaving, messages, answers, growth, feature reader */
function refreshCounts(){ const P=planData(), left=P.n-ST.done.size, N=$("#ringN");
  if(N){ N.textContent=left?left:"✓"; N.classList.remove("bump"); void N.offsetWidth; N.classList.add("bump"); $("#ringL").textContent=ST.done.size?(left?"left":"all clear"):"planned"; }
  $$("#plan .grp").forEach(g=>{ const gr=P.gs[+g.dataset.g]; if(!gr) return; const live=gr.items.filter(x=>!ST.done.has(x.k)), c=g.querySelector(".cnt"); c.textContent=live.length||"Clear"; c.classList.toggle("ok",!live.length);
    const late=live.filter(x=>x.due&&x.due<REAL.today).length, s=g.querySelector(".gh .stk"); if(s){ if(late) s.lastChild.textContent=late+" late"; else s.remove(); }
    if(!live.length&&!g.dataset.leaving){ g.dataset.leaving="1"; setTimeout(()=>{ const cur=planData().gs[+g.dataset.g]; if(cur&&cur.items.some(x=>!ST.done.has(x.k))){ delete g.dataset.leaving; return; } collapse(g,()=>{ g.remove(); if(ST.openName===gr.name) ST.openName=null; lightRing(null); autoOpen(); ensureAllDone(); }); },1100); } });
  const plan=$("#plan"); if(plan) plan.classList.toggle("clear",left===0&&P.n>0); }

/* ranking */
function initManual(){ if(ST.manual) return; const P=planData(); ST.manual={groups:P.gs.map(g=>g.name),items:{}}; P.gs.forEach(g=>ST.manual.items[g.name]=g.items.map(x=>x.k)); }
function placeTask(k,tk,before,gname){ initManual(); const arr=ST.manual.items[gname]; arr.splice(arr.indexOf(k),1); let i=arr.indexOf(tk); if(!before) i++; arr.splice(i,0,k); ST.sort="mine"; rerenderPlan(); toast("Order saved.",()=>{ ST.manual=null; ST.sort="mantis"; rerenderPlan(); }); }
function placeGroup(name,tn,before){ initManual(); const arr=ST.manual.groups; arr.splice(arr.indexOf(name),1); let i=arr.indexOf(tn); if(!before) i++; arr.splice(i,0,name); ST.sort="mine"; rerenderPlan(); toast("Order saved.",()=>{ ST.manual=null; ST.sort="mantis"; rerenderPlan(); }); }
function moveTask(k,dir){ const P=planData(); initManual(); const g=P.gs.find(x=>x.items.some(y=>y.k===k)); if(!g) return; const arr=ST.manual.items[g.name]; const i=arr.indexOf(k); let j=i+dir; while(j>=0&&j<arr.length&&ST.done.has(arr[j])) j+=dir; if(j<0||j>=arr.length) return; [arr[i],arr[j]]=[arr[j],arr[i]]; ST.sort="mine"; rerenderPlan(); const ck=$(`#plan .ck[data-ck="${k}"]`); ck&&ck.focus(); }
function clearIns(){ $$(".ins-before,.ins-after,.dragging").forEach(x=>x.classList.remove("ins-before","ins-after","dragging")); }
document.addEventListener("mousedown",e=>{ const h=e.target.closest&&e.target.closest("#plan .gh"); $$("#plan .grp[draggable]").forEach(g=>g.removeAttribute("draggable")); if(h&&!e.target.closest(".decide")){ const g=h.closest(".grp"); if(g) g.setAttribute("draggable","true"); } });
document.addEventListener("dragstart",e=>{ const li=e.target.closest&&e.target.closest("#plan .trow[draggable]"), g=e.target.closest&&e.target.closest("#plan .grp");
  if(li){ ST.drag={t:"row",k:+li.dataset.k,g:li.closest(".grp").dataset.name}; li.classList.add("dragging"); e.dataTransfer.effectAllowed="move"; e.dataTransfer.setData("text/plain","task"); e.stopPropagation(); }
  else if(g&&g.getAttribute("draggable")){ ST.drag={t:"grp",g:g.dataset.name}; g.classList.add("dragging"); e.dataTransfer.effectAllowed="move"; e.dataTransfer.setData("text/plain","group"); } });
document.addEventListener("dragover",e=>{ if(!ST.drag) return; let el;
  if(ST.drag.t==="row"){ el=e.target.closest("#plan .trow[draggable]"); if(!el||+el.dataset.k===ST.drag.k||el.closest(".grp").dataset.name!==ST.drag.g) return; }
  else { el=e.target.closest("#plan .grp"); if(!el||el.dataset.name===ST.drag.g) return; }
  e.preventDefault(); const r=el.getBoundingClientRect(), before=(e.clientY-r.top)<r.height/2; $$(".ins-before,.ins-after").forEach(x=>x.classList.remove("ins-before","ins-after")); el.classList.add(before?"ins-before":"ins-after"); ST.drag.over={el,before}; });
document.addEventListener("drop",e=>{ if(!ST.drag||!ST.drag.over) return; e.preventDefault(); const d=ST.drag, o=d.over; ST.drag=null; clearIns();
  if(d.t==="row") placeTask(d.k,+o.el.dataset.k,o.before,d.g); else placeGroup(d.g,o.el.dataset.name,o.before); });
document.addEventListener("dragend",()=>{ ST.drag=null; clearIns(); $$("#plan .grp[draggable]").forEach(g=>g.removeAttribute("draggable")); });
document.addEventListener("keydown",e=>{ const ck=document.activeElement&&document.activeElement.closest&&document.activeElement.closest("#plan .ck[data-ck]"); if(ck&&e.altKey&&(e.key==="ArrowUp"||e.key==="ArrowDown")){ e.preventDefault(); moveTask(+ck.dataset.ck,e.key==="ArrowUp"?-1:1); } });
function openSort(btn){ $$(".pop").forEach(p=>p.remove()); const r=btn.getBoundingClientRect(), pop=document.createElement("div"); pop.className="pop"; pop.setAttribute("role","menu");
  pop.innerHTML=["mantis","due","priority"].concat(ST.manual?["mine"]:[]).map(o=>`<button role="menuitem" data-ps="${o}" class="${ST.sort===o?"cur":""}">${SORTN[o]}</button>`).join("")+(ST.manual?`<button role="menuitem" data-ps="reset">Reset my order</button>`:"");
  pop.style.left=(Math.max(8,r.right-210)+scrollX)+"px"; pop.style.top=(r.bottom+scrollY+6)+"px"; document.body.appendChild(pop); }

/* messages */
function sheet(title,text,note){ layer.innerHTML=`<div class="scrim"></div><div class="sheet" role="dialog" aria-label="${esc(title)}"><h2>${esc(title)}</h2><p class="u-m-6-0-12 muted">${esc(note)}</p><textarea class="u-minh-240 field" id="stext">${esc(text)}</textarea><div class="acts"><button class="btn2" data-sheetcopy>Copy message</button><button class="link" data-sheetx>Cancel</button></div></div>`; layer.querySelector(".scrim").onclick=close; $("#stext").focus(); }
const NOTE="This is exactly what will be copied. Edit it if you like. Mantis does not send it.";

/* growth */
const gTabsHtml=()=>{ const L=gLists(); return [["Proposed",L.prop.length],["In progress",L.prog.length],["Done",L.done.length],["Hidden",L.hidden]].map(([n,c])=>`<button data-gv="${n}" aria-pressed="${ST.gv===n}">${n}<span class="m">${c}</span></button>`).join(""); };
function refreshG(){ const t=$("#gtabs"); if(t) t.innerHTML=gTabsHtml(); const gl=$("#glist"); if(gl){ gl.classList.remove("swap"); void gl.offsetWidth; gl.classList.add("swap"); gl.innerHTML=gListHtml(); } const h=$("#ghead"); if(h) h.innerHTML=gHead(); }
function readForm(){ const t=$("#gtitle"), w=$("#gwhy"); if(t) ST.gform.title=t.value; if(w) ST.gform.why=w.value; }
function renderForm(){ readForm(); $("#gform").innerHTML=gFormHtml(); if(ST.gform.title) $("#gtitle").value=ST.gform.title; if(ST.gform.why) $("#gwhy").value=ST.gform.why; }

document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("[data-sort]")){ openSort(b); return; }
  if(b=t.closest("[data-ps]")){ const o=b.dataset.ps; if(o==="reset"){ ST.manual=null; ST.sort="mantis"; } else ST.sort=o; $$(".pop").forEach(p=>p.remove()); rerenderPlan(); return; }
  if(b=t.closest("[data-showover]")){ const rows=$$("#plan .trow[data-over='1']:not(.done)"); if(!rows.length) return; const g=rows[0].closest(".grp"); if(g&&!g.classList.contains("open")) g.querySelector(".gh").click();
    setTimeout(()=>{ rows[0].scrollIntoView({block:"center",behavior:"smooth"}); rows.forEach(r=>{ r.classList.add("flash"); setTimeout(()=>r.classList.remove("flash"),1900); }); },280); return; }
  if(b=t.closest("[data-who]")){ QF.who=b.dataset.who; QF.feat="All features"; QF.pri="Any priority"; ST.qGroup="Who"; if(location.hash==="#questions") show("questions"); else location.hash="questions"; return; }
  if(b=t.closest("[data-qfeat]")){ QF.feat=b.dataset.qfeat; QF.who="Anyone"; QF.pri="Any priority"; ST.qGroup="Who"; location.hash="questions"; return; }
  if(b=t.closest("[data-chase]")){ const n=b.dataset.chase; sheet("Chase message for "+n.split(" ")[0],chaseText(n),NOTE); return; }
  if(b=t.closest("[data-qchase]")){ const n=b.dataset.qchase; sheet("Message for "+n.split(" ")[0],`Hi ${n.split(" ")[0]},\n\nA few questions when you have a minute:\n${qFilter().filter(q=>q.who===n).map(q=>"• "+q.q).join("\n")}\n\nThanks,`,NOTE); return; }
  if(b=t.closest("[data-sheetcopy]")){ navigator.clipboard&&navigator.clipboard.writeText($("#stext").value).catch(()=>{}); close(); toast("Message copied"); return; }
  if(b=t.closest("[data-sheetx]")){ close(); return; }
  if(b=t.closest("[data-qx]")){ const i=+b.dataset.qx, li=b.closest("li.qr"); if(!li) return; const on=!li.classList.contains("open"); li.classList.toggle("open",on); li.querySelector(".qrh").setAttribute("aria-expanded",on); on?ST.qx.add(i):ST.qx.delete(i); if(on) setTimeout(()=>{ const ta=li.querySelector("textarea"); ta&&ta.focus({preventScroll:true}); },420); return; }
  if(b=t.closest("[data-qsave]")){ const i=+b.dataset.qsave, li=b.closest("li.qr"), v=$("#qa"+i).value.trim(); if(!v){ toast("Type an answer first"); return; } ST.ans[i]=v; li.classList.add("answered");
    const w=li.querySelector(".qrh .when"); if(w){ const c=document.createElement("span"); c.className="chip ok"; c.textContent="In inbox"; w.replaceWith(c); } b.textContent="Update answer"; const sb=$("#sbar"); if(sb) sb.outerHTML=sbarHtml(); toast("Answer saved to the inbox");
    setTimeout(()=>{ li.classList.remove("open"); ST.qx.delete(i); li.querySelector(".qrh").setAttribute("aria-expanded","false"); },650); return; }
  if(b=t.closest("[data-gv]")){ ST.gv=b.dataset.gv; refreshG(); return; }
  if(b=t.closest("[data-gs]")){ const i=+b.dataset.gs, on=!ST.gsel.has(i); on?ST.gsel.add(i):ST.gsel.delete(i); b.setAttribute("aria-pressed",on); const bar=$("#gbar"); if(bar){ bar.classList.toggle("show",ST.gsel.size>0); bar.querySelector("b").textContent=ST.gsel.size; } return; }
  if(b=t.closest("[data-gx]")){ const li=b.closest("li.gr"), i=+b.dataset.gx, on=!li.classList.contains("open"); li.classList.toggle("open",on); b.setAttribute("aria-expanded",on); on?ST.qx.add("g"+i):ST.qx.delete("g"+i); return; }
  if(b=t.closest("[data-gk]")){ readForm(); ST.gform.kind=b.dataset.gk; $$("[data-gk]").forEach(x=>x.setAttribute("aria-pressed",x===b)); renderForm(); $$("[data-gk]").forEach(x=>x.setAttribute("aria-pressed",x.dataset.gk===ST.gform.kind)); return; }
  if(b=t.closest("[data-garea]")){ const a=b.dataset.garea, on=!ST.gform.areas.has(a); on?ST.gform.areas.add(a):ST.gform.areas.delete(a); b.classList.toggle("on",on); return; }
  if(b=t.closest("[data-gwhen]")){ ST.gform.when=b.dataset.gwhen; $$("[data-gwhen]").forEach(x=>x.classList.toggle("on",x===b)); return; }
  if(b=t.closest("[data-ft]")){ ST.ft=b.dataset.ft; const fb=$("#fbody"); fb.innerHTML=ftabHtml(); return; }
  if(b=t.closest("[data-st]")){ ST.st=+b.dataset.st; $$("[data-st]").forEach(x=>x.setAttribute("aria-pressed",x===b)); const r=$("#reader"); r.classList.remove("swap"); void r.offsetWidth; r.classList.add("swap"); r.innerHTML=readerHtml(FITEMS()[ST.st]); return; }
});
