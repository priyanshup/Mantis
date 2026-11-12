/* behaviour: motion, toasts, delegated clicks, drawers, search */
const main=$("#main"), nav=$("#nav"), layer=$("#layer");
const WALL={
 today:()=>`<g>${Array.from({length:48},(_,i)=>`<rect x="98.5" y="8" width="3" height="${i%4===0?22:14}" rx="1.5" transform="rotate(${i*7.5} 100 100)"/>`).join("")}</g><circle cx="100" cy="100" r="50"/><path d="M100 100V66M100 100l20 12"/>`,
 meetings:()=>`<rect x="24" y="34" width="152" height="136" rx="16"/><path d="M24 66h152M64 20v28M136 20v28"/>${[0,1,2,3,4].map(c=>[0,1,2].map(r=>`<rect x="${42+c*28}" y="${84+r*26}" width="16" height="14" rx="4"/>`).join("")).join("")}`,
 features:()=>`<path d="M100 22 176 62 100 102 24 62Z"/><path d="M24 92l76 40 76-40"/><path d="M24 122l76 40 76-40"/>`,
 questions:()=>`<circle cx="100" cy="100" r="78"/><path d="M72 82a28 28 0 1 1 42 24c-10 6-14 12-14 22v6"/><circle cx="100" cy="150" r="2.5"/>`,
 sources:()=>`<rect x="48" y="22" width="104" height="120" rx="12"/><path d="M68 54h64M68 78h64M68 102h40"/><path d="M30 164h140M30 164l10-14M170 164l-10-14"/>`,
 growth:()=>`<path d="M24 172h152"/>${[0,1,2,3,4].map(i=>`<rect x="${34+i*30}" y="${150-i*24}" width="20" height="${20+i*24}" rx="6"/>`).join("")}<path d="M150 56c14-4 22-14 24-30-16 2-26 10-24 30Z"/>`};
(function(){ const w=document.createElement("div"); w.className="wall"; w.setAttribute("aria-hidden","true"); w.innerHTML=Object.keys(WALL).map(k=>`<svg data-w="${k}" viewBox="0 0 200 200" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">${WALL[k]()}</svg>`).join(""); document.body.prepend(w); })();
const setWall=key=>$$(".wall svg").forEach(s=>s.classList.toggle("on",s.dataset.w===key));

let toastT;
function burst(tick){ const svg=tick.ownerSVGElement, a=(+tick.dataset.a)*Math.PI/180, x=105+93*Math.sin(a), y=105-93*Math.cos(a);
  for(let i=0;i<9;i++){ const c=document.createElementNS("http://www.w3.org/2000/svg","circle"), ang=a+(i-4)*0.42, d=16+Math.random()*12;
    c.setAttribute("cx",x); c.setAttribute("cy",y); c.setAttribute("r",i%2?2.3:1.7); c.setAttribute("fill",i%3?"var(--leaf)":"var(--accent)"); c.setAttribute("class","puff");
    c.style.setProperty("--dx",(Math.sin(ang)*d).toFixed(1)+"px"); c.style.setProperty("--dy",(-Math.cos(ang)*d).toFixed(1)+"px"); svg.appendChild(c); setTimeout(()=>c.remove(),800); } }
function collapse(el,done){ el.style.height=el.offsetHeight+"px"; el.style.overflow="hidden"; requestAnimationFrame(()=>{ el.style.transition="height .45s cubic-bezier(.32,.72,0,1),opacity .3s,padding .45s,min-height .45s"; el.style.height="0"; el.style.minHeight="0"; el.style.opacity="0"; el.style.paddingTop="0"; el.style.paddingBottom="0"; }); setTimeout(done,480); }
function lightRing(g){ const ring=$("#ring"); if(!ring) return; ring.querySelectorAll(".tick").forEach(t=>t.classList.remove("on")); if(g){ ring.dataset.hl=g.dataset.g; ring.querySelectorAll(".tick.g"+g.dataset.g).forEach(t=>t.classList.add("on")); } else delete ring.dataset.hl; }

