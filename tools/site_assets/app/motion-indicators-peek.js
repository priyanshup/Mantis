/* v13: elastic indicators, rows that glide, sticky bars, reveal on scroll, peek cards, drag to dismiss, shortcuts sheet, back to top */
/* 1. indicators stretch toward the new place, then settle */
function elastic(el,left,width){ const pl=el.dataset.l===undefined?null:+el.dataset.l, pw=+el.dataset.w; el.dataset.l=left; el.dataset.w=width;
  el.style.width=width+"px"; el.style.transform=`translateX(${left}px)`;
  if(pl===null||REDUCED||(pl===left&&pw===width)) return;
  const min=Math.min(pl,left), span=Math.max(pl+pw,left+width)-min; el.getAnimations().forEach(a=>a.cancel());
  el.animate([{width:pw+"px",transform:`translateX(${pl}px)`},{width:span+"px",transform:`translateX(${min}px)`,offset:.4},{width:width+"px",transform:`translateX(${left}px)`}],{duration:560,easing:"cubic-bezier(.32,.72,0,1)"}); }
function moveInd(){ const b=nav.querySelector('[aria-current="page"]'); let ind=nav.querySelector(".ind"); if(!ind){ ind=document.createElement("i"); ind.className="ind"; nav.appendChild(ind); } if(b) elastic(ind,b.offsetLeft+14,b.offsetWidth-28); }
function placeSeg(seg){ const b=seg.querySelector(':scope > button[aria-pressed="true"]'); let i=seg.querySelector(":scope > .segi"); if(!b){ if(i) i.style.opacity=0; return; }
  if(!i){ i=document.createElement("i"); i.className="segi"; seg.appendChild(i); seg.classList.add("has-ind"); } const s=seg.getBoundingClientRect(), r=b.getBoundingClientRect(); i.style.opacity=1; elastic(i,+(r.left-s.left+seg.scrollLeft).toFixed(1),+r.width.toFixed(1)); }

/* 2. rows glide to their new places whenever the plan reorders */
const _rr3=rerenderPlan; rerenderPlan=function(o){ const first={}, gfirst={}; $$("#plan .trow[data-k]").forEach(li=>{ const r=li.getBoundingClientRect(); if(r.height>0) first[li.dataset.k]=r; }); $$("#plan .grp").forEach(g=>{ const r=g.getBoundingClientRect(); if(r.height>0) gfirst[g.dataset.name]=r.top; }); _rr3(o); if(REDUCED) return;
  const gd={}; $$("#plan .grp").forEach(g=>{ const f=gfirst[g.dataset.name]; if(f===undefined) return; const dy=f-g.getBoundingClientRect().top; if(Math.abs(dy)>=1){ gd[g.dataset.name]=dy; g.animate([{transform:`translateY(${dy}px)`},{transform:"none"}],{duration:520,easing:"cubic-bezier(.32,.72,0,1)"}); } });
  $$("#plan .trow[data-k]").forEach(li=>{ const f=first[li.dataset.k]; if(!f) return; const l=li.getBoundingClientRect(); if(l.height<=0) return; const g=li.closest(".grp"), shift=g&&gd[g.dataset.name]?gd[g.dataset.name]:0, dx=f.left-l.left, dy=(f.top-l.top)-shift;
    if(Math.abs(dx)<1&&Math.abs(dy)<1) return; li.animate([{transform:`translate(${dx}px,${dy}px)`},{transform:"none"}],{duration:440,easing:"cubic-bezier(.32,.72,0,1)"}); }); };
const _rc3=refreshCounts; refreshCounts=function(){ _rc3(); const P=planData(); if(P.n&&P.n===ST.done.size&&!REDUCED) $$("#ring .tick").forEach((t,i)=>{ t.style.animationDelay=(i*16)+"ms"; t.classList.remove("wave"); void t.offsetWidth; t.classList.add("wave"); }); };

/* 3. sticky offsets follow the header as it tightens */
const setTop=()=>document.documentElement.style.setProperty("--top","64px");
addEventListener("scroll",()=>{ setTop(); document.documentElement.style.setProperty("--sy",Math.min(scrollY*.06,110)+"px"); updTop(); },{passive:true}); setTop();

