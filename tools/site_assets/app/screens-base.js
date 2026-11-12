/* Mantis redesign mock v4. Real numbers from data.js; the rest is illustrative where stated in notes.md. */
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ini=n=>n.split(" ").slice(0,2).map(x=>x[0]).join("").toUpperCase();
const CK='<svg viewBox="0 0 24 24"><path d="m6 12.5 4 4 8-9"/></svg>';
const CHEV='<svg class="chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>';
const X='<svg viewBox="0 0 24 24"><path d="M7 7l10 10M17 7 7 17"/></svg>';
const MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], TODAYD=new Date(REAL.today+"T12:00:00");
const fmt=d=>{ if(!d) return ""; const [y,m,dd]=d.split("-"); return +dd+" "+MONTHS[+m-1]; };
function rel(due){ if(!due) return ""; const dt=new Date(due+"T12:00:00"), n=Math.round((dt-TODAYD)/864e5); if(n<0) return `${-n} ${-n===1?"day":"days"} late`; if(n===0) return "Today"; if(n===1) return "Tomorrow"; if(n<7) return ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][dt.getDay()]; return fmt(due); }

/* ---------- data ---------- */
const TABS=UI.tabs();   // from site_config/layout.json
const DATES={Mon:"9 Nov",Tue:"10 Nov",Wed:"11 Nov",Thu:"12 Nov",Fri:"13 Nov"}, WEEK=["Mon","Tue","Wed","Thu","Fri"];
const MEET=[];
const TOPICS=[];
const WANT={};
const FEATS=[], STAGES=["Discovery","Refinement","Build"];
const QALL=[];
const NEXTM={};
const QOPT={who:["Anyone","You"],feat:["All features"],pri:["Any priority","High","Medium","None"]};   // the people and features are filled from the live data
const FILT=[];
const RECENT=[];
const AREAS=[];
const PEOPLE=[];

/* ---------- state ---------- */
const ST={done:new Set(),added:[],gone:new Set(),carryKept:false,open:0,mode:"normal",wkSel:3,qGroup:"Who",rc:"Pages",gi:0,raised:new Set(),pulled:false};
const QF={who:"Anyone",feat:"All features",pri:"Any priority"};
let prevIdx=0;

/* ---------- plan ---------- */
const taskByK=k=>allTasks().find(x=>x.k===k);
function ringG(gs){ const n=gs.reduce((a,g)=>a+g.items.length,0);
  if(!n) return `<svg viewBox="0 0 210 210">${Array.from({length:36},(_,i)=>`<g transform="rotate(${i*10} 105 105)"><rect x="102.4" y="5" width="5.2" height="22" rx="2.6" fill="var(--fill-2)"/></g>`).join("")}</svg>`;
  const gap=gs.length>1?9:0, step=(360-gap*gs.length)/n; let a=gap/2,out="",k=0;
  gs.forEach((g,gi)=>{ g.items.forEach(x=>{ const col=x.p==="high"?"var(--accent)":(x.p==="medium"?"var(--ink)":"var(--fill-2)"); out+=`<g transform="rotate(${a.toFixed(2)} 105 105)"><rect class="tick g${gi}${ST.done.has(x.k)?" done":""}" data-k="${x.k}" data-a="${a.toFixed(2)}" x="102.4" y="5" width="5.2" height="22" rx="2.6" fill="${col}" style="animation-delay:${k*22}ms"/></g>`; a+=step; k++; }); a+=gap; });
  return `<svg viewBox="0 0 210 210" role="img" aria-label="${n} tasks in ${gs.length} groups">${out}</svg>`; }
function decideHtml(){ const sg=EXTRA.sugg.map((s,i)=>({...s,i})).filter(s=>!ST.gone.has("s"+s.i)), carry=!ST.carryKept&&ST.mode!=="empty"?EXTRA.carried:0;
  if(!sg.length&&!carry) return "";
  const bits=[sg.length?sg.length+" suggested":"",carry?carry+" carried over":""].filter(Boolean).join(" · ");
  return `<div class="decide"><button class="gh" aria-expanded="false"><span class="pulse"></span><span class="nm">Needs a decision</span><span class="cnt">${bits}</span>${CHEV}</button>
  <div class="acc"><div class="in"><ul class="rows">${sg.map(s=>`<li class="sg"><span class="t"><b>${esc(s.t)}</b><small>${esc(s.why)}</small>${s.say?`<button class="link" data-copy="${esc(s.say)}">Copy the message to send</button>`:""}</span><button class="ibtn ok" data-sa="${s.i}" aria-label="Add to my plan">${CK}</button><button class="ibtn" data-sd="${s.i}" aria-label="Dismiss">${X}</button></li>`).join("")}
  ${carry?`<li class="cr"><span class="t">${carry} tasks from yesterday are in today's plan<small>Keep them all, or step through them one by one</small></span><button class="pick nochev" data-keep>Keep all</button><button class="pick nochev" data-review>Review</button></li>`:""}</ul></div></div></div>`; }

/* ---------- today widgets ---------- */
function dayCounts(i){ const date=EXTRA.week[i].d; return {m:MEET.filter(x=>x.d===WEEK[i]).length,t:REAL.tasks.filter(x=>x.due===date).length}; }
function dayList(i){ const date=EXTRA.week[i].d, ms=MEET.filter(m=>m.d===WEEK[i]).map(m=>[m.t,m.n,"Meeting"]), ts=REAL.tasks.filter(x=>x.due===date).map(x=>["Due",x.t,"Task"]), all=[...ms,...ts];
  return all.length?`<ul class="rows">${all.map(r=>`<li><span class="u-w-46 when">${r[0]}</span><span class="t clamp">${esc(r[1])}</span></li>`).join("")}</ul>`:`<p class="zero">Nothing scheduled. A good day for focus work.</p>`; }
const S={};

/* ---------- meetings ---------- */

/* ---------- features ---------- */

/* ---------- questions ---------- */
const qFilter=()=>QALL.filter(q=>(QF.who==="Anyone"||q.who===QF.who)&&(QF.feat==="All features"||q.feat===QF.feat)&&(QF.pri==="Any priority"||q.pri===QF.pri));

/* ---------- sources ---------- */
function composeHtml(){ if(ST.pulled) return `<p class="u-p-8-0-14">In the inbox. Read on the next pull.</p><button class="pick nochev" data-again>Add another</button>`;
  return `<div class="card-h"><h2>Add notes or a file</h2><span class="hint">Minutes, a message, a document</span></div><input class="field" id="ctitle" aria-label="Name" placeholder="Name it, for example Weekly sync, 12 Nov"><textarea class="u-mt8 u-minh-240 field" id="ctext" aria-label="Text" placeholder="Paste or type here"></textarea>
  <div class="drop" id="drop"><span>Or drop a file here</span><button class="link" type="button" data-act="inbox-choose">Choose a file</button><input type="file" id="cfile" multiple hidden accept=".md,.txt,.vtt,.srt,.docx,.pdf,.html,.htm,.xlsx,.pptx"></div><div class="u-mt0 acts"><button class="btn2" data-add>Add to inbox</button></div>`; }

/* ---------- growth ---------- */
