/* v12 craft and delight. Everything here is transform or opacity, under half a second, and off for reduced motion. */
let segRaf, idleT, mainT;
/* 1. one sliding underline for every tab group */
const initSegs=()=>$$(".seg").forEach(placeSeg);
/* 2. a fresh screen: rows arrive one after another */
new MutationObserver(()=>{ main.classList.add("fresh"); clearTimeout(mainT); mainT=setTimeout(()=>main.classList.remove("fresh"),900); }).observe(main,{childList:true});
/* 3. things that fly where they go */
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest("[data-add],[data-qsave]"); if(b) ST.lastRect=b.getBoundingClientRect(); },true);
function fly(rect,target){ if(REDUCED||!rect||!target) return; const t=target.getBoundingClientRect(), x0=rect.left+rect.width/2, y0=rect.top+rect.height/2, dx=t.left+t.width/2-x0, dy=t.top+t.height/2-y0, d=document.createElement("div"); d.className="fly"; d.style.left=x0+"px"; d.style.top=y0+"px"; document.body.appendChild(d);
  d.animate([{transform:"translate(-50%,-50%) scale(1)",opacity:1},{transform:`translate(calc(-50% + ${dx*.45}px),calc(-50% + ${dy*.45-70}px)) scale(.9)`,opacity:1,offset:.5},{transform:`translate(calc(-50% + ${dx}px),calc(-50% + ${dy}px)) scale(.25)`,opacity:.3}],{duration:640,easing:"cubic-bezier(.32,.72,0,1)"}).onfinish=()=>{ d.remove(); const bd=$("#ibadge"); if(bd){ bd.classList.remove("bump"); void bd.offsetWidth; bd.classList.add("bump"); } }; }
/* 4. tasks: snooze, bring back, tick and row linked */
document.addEventListener("click",e=>{ const t=e.target; let b;
  if(b=t.closest("[data-snooze]")){ const k=+b.dataset.snooze, li=b.closest("li"), prev=ST.edits[k]?{...ST.edits[k]}:null; ST.edits[k]=Object.assign(ST.edits[k]||{},{due:addDays(1),snz:true}); collapse(li,()=>rerenderPlan()); toast("Moved to tomorrow",()=>{ if(prev) ST.edits[k]=prev; else delete ST.edits[k]; rerenderPlan(); }); return; }
  if(b=t.closest("[data-unsnz]")){ const k=+b.dataset.unsnz; ST.edits[k]=Object.assign(ST.edits[k]||{},{snz:false}); rerenderPlan(); toast("Back in today's plan"); return; }
  if(b=t.closest("[data-copy]")){ if(b.classList.contains("copied")) return; const old=b.textContent; if(b.children.length) return; b.classList.add("copied"); b.textContent="Copied"; setTimeout(()=>{ b.textContent=old; b.classList.remove("copied"); },1300); }
  if(b=t.closest("[data-qsave]")){ if(ST.ans[+b.dataset.qsave]) fly(ST.lastRect,$("#b-inbox")); }
  if(b=t.closest("[data-add]")){ if(ST.pulled) fly(ST.lastRect,$("#b-inbox")); }
  if(b=t.closest("[data-act=growth-add-selected],[data-act=growth-add]")){ setTimeout(()=>$$("#gtabs .m").forEach(m=>{ m.classList.remove("bump"); void m.offsetWidth; m.classList.add("bump"); }),b.dataset.act==="growth-add"?30:580); }
  if(b=t.closest("[data-raise]")){ setTimeout(()=>{ const all=$$("[data-raise]"), ul=all[0]&&all[0].closest("ul"); if(!ul) return; const old=ul.parentElement.querySelector(".allr"); const done=all.every(x=>x.getAttribute("aria-pressed")==="true"); if(done&&!old) ul.insertAdjacentHTML("afterend",'<p class="allr">That is all of them.</p>'); if(!done&&old) old.remove(); },20); }
  if(b=t.closest("[data-pull]")){ if(ST.pulling) return; ST.pulling=true; const btns=$$("[data-pull]"), old=btns.map(x=>x.textContent); btns.forEach(x=>{ if(!x.children.length) x.textContent="Pulling…"; x.classList.add("busy"); }); $(".top").classList.add("run");
    setTimeout(()=>{ ST.pulling=false; $(".top").classList.remove("run"); btns.forEach((x,i)=>{ if(x.isConnected){ x.textContent=old[i]; x.classList.remove("busy"); } }); toast("Pull done: 18 new, 14 changed. 1 file read."); const c=$("#changes"); if(c){ c.classList.remove("pulse-in"); void c.offsetWidth; c.classList.add("pulse-in"); } },2600); } });
document.addEventListener("mouseover",e=>{ const li=e.target.closest&&e.target.closest("#plan .trow[data-k]"); $$(".tick.hot").forEach(x=>x.classList.remove("hot")); if(li){ const t=$(`#ring .tick[data-k="${li.dataset.k}"]`); if(t) t.classList.add("hot"); } });
/* 5. the dark card: a light that follows the pointer, and a real countdown */
document.addEventListener("mousemove",e=>{ const c=e.target.closest&&e.target.closest(".card.night"); if(c){ const r=c.getBoundingClientRect(); c.style.setProperty("--mx",(e.clientX-r.left)+"px"); c.style.setProperty("--my",(e.clientY-r.top)+"px"); } });
function updCd(){ const el=$("#cd"); if(!el) return; const t=new Date(), n=new Date(t); n.setHours(9,30,0,0); if(n<=t) n.setDate(n.getDate()+1); const m=Math.round((n-t)/60000), h=Math.floor(m/60); el.textContent=`Tomorrow 09:30 · in ${h?h+" h ":""}${m%60} min`; }
setInterval(()=>updCd(),30000);
/* 6. a title that travels from the list to its page */
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest(".frow[data-f]"); if(b){ ST.lastF=b.dataset.f; const n=b.querySelector(".fn"); if(n) n.style.viewTransitionName="ftitle"; } },true);
/* 7. small things */
{ let s=false; addEventListener("scroll",()=>{ const n=s?scrollY>6:scrollY>28; if(n!==s){ s=n; $(".top").classList.toggle("scrolled",s); } },{passive:true}); }
const brandImg=()=>$(".brand img"); const twitch=()=>{ const i=brandImg(); if(!i||REDUCED) return; i.classList.remove("twitch"); void i.offsetWidth; i.classList.add("twitch"); };
const idleReset=()=>{ clearTimeout(idleT); idleT=setTimeout(function again(){ twitch(); idleT=setTimeout(again,45000); },45000); };
["mousemove","keydown","click"].forEach(ev=>document.addEventListener(ev,idleReset,{passive:true})); idleReset();