/* 4. below-the-fold blocks arrive as they come into view */
const io=new IntersectionObserver(es=>{ let n=0; es.forEach(e=>{ if(e.isIntersecting){ e.target.style.transitionDelay=(n++*70)+"ms"; e.target.classList.add("in"); io.unobserve(e.target); } }); },{threshold:.08,rootMargin:"0px 0px -6% 0px"});
function setupReveal(){ if(REDUCED) return; $$("main .rise").forEach(el=>{ const r=el.getBoundingClientRect(); if(r.top>innerHeight*.92){ el.classList.remove("rise"); el.classList.add("reveal"); io.observe(el); } }); }
new MutationObserver(()=>requestAnimationFrame(setupReveal)).observe(main,{childList:true});

/* 5. peek cards: hover a meeting for its purpose and people */
let peekT, peekFor=null; const peekEl=()=>{ let p=$("#peek"); if(!p){ p=document.createElement("div"); p.id="peek"; p.className="peek"; p.setAttribute("role","tooltip"); document.body.appendChild(p); } return p; };
const hidePeek=()=>{ clearTimeout(peekT); peekFor=null; const p=$("#peek"); if(p) p.classList.remove("show"); };
function showPeek(row,i){ const m=MEET[i], p=peekEl(), n=m.ag.length+m.more, names=m.w.slice(0,5).join(", ")+(m.w.length>5?` and ${m.w.length-5} more`:"");
  p.innerHTML=`<b>${esc(m.n)}</b><span class="mono">${m.d} ${DATES[m.d]}, ${m.t}</span><p>${esc(m.why)}</p><p class="mono">${esc(names)}</p><p class="pk">${n?`${n} to raise. Brief ready. Click to open.`:"Nothing to raise. Click to open."}</p>`;
  const r=row.getBoundingClientRect(), w=300; p.style.width=w+"px"; let left=r.left-w-12; if(left<8) left=Math.min(r.right+12,innerWidth-w-8); p.style.left=left+"px"; p.style.top=Math.max(72,Math.min(r.top-8,innerHeight-p.offsetHeight-12))+"px"; p.classList.add("show"); }
UI.hoverIntent("[data-gomeet],.mrow[data-mi]",{delay:220,show:r=>{ const i=+(r.dataset.gomeet!==undefined?r.dataset.gomeet:r.dataset.mi); if(MEET[i]){ peekFor=i; showPeek(r,i); } },hide:()=>hidePeek()});
document.addEventListener("click",hidePeek); addEventListener("scroll",hidePeek,{passive:true});

/* 6. a drawer can be pulled away, with some resistance */
let dr=null;
document.addEventListener("pointerdown",e=>{ const h=e.target.closest&&e.target.closest(".drawer .hd"); if(!h||e.target.closest("button")) return; dr={el:h.closest(".drawer"),x:e.clientX,dx:0}; dr.el.style.transition="none"; h.setPointerCapture&&h.setPointerCapture(e.pointerId); });
document.addEventListener("pointermove",e=>{ if(!dr) return; const raw=Math.max(0,e.clientX-dr.x); dr.dx=raw<140?raw:140+(raw-140)*.35; dr.el.style.transform=`translateX(${dr.dx}px)`; });
document.addEventListener("pointerup",()=>{ if(!dr) return; const el=dr.el, far=dr.dx>120; dr=null; el.style.transition="transform .35s cubic-bezier(.32,.72,0,1),opacity .3s"; if(far){ el.style.transform="translateX(110%)"; el.style.opacity="0"; setTimeout(close,300); } else el.style.transform=""; });

/* 7. a primary button leans toward the pointer */
document.addEventListener("mousemove",e=>{ if(REDUCED) return; const b=e.target.closest&&e.target.closest(".btn"); $$(".btn.mag").forEach(x=>{ if(x!==b){ x.style.setProperty("--tx","0px"); x.style.setProperty("--ty","0px"); x.classList.remove("mag"); } }); if(!b) return; const r=b.getBoundingClientRect(); b.classList.add("mag"); b.style.setProperty("--tx",((e.clientX-r.left-r.width/2)*.12).toFixed(1)+"px"); b.style.setProperty("--ty",((e.clientY-r.top-r.height/2)*.2).toFixed(1)+"px"); });

