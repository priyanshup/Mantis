/* v6 behaviour: add and edit tasks, drag between groups, inbox, command palette, zing */
const REDUCED=matchMedia("(prefers-reduced-motion: reduce)").matches;
const go=h=>{ if(location.hash==="#"+h) show(h); else location.hash=h; };
function updInbox(){ const b=$("#ibadge"); if(!b) return; const n=inboxCount(); b.textContent=n; b.hidden=!n; }
function navFade(){ nav.classList.toggle("fade",nav.scrollWidth>nav.clientWidth+2); const a=nav.querySelector('[aria-current="page"]'); if(a&&nav.scrollWidth>nav.clientWidth+2) a.scrollIntoView({inline:"nearest",block:"nearest"}); }
function confetti(host){ if(!host||REDUCED) return; const c=document.createElement("div"); c.className="cf"; const cols=["var(--accent)","var(--leaf)","var(--ink)","var(--glow-3)"];
  for(let i=0;i<44;i++){ const p=document.createElement("i"); p.style.left=(Math.random()*100)+"%"; p.style.background=cols[i%4]; p.style.setProperty("--dx",((Math.random()-.5)*160).toFixed(0)+"px"); p.style.setProperty("--r",((Math.random()-.5)*720).toFixed(0)+"deg"); p.style.animationDelay=(Math.random()*.35).toFixed(2)+"s"; c.appendChild(p); }
  host.appendChild(c); setTimeout(()=>c.remove(),2500); }
const _rc=refreshCounts; refreshCounts=function(){ _rc(); const P=planData(); if(P.n&&P.n===ST.done.size) confetti($("#plan")); };
const _rr=rerenderPlan; rerenderPlan=function(openDecide){ const inp=$("#addin"), val=inp?inp.value:"", foc=inp&&document.activeElement===inp; _rr(openDecide); const n=$("#addin"); if(n){ n.value=val; if(foc) n.focus(); syncAdd(); } };

/* quick add */
function syncAdd(){ const o=$("#addopts"); if(o){ o.innerHTML=addOptsHtml(); const f=ST.addf; o.classList.toggle("has",!!(($("#addin")||{}).value||Object.keys(f.man).length||$(".pop"))); } }
function resetAdd(){ ST.addf={p:"medium",due:"",g:"Other tasks",ask:"",man:{},auto:{}}; syncAdd(); }
function addTask(){ const inp=$("#addin"), v=inp.value.trim(); if(!v){ toast("Type the task first"); return; } const f=ST.addf, k=2000+ST.nid++;
  const x={k,t:v,p:f.p,due:f.due,g:f.g,ask:f.ask,n:"",est:0,rem:"",src:"Added by you"}; ST.newTasks.push(x); ST.openName=x.g; inp.value=""; resetAdd(); rerenderPlan(); $("#addin").focus();
  const row=$(`#plan .trow[data-k="${k}"]`); if(row){ row.classList.add("flash"); setTimeout(()=>row.classList.remove("flash"),1900); }
  toast(`Added to ${x.g}`,()=>{ ST.edits[k]=Object.assign(ST.edits[k]||{},{del:true}); rerenderPlan(); }); }
function openAo(btn,kind){ $$(".pop").forEach(p=>p.remove()); const r=btn.getBoundingClientRect(), pop=document.createElement("div"); pop.className="pop"; pop.setAttribute("role","menu"); let h="";
  if(kind==="due"){ openCal(btn,{value:ST.addf.due,onPick:iso=>{ ST.addf.man.due=true; ST.addf.due=iso; syncAdd(); const i=$("#addin"); i&&i.focus(); }}); return; }
  if(kind==="p") h=["high","medium","low"].map(p=>`<button data-aov="p:${p}" class="${ST.addf.p===p?"cur":""}">${PN[p]}</button>`).join("");
  if(kind==="due") h=[["0","Today"],["1","Tomorrow"],["7","Next week"],["x","No date"]].map(([v,l])=>`<button data-aov="due:${v}">${l}</button>`).join("");
  if(kind==="g"){ pop.classList.add("gpop"); h=`<input class="field" data-gq placeholder="Find or create a group" autocomplete="off"><div class="gopts" id="gopts">${gOpts("")}</div>`; }
  pop.innerHTML=h; pop.style.left=(r.left+scrollX)+"px"; pop.style.top=(r.bottom+scrollY+6)+"px"; document.body.appendChild(pop); const i=pop.querySelector("input"); if(i) i.focus(); }