/* done, restore */
function refreshHist(){ const box=$("#groups"); if(!box) return; const old=box.querySelector(".hist"), was=old&&old.classList.contains("open"); if(old) old.remove(); const h=histHtml(); if(h){ box.insertAdjacentHTML("beforeend",h); if(was) box.querySelector(".hist").classList.add("open"); } }
function rerenderPlan(openDecide){ const plan=$("#plan"); if(!plan) return; plan.innerHTML=planInner(planData()); const d=plan.querySelector(".decide"); if(d&&openDecide) d.classList.add("open"); lightRing(plan.querySelector(".grp.open")); }

/* drawers, search, pickers */
function close(){ layer.innerHTML=""; $$(".pop").forEach(x=>x.remove()); }
function drawer(title,body,cls){ layer.innerHTML=`<div class="scrim"></div><aside class="drawer ${cls||""}" role="dialog" aria-label="${title}"><div class="hd"><h2>${title}</h2><button class="ic" aria-label="Close" data-act="close-layer"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div><div id="dbody">${body}</div></aside>`; layer.querySelector(".scrim").onclick=close; layer.querySelector(".hd .ic").onclick=close; }
function allTab(tab){ const P=planData();
  const tabs=`<div class="seg"><button data-tf="Open" aria-pressed="${tab==="Open"}">Open<span class="m">${P.n-ST.done.size}</span></button><button data-tf="Done" aria-pressed="${tab==="Done"}">Done<span class="m">${ST.done.size}</span></button><button data-tf="Archived" aria-pressed="${tab==="Archived"}">Archived<span class="m">${EXTRA.archN}</span></button></div>`;
  if(tab==="Open") return tabs+P.gs.map(g=>{ const live=g.items.filter(x=>!ST.done.has(x.k)); return live.length?`<div class="dgrp"><div class="u-m-14-0-2 cap muted">${esc(g.name)}</div><ul class="rows">${live.map(trow).join("")}</ul></div>`:""; }).join("");
  if(tab==="Done") return tabs+(ST.done.size?`<ul class="rows">${[...ST.done].map(k=>`<li class="trow done"><button class="ck" aria-pressed="true" data-restore="${k}" aria-label="Bring back">${CK}</button><span class="t clamp">${esc(taskByK(k).t)}</span><span class="when">Bring back</span></li>`).join("")}</ul>`:`<p class="zero">Nothing done yet today.</p>`);
  return tabs+`<ul class="rows">${EXTRA.arch.map(a=>`<li class="trow done"><span class="u-bg-fill-2 u-bc-transparent ck" aria-hidden="true"></span><span class="t clamp">${esc(a.t)}</span><span class="when">${fmt(a.d)}</span></li>`).join("")}</ul><p class="u-mt8 hint">Latest ${EXTRA.arch.length} of ${EXTRA.archN}. Older ones are searchable.</p>`; }
function refreshQ(){ const ql=$("#ql"); ql.classList.remove("swap"); void ql.offsetWidth; ql.classList.add("swap"); ql.innerHTML=qList(); $$("[data-pk]").forEach(b=>{ const k=b.dataset.pk; b.textContent=QF[k]; b.classList.toggle("set",QOPT[k][0]!==QF[k]); }); }

/* screens */
function wire(id){ if(id==="today") lightRing($("#plan .grp.open")); $$(".card,.fcard,.head").forEach((el,i)=>{ if(!el.classList.contains("rise")&&!el.hasAttribute("data-still")){ el.classList.add("rise"); el.style.setProperty("--i",Math.min(i,8)); } }); }
function show(id){ id=id||"today"; const key=id==="promotions"?"features":id, idx=Math.max(0,TABS.findIndex(t=>t[0]===key));
  document.documentElement.style.setProperty("--dx",((idx>=prevIdx?1:-1)*26)+"px"); prevIdx=idx;
  nav.querySelectorAll("button").forEach(b=>{ if(b.dataset.t===key) b.setAttribute("aria-current","page"); else b.removeAttribute("aria-current"); });
  setWall(key); moveInd();
  const render=()=>{ main.innerHTML=(S[id]||S.today)(); wire(id); scrollTo(0,0); main.removeAttribute("aria-busy"); window.__appReady=true; UI.shown(id); };
  if(document.startViewTransition&&!matchMedia("(prefers-reduced-motion: reduce)").matches) document.startViewTransition(render); else render(); }