/* 8. back to top, with a ring that shows how far down you are */
(function(){ const b=document.createElement("button"); b.id="totop"; b.className="totop"; b.setAttribute("aria-label","Back to top"); b.innerHTML='<svg class="tring" viewBox="0 0 44 44"><circle cx="22" cy="22" r="20"/><circle id="tprog" cx="22" cy="22" r="20"/></svg><svg class="tarr" viewBox="0 0 24 24"><path d="M12 19V6M6 12l6-6 6 6"/></svg>'; document.body.appendChild(b); b.onclick=()=>scrollTo({top:0,behavior:REDUCED?"auto":"smooth"}); })();
function updTop(){ const b=$("#totop"); if(!b) return; const max=document.documentElement.scrollHeight-innerHeight, show=max>innerHeight*.5&&scrollY>480; b.classList.toggle("show",show); const p=max>0?Math.min(1,scrollY/max):0, c=$("#tprog"); if(c) c.style.strokeDashoffset=String(125.7*(1-p)); }
addEventListener("resize",updTop); new MutationObserver(()=>requestAnimationFrame(updTop)).observe(main,{childList:true}); updTop();

/* 9. the shortcuts sheet, and G then a letter to go somewhere */
const KEYS=[["Go anywhere",[["Search and commands",["Ctrl","K"]],["Same, from anywhere",["/"]],["Today, Meetings, Features",["G","T"],["G","M"],["G","F"]],["Questions, Sources, Growth",["G","Q"],["G","S"],["G","R"]]]],
  ["Tasks",[["Add a task",["N"]],["Edit a task",["Enter"],"on its title"],["Rank a task up or down",["Alt","↑"],["Alt","↓"],"on its checkbox"],["Rank a group up or down",["Alt","↑"],["Alt","↓"],"on its header"],["Mark done",["Space"],"on its checkbox"],["Drag a task to another group",["Drag"]]]],
  ["Menus and fields",[["Move through a list",["↑"],["↓"]],["Choose",["Enter"]],["Close anything",["Esc"]]]],
  ["This sheet",[["Show or hide the shortcuts",["?"]]]]];
function keyRow(r){ const label=r[0], rest=r.slice(1), note=rest.find(x=>typeof x==="string"), combos=rest.filter(x=>Array.isArray(x)); return `<li><span class="kl">${esc(label)}${note?`<small>${esc(note)}</small>`:""}</span><span class="kc">${combos.map(c=>`<span class="kcombo">${c.map(k=>`<kbd>${esc(k)}</kbd>`).join("")}</span>`).join("")}</span></li>`; }
function showKeys(){ if($(".keys")){ close(); return; } layer.innerHTML=`<div class="scrim"></div><div class="sheet keys" role="dialog" aria-label="Keyboard shortcuts"><div class="hd2"><h2>Keyboard shortcuts</h2><button class="ic" aria-label="Close" data-act="close-layer"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div><div class="kgrid">${KEYS.map(([h,rows])=>`<section><div class="cap muted">${h}</div><ul class="rows">${rows.map(keyRow).join("")}</ul></section>`).join("")}</div></div>`; layer.querySelector(".scrim").onclick=close; layer.querySelector(".hd2 .ic").onclick=close; }
let chord=0; const GO={t:"today",m:"meetings",f:"features",q:"questions",s:"sources",r:"growth"};
document.addEventListener("keydown",e=>{ const typing=/INPUT|TEXTAREA|SELECT/.test((document.activeElement||{}).tagName||"")||(document.activeElement&&document.activeElement.isContentEditable); if(typing||e.ctrlKey||e.metaKey||e.altKey) return; const k=e.key;
  if(k==="?"){ e.preventDefault(); showKeys(); return; }
  if(k==="/"){ e.preventDefault(); search(); return; }
  if(chord&&Date.now()-chord<1300&&GO[k.toLowerCase()]){ e.preventDefault(); chord=0; hideChord(); close(); go(GO[k.toLowerCase()]); return; }
  if(k.toLowerCase()==="g"&&!layer.innerHTML){ chord=Date.now(); const c=$("#chord")||Object.assign(document.body.appendChild(document.createElement("div")),{id:"chord",className:"chord"}); c.innerHTML="Go to <kbd>T</kbd> Today <kbd>M</kbd> Meetings <kbd>F</kbd> Features <kbd>Q</kbd> Questions <kbd>S</kbd> Sources <kbd>R</kbd> Growth"; c.classList.add("show"); setTimeout(hideChord,1300); } });
const hideChord=()=>{ const c=$("#chord"); if(c) c.classList.remove("show"); };

addEventListener("resize",()=>{ moveInd(); initSegs(); });