function gOpts(q){ const ql=q.trim().toLowerCase(), names=groupNames(), feats=FEATS.map(f=>f.title).filter(n=>!names.includes(n)), has=n=>!ql||n.toLowerCase().includes(ql);
  const rows=[...names.filter(has).map(n=>[n,"Group"]),...feats.filter(has).map(n=>[n,"Feature card"])]; const exact=[...names,...feats].some(n=>n.toLowerCase()===ql);
  if(q.trim()&&!exact) rows.push([q.trim(),"Create new group"]);
  return rows.map((r,i)=>`<button data-aov="g:${esc(r[0])}" class="${i===0?"sel":""} ${ST.addf.g===r[0]?"cur":""}">${r[1]==="Create new group"?"Create “"+esc(r[0])+"”":esc(r[0])}<span class="hint">${r[1]}</span></button>`).join("")||`<p class="u-p-8 zero">Nothing yet. Keep typing to create it.</p>`; }
function setAdd(kind,val){ if(kind==="g") ST.extraGroups.add(val); const f=ST.addf; f.man[kind]=true; if(kind==="due") f.due=val==="x"?"":addDays(+val); else f[kind]=val; syncAdd(); $$(".pop").forEach(p=>p.remove()); const i=$("#addin"); i&&i.focus(); }
document.addEventListener("input",e=>{ if(e.target.dataset&&e.target.dataset.gq!==undefined){ $("#gopts").innerHTML=gOpts(e.target.value); return; } if(e.target.id!=="addin") return; const r=parseTask(e.target.value), f=ST.addf; f.auto={};
  [["p","medium"],["due",""],["g","Other tasks"]].forEach(([k,d])=>{ if(!f.man[k]){ if(r[k]!==undefined){ f[k]=r[k]; f.auto[k]=true; } else f[k]=d; } }); f.ask=r.ask||""; syncAdd(); });
document.addEventListener("keydown",e=>{
  if(e.target.id==="tf-t"&&e.key==="Enter"){ e.preventDefault(); saveTask($(".tf")); return; }
  if(e.target.id==="addin"&&e.key==="Enter"){ e.preventDefault(); addTask(); return; }
  if(e.target.dataset&&e.target.dataset.gq!==undefined){ const o=$$("#gopts button"); let i=o.findIndex(x=>x.classList.contains("sel"));
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){ e.preventDefault(); o.forEach(x=>x.classList.remove("sel")); i=e.key==="ArrowDown"?Math.min(i+1,o.length-1):Math.max(i-1,0); if(o[i]){ o[i].classList.add("sel"); o[i].scrollIntoView({block:"nearest"}); } return; }
    if(e.key==="Enter"){ e.preventDefault(); const t=o[Math.max(i,0)]; if(t){ const [k,v]=t.dataset.aov.split(/:(.+)/); setAdd(k,v); } return; } }
  if(e.target.dataset&&e.target.dataset.edit!==undefined&&(e.key==="Enter"||e.key===" ")){ e.preventDefault(); openTask(+e.target.dataset.edit); return; }
  if(e.key==="Escape"&&e.target.id==="addin"){ e.target.blur(); return; }
  if(e.key.toLowerCase()==="n"&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!/INPUT|TEXTAREA|SELECT/.test((document.activeElement||{}).tagName||"")&&!layer.innerHTML){ e.preventDefault(); go("today"); setTimeout(()=>{ const i=$("#addin"); if(i){ i.focus(); i.scrollIntoView({block:"center",behavior:"smooth"}); } },location.hash==="#today"?0:420); } });

/* editor */
function openTask(k){ const x=allTasks().find(t=>t.k===k); if(!x) return; const fromAll=!!$(".drawer.fix"); ST.backAll=fromAll; drawer("Edit task",taskForm(x),"wide"); if(fromAll) $(".drawer .hd").insertAdjacentHTML("afterbegin",'<button class="link back" data-backall>← All tasks</button>'); $$("[data-grow]").forEach(growEl); }
function saveTask(f){ const k=+f.dataset.k, g=$("#tf-g").value.trim(); if(!$("#tf-t").value.trim()){ toast("A task needs a name"); return; }
  if(g&&!groupNames().includes(g)) ST.extraGroups.add(g); const pe=$("#tf-p .on"), ee=$("#tf-e .on");
  ST.edits[k]=Object.assign(ST.edits[k]||{},{t:$("#tf-t").value.trim(),p:pe?pe.dataset.tfp:"medium",due:$("#tf-due").dataset.v||"",g:g||"Other tasks",n:$("#tf-n").value,ask:$("#tf-ask").value,rem:$("#tf-rem").dataset.v||"",est:ee?+ee.dataset.tfe:0});
  ST.openName=ST.edits[k].g; afterEdit(); rerenderPlan(); toast("Saved"); }