nav.innerHTML=TABS.map(t=>`<button data-t="${t[0]}">${t[1]}${t[2]?`<span class="n">${t[2]}</span>`:""}</button>`).join("");
nav.onclick=e=>{ const b=e.target.closest("button"); if(b) location.hash=b.dataset.t; };
addEventListener("hashchange",()=>show(location.hash.slice(1))); 

document.addEventListener("click",e=>{ const t=e.target; let b;
  if(!t.closest(".pop")&&!t.closest("[data-pk]")) $$(".pop").forEach(p=>p.remove());
  if(b=t.closest(".seg button")){ b.parentElement.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false")); b.setAttribute("aria-pressed","true");
    if(b.dataset.tf){ $("#dbody").innerHTML=allTab(b.dataset.tf); } if(b.dataset.qg){ ST.qGroup=b.dataset.qg; refreshQ(); } return; }
  if(b=t.closest("[data-ck]")){ const k=+b.dataset.ck; if(ST.done.has(k)) restoreTask(k); else doneTask(k); return; }
  if(b=t.closest("[data-restore]")){ const k=+b.dataset.restore; restoreTask(k); if($(".drawer")) $("#dbody").innerHTML=allTab("Done"); return; }
  if(b=t.closest("[data-restores]")){ ST.gone.delete("s"+b.dataset.restores); rerenderPlan(true); toast("Back in your suggestions"); return; }
  if(b=t.closest("[data-hh]")){ b.closest(".hist").classList.toggle("open"); return; }
  if(b=t.closest("[data-tp]")){ b.closest(".tp").classList.toggle("open"); return; }
  if(b=t.closest(".gh")){ const g=b.closest(".grp"), d=b.closest(".decide");
    if(g){ const was=g.classList.contains("open"); g.parentElement.querySelectorAll(".grp").forEach(x=>{ x.classList.remove("open"); x.querySelector(".gh").setAttribute("aria-expanded","false"); }); if(!was){ g.classList.add("open"); b.setAttribute("aria-expanded","true"); ST.open=+g.dataset.g; } else ST.open=-1; lightRing(was?null:g); }
    else if(d){ d.classList.toggle("open"); b.setAttribute("aria-expanded",d.classList.contains("open")); } return; }
  if(b=t.closest("[data-more]")){ const acc=b.previousElementSibling; if(acc&&acc.classList.contains("more-acc")){ const open=acc.classList.toggle("open"); if(!b.dataset.t) b.dataset.t=b.textContent; b.textContent=open?"Show fewer":b.dataset.t; const g=b.closest(".grp"); if(g){ if(open) ST.expanded.add(g.dataset.name); else ST.expanded.delete(g.dataset.name); } } return; }
  if(b=t.closest("[data-all]")){ drawer("All tasks",allTab("Open"),"wide fix"); return; }
  if(b=t.closest("[data-sa]")){ const i=+b.dataset.sa, s=EXTRA.sugg[i], li=b.closest("li"); ST.gone.add("s"+i); ST.added.push({t:s.t,p:s.p||"high",g:"Other tasks",due:"",k:900+i}); collapse(li,()=>rerenderPlan(true)); toast("Added to your plan"); return; }
  if(b=t.closest("[data-sd]")){ const i=+b.dataset.sd, li=b.closest("li"); ST.gone.add("s"+i); collapse(li,()=>rerenderPlan(true)); toast("Dismissed for today.",()=>{ ST.gone.delete("s"+i); rerenderPlan(true); }); return; }
  if(b=t.closest("[data-keep]")){ ST.carryKept=true; collapse(b.closest("li"),()=>rerenderPlan(true)); toast("Kept "+EXTRA.carried+" tasks for today"); return; }
  if(b=t.closest("[data-review]")){ toast("In the real site this steps through them one at a time."); return; }
  if(b=t.closest("[data-copy]")){ navigator.clipboard&&navigator.clipboard.writeText(b.dataset.copy).catch(()=>{}); const nl=b.dataset.copy.split("\n").length; toast(nl>1?"Copied "+nl+" lines":"Copied"); return; }
  if(b=t.closest("[data-msg]")){ const n=b.dataset.msg; navigator.clipboard&&navigator.clipboard.writeText(`Hi ${n.split(" ")[0]}, a quick check on:\n`+WANT[n].items.map(x=>"• "+x).join("\n")).catch(()=>{}); toast("Chase message for "+n.split(" ")[0]+" copied"); return; }
  if(b=t.closest("[data-qcopy]")){ const n=b.dataset.qcopy; navigator.clipboard&&navigator.clipboard.writeText(`Hi ${n.split(" ")[0]}, a few questions:\n`+qFilter().filter(q=>q.who===n).map(q=>"• "+q.q).join("\n")).catch(()=>{}); toast("Message for "+n.split(" ")[0]+" copied"); return; }
  if(b=t.closest("[data-qans]")){ const li=b.closest("li"); b.setAttribute("aria-pressed","true"); li.classList.add("done"); setTimeout(()=>collapse(li,()=>{ li.remove(); }),600); toast("Marked answered. Mantis closes it on the next pull."); return; }
  if(b=t.closest("[data-pk]")){ const o=$(".pop"); if(o&&o.dataset.k===b.dataset.pk) o.remove(); else openPick(b,b.dataset.pk); return; }
  if(b=t.closest("[data-po]")){ QF[b.parentElement.dataset.k]=b.dataset.po; b.parentElement.remove(); refreshQ(); return; }
  if(b=t.closest("[data-clearq]")){ Object.assign(QF,{who:"Anyone",feat:"All features",pri:"Any priority"}); show("questions"); return; }
  if(b=t.closest("[data-day]")){ ST.wkSel=+b.dataset.day; $$("[data-day]").forEach(x=>x.setAttribute("aria-pressed",x===b)); const l=$("#dayl"); l.classList.remove("swap"); void l.offsetWidth; l.classList.add("swap"); l.innerHTML=dayList(ST.wkSel); return; }
  if(b=t.closest("[data-mi]")){ $$(".mrow").forEach(x=>x.setAttribute("aria-pressed","false")); b.setAttribute("aria-pressed","true"); const d=$("#mdet"); d.classList.remove("swap"); void d.offsetWidth; d.classList.add("swap"); d.innerHTML=meetDetail(+b.dataset.mi); return; }
  if(b=t.closest("[data-raise]")){ const on=b.getAttribute("aria-pressed")!=="true"; b.setAttribute("aria-pressed",on); b.closest("li").classList.toggle("done",on); if(on) ST.raised.add(b.dataset.raise); else ST.raised.delete(b.dataset.raise); toast(on?"Marked as raised":"Back on the list"); return; }
  if(b=t.closest("[data-take]")){ $("#take").classList.toggle("open"); return; }
  if(b=t.closest("[data-savetake]")){ toast("Takeaways saved. Mantis reads them on the next pull."); $("#take").classList.remove("open"); return; }
  if(b=t.closest(".sw")){ const on=!b.classList.contains("on"); b.classList.toggle("on",on); b.setAttribute("aria-checked",on); return; }
  if(b=t.closest("[data-add]")){ if(!$("#ctext").value.trim()){ toast("Paste or type something first"); $("#ctext").focus(); return; } (ST.inbox=ST.inbox||[]).push({t:($("#ctitle").value.trim()||$("#ctext").value.trim().slice(0,48))}); ST.pulled=true; $("#compose").innerHTML=composeHtml(); return; }
  if(b=t.closest("[data-again]")){ ST.pulled=false; $("#compose").innerHTML=composeHtml(); return; }
  if(b=t.closest("[data-pull]")){ const h=$(".top"); h.classList.remove("run"); toast("Pulling from Jira and Confluence…"); return; }
  if(b=t.closest(".fcard")){ if(b.dataset.f==="Promotions") location.hash="promotions"; return; }
  if(b=t.closest("[data-mode]")){ ST.mode=b.dataset.mode; $$(".lab button").forEach(x=>x.setAttribute("aria-pressed",x===b)); show(location.hash.slice(1)); return; }
});
document.addEventListener("keydown",e=>{ if(e.key==="Escape") close(); if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); search(); }
  });
$("#b-theme").onclick=()=>{ const r=document.documentElement, dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches; r.dataset.theme=dark?"light":"dark"; };
if(location.search.includes("dark")) document.documentElement.dataset.theme="dark";