/* drag between groups */
function moveTaskTo(k,gname,tk,before){ initManual(); const snap=JSON.stringify(ST.manual), prev=ST.edits[k]?{...ST.edits[k]}:null, ps=ST.sort;
  Object.values(ST.manual.items).forEach(a=>{ const i=a.indexOf(k); if(i>=0) a.splice(i,1); }); const arr=(ST.manual.items[gname]=ST.manual.items[gname]||[]);
  if(tk==null) arr.push(k); else { let i=arr.indexOf(tk); if(i<0) i=arr.length; if(!before) i++; arr.splice(i,0,k); }
  if(!ST.manual.groups.includes(gname)) ST.manual.groups.push(gname); ST.edits[k]=Object.assign(ST.edits[k]||{},{g:gname}); ST.sort="mine"; ST.openName=gname; rerenderPlan();
  toast(gname==="Other tasks"?"Taken out of its group":`Moved to ${gname}`,()=>{ ST.manual=JSON.parse(snap); if(prev) ST.edits[k]=prev; else delete ST.edits[k]; ST.sort=ps; rerenderPlan(); }); }
document.addEventListener("dragstart",()=>{ const p=$("#plan"); if(p) p.classList.add("drag-on"); });
document.addEventListener("dragend",()=>{ const p=$("#plan"); if(p) p.classList.remove("drag-on"); $$(".drop-on,.over").forEach(x=>x.classList.remove("drop-on","over")); });
document.addEventListener("dragover",e=>{ const d=ST.drag; if(!d||d.t!=="row") return; d.x=null; let el;
  if(el=e.target.closest("[data-dropz]")){ if(d.g!=="Other tasks"&&d.g!=="__flat"){ e.preventDefault(); e.stopImmediatePropagation(); clearIns(); el.classList.add("over"); d.x={zone:true}; } return; }
  el=e.target.closest("#plan .trow[draggable]"); if(el&&+el.dataset.k!==d.k&&el.closest(".grp").dataset.name!==d.g){ e.preventDefault(); e.stopImmediatePropagation(); const r=el.getBoundingClientRect(), before=(e.clientY-r.top)<r.height/2; clearIns(); $$(".drop-on").forEach(x=>x.classList.remove("drop-on")); el.classList.add(before?"ins-before":"ins-after"); d.x={tk:+el.dataset.k,g:el.closest(".grp").dataset.name,before}; return; }
  const gh=e.target.closest("#plan .gh"), g=gh&&gh.closest(".grp"); if(g&&g.dataset.name!==d.g){ e.preventDefault(); e.stopImmediatePropagation(); clearIns(); $$(".drop-on").forEach(x=>x.classList.remove("drop-on")); g.classList.add("drop-on"); d.x={g:g.dataset.name,tk:null}; } },true);
document.addEventListener("drop",e=>{ const d=ST.drag; if(!d||!d.x) return; e.preventDefault(); e.stopImmediatePropagation(); const x=d.x; ST.drag=null; clearIns(); $$(".drop-on,.over").forEach(y=>y.classList.remove("drop-on","over")); const p=$("#plan"); p&&p.classList.remove("drag-on");
  if(x.zone) moveTaskTo(d.k,"Other tasks",null,false); else moveTaskTo(d.k,x.g,x.tk,x.before); },true);

/* clicks */
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("[data-edit]")){ openTask(+b.dataset.edit); return; }
  if(b=t.closest("[data-tfp]")){ $$("#tf-p .chip").forEach(x=>x.classList.toggle("on",x===b)); return; }
  if(b=t.closest("[data-tfe]")){ $$("#tf-e .chip").forEach(x=>x.classList.toggle("on",x===b)); return; }
  if(b=t.closest("[data-tfd]")){ setDate($("#tf-due"),b.dataset.tfd==="x"?"":addDays(+b.dataset.tfd)); return; }
  if(b=t.closest("[data-tfmore]")){ $("#tf-more").classList.toggle("open"); return; }
  if(b=t.closest("[data-tfsave]")){ saveTask(b.closest(".tf")); return; }
  if(b=t.closest("[data-tfdone]")){ const k=+b.closest(".tf").dataset.k; afterEdit(); doneTask(k); return; }
  if(b=t.closest("[data-tfdel]")){ const k=+b.closest(".tf").dataset.k, prev=ST.edits[k]?{...ST.edits[k]}:null; ST.edits[k]=Object.assign(ST.edits[k]||{},{del:true}); afterEdit(); rerenderPlan(); toast("Task deleted",()=>{ if(prev) ST.edits[k]=prev; else delete ST.edits[k]; rerenderPlan(); }); return; }
  if(b=t.closest("[data-ao]")){ const o=$(".pop"); if(o&&o.dataset.ao===b.dataset.ao){ o.remove(); return; } openAo(b,b.dataset.ao); const p=$(".pop"); if(p) p.dataset.ao=b.dataset.ao; return; }
  if(b=t.closest("[data-aov]")){ const [k,v]=b.dataset.aov.split(/:(.+)/); setAdd(k,v); return; }
  if(b=t.closest("[data-inbox]")){ drawer("Inbox",inboxHtml()); return; }
  if(b=t.closest("[data-ibx]")){ const id=b.dataset.ibx; if(id[0]==="p") ST.inbox.splice(+id.slice(1),1); else delete ST.ans[id.slice(1)]; $("#dbody").innerHTML=inboxHtml(); const sb=$("#sbar"); if(sb) sb.outerHTML=sbarHtml(); return; } });

document.addEventListener("click",()=>setTimeout(updInbox,0));

/* command palette */
function search(){ layer.innerHTML=`<div class="scrim"></div><div class="srch" role="dialog" aria-label="Search and commands"><input id="cmdq" placeholder="Search, or type a command" autocomplete="off"><ul class="rows" id="cmdl"></ul></div>`; layer.querySelector(".scrim").onclick=close; const inp=$("#cmdq"); let sel=0, items=[];
  const all=()=>[{l:"Add a task",h:"Action",a:()=>{ close(); go("today"); setTimeout(()=>{ const i=$("#addin"); i&&i.focus(); },420); }},{l:"Start a pull",h:"Action",a:()=>{ close(); toast("Pulling from Jira and Confluence…"); }},{l:"Open the inbox",h:"Action",a:()=>drawer("Inbox",inboxHtml())},{l:"Keyboard shortcuts",h:"Help",a:()=>{ close(); showKeys(); }},
    ...TABS.map(x=>({l:"Go to "+x[1],h:"Page",a:()=>{ close(); go(x[0]); }})),...PEOPLE.map(p=>({l:p.name,h:"Person · "+p.role,a:()=>{ close(); QF.who=p.name; QF.feat="All features"; QF.pri="Any priority"; ST.qGroup="Who"; go("questions"); }})),
    ...FEATS.map(f=>({l:f.title,h:"Feature",a:()=>{ close(); go(f.title==="Promotions"?"promotions":"features"); }})),...allTasks().map(x=>({l:x.t,h:"Task",a:()=>openTask(x.k)})),...QALL.map((q,i)=>({l:q.q,h:"Question",a:()=>{ close(); QF.who="Anyone"; QF.feat="All features"; QF.pri="Any priority"; ST.qx.add(i); go("questions"); }}))];
  const draw=()=>{ const q=inp.value.trim().toLowerCase(), base=all(); items=(q?base.filter(x=>x.l.toLowerCase().includes(q)):base.slice(0,9)).slice(0,9); sel=Math.min(sel,Math.max(0,items.length-1));
    $("#cmdl").innerHTML=items.length?items.map((x,i)=>`<li class="${i===sel?"sel":""}" data-ci="${i}"><span class="t clamp">${esc(x.l)}</span><span class="hint">${esc(x.h)}</span></li>`).join(""):`<li><span class="t muted">Nothing found</span></li>`; };
  inp.oninput=()=>{ sel=0; draw(); }; inp.onkeydown=e=>{ if(e.key==="ArrowDown"){ e.preventDefault(); sel=Math.min(sel+1,items.length-1); draw(); } if(e.key==="ArrowUp"){ e.preventDefault(); sel=Math.max(sel-1,0); draw(); } if(e.key==="Enter"&&items[sel]){ items[sel].a(); } };
  $("#cmdl").onclick=e=>{ const li=e.target.closest("[data-ci]"); if(li) items[+li.dataset.ci].a(); }; draw(); inp.focus(); }
$("#b-find").onclick=search;
$("#b-inbox").onclick=()=>drawer("Inbox",inboxHtml());

/* zing: wallpaper drifts with the pointer */
const wallEl=$(".wall"); if(wallEl&&!REDUCED) document.addEventListener("mousemove",e=>{ wallEl.style.transform=`translate(${((e.clientX/innerWidth-.5)*-22).toFixed(1)}px,${((e.clientY/innerHeight-.5)*-22).toFixed(1)}px)`; });
addEventListener("resize",navFade); addEventListener("hashchange",()=>setTimeout(navFade,50)); navFade(); updInbox();
const afterEdit=()=>{ if(ST.backAll){ drawer("All tasks",allTab("Open"),"wide fix"); } else close(); };
document.addEventListener("click",e=>{ if(e.target.closest("[data-backall]")) drawer("All tasks",allTab("Open"),"wide fix"); });
