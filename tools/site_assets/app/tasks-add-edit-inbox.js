/* v6: add task, edit task, groups by drag between, inbox */
Object.assign(ST,{edits:{},newTasks:[],nid:0,inbox:[],extraGroups:new Set(),addf:{p:"medium",due:"",g:"Other tasks",ask:"",man:{},auto:{}}});
const iso=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const addDays=n=>{ const d=new Date(TODAYD); d.setDate(d.getDate()+n); return iso(d); };
const WD={sun:0,mon:1,tue:2,wed:3,thu:4,fri:5,sat:6}, PN={high:"High",medium:"Medium",low:"Low",none:"None"};
function parseTask(s){ const l=s.toLowerCase(), r={};
  if(/\b(urgent|asap|critical|high priority)\b|!high/.test(l)) r.p="high"; else if(/\b(low priority|someday|whenever)\b|!low/.test(l)) r.p="low";
  if(/\btoday\b/.test(l)) r.due=addDays(0); else if(/\btomorrow\b/.test(l)) r.due=addDays(1); else if(/\bnext week\b/.test(l)) r.due=addDays(7); else { const m=l.match(/\b(mon|tue|wed|thu|fri)[a-z]*\b/); if(m){ let n=(WD[m[1]]-TODAYD.getDay()+7)%7; if(n===0) n=7; r.due=addDays(n); } }
  if(/\b(ask|chase|ping|check with)\b/.test(l)){ const p=PEOPLE.find(p=>l.includes(p.name.split(" ")[0].toLowerCase())); if(p) r.ask=p.name; }
  const pd=planData(), gn=(pd.names||pd.gs.map(g=>g.name)).concat([...ST.extraGroups]).filter(n=>n!=="Other tasks"); const hit=gn.find(n=>l.includes(n.toLowerCase().split(" ")[0])); if(hit) r.g=hit; else if(/promotion/.test(l)&&gn.includes("Promotions")) r.g="Promotions";
  return r; }
function allTasks(){ let t=REAL.tasks.map((x,i)=>({...x,k:i}));
  if(ST.mode==="empty") t=[];
  if(ST.mode==="busy"){ const b=t.slice(); t=[]; for(let r=0;r<3;r++) b.forEach((x,i)=>t.push({...x,k:r*100+i,t:x.t+(r?" (second part of a very long task name that goes on and on to test two-line clamping)":"")})); t.forEach((x,i)=>{ if(i%5===0) x.g="A group with a very long name, to test how it wraps and clamps"; }); }
  return t.concat(ST.added,ST.newTasks).map(x=>ST.edits[x.k]?{...x,...ST.edits[x.k]}:x).filter(x=>!x.del&&(ALLT_RAW||!x.snz)); }
var rowBody=(x,o)=>{ const over=x.due&&x.due<REAL.today; return `<button class="ck ${x.p==="high"?"hi":""}" data-ck="${x.k}" aria-label="Mark done" aria-pressed="false">${CK}</button><span class="t clamp" data-edit="${x.k}" tabindex="0" role="button" title="Edit this task">${o&&o.chip?gchip(x):""}${esc(x.t)}</span><span class="rhs">${over?stk(daysLate(x),o&&o.chip):`<span class="when">${rel(x.due)}</span>`}<button class="snz" data-snooze="${x.k}" title="Move to tomorrow" aria-label="Move to tomorrow">Tomorrow${ARROW}</button></span>`; };
const groupNames=()=>{ const pd=planData(); return [...new Set(["Other tasks",...(pd.names||pd.gs.map(g=>g.name)),...ST.extraGroups])].filter(n=>n!=="__flat"); };

/* quick add */
const PLUS='<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>';
function addOptsHtml(){ const f=ST.addf, a=f.auto||{};
  return `<button class="pick ${a.p||f.man.p?"set":""}" data-ao="p">Priority · ${PN[f.p]}</button><button class="pick ${a.due||f.man.due?"set":""}" data-ao="due">Due · ${f.due?rel(f.due):"No date"}</button><button class="pick ${a.g||f.man.g?"set":""}" data-ao="g">Group · ${esc(f.g)}</button>${f.ask?`<span class="chip hot">Ask ${esc(f.ask)}</span>`:""}`; }
const addHtml=()=>`<div class="addwrap" id="addwrap"><div class="addt"><span class="plus">${PLUS}</span><input id="addin" autocomplete="off" aria-label="Add a task" placeholder="Add a task. Try: Ask Sam about the release fix tomorrow"><kbd class="kn">N</kbd></div><div class="addopts" id="addopts">${addOptsHtml()}</div></div>`;

/* task editor */
const ESTS=[["15","15m"],["30","30m"],["60","1h"],["120","2h"],["240","½ day"],["480","1 day"],["0","None"]];
function taskForm(x){ const gs=groupNames(), pr=["high","medium","low"];
  return `<div class="tf" data-k="${x.k}"><textarea class="field big" id="tf-t" rows="1" data-grow aria-label="Task name">${esc(x.t)}</textarea>
  <div class="cap muted tfl">Priority</div><div class="pills" id="tf-p">${pr.map(p=>`<button class="chip sel ${x.p===p?"on":""}" data-tfp="${p}"><i class="pd ${p}"></i>${PN[p]}</button>`).join("")}</div>
  <div class="cap muted tfl">Due</div><div class="row2">${dateHtml("tf-due",x.due,"No date")}<div class="pills">${[["0","Today"],["1","Tomorrow"],["7","Next week"],["x","None"]].map(([v,l])=>`<button class="chip sel" data-tfd="${v}">${l}</button>`).join("")}</div></div>
  <div class="cap muted tfl">Group</div>${comboHtml("tf-g",x.g,"groups","Pick a group or type a new one")}
  <div class="cap muted tfl">Details</div><textarea class="field" id="tf-n" data-grow aria-label="Details" placeholder="Context, links, what done looks like">${esc(x.n||"")}</textarea>
  <button class="u-mt10 link" data-tfmore>More options</button>
  <div class="acc" id="tf-more"><div class="in"><div class="u-pt12 row2"><div><div class="cap muted tfl">Time</div><div class="pills" id="tf-e">${ESTS.map(([v,l])=>`<button class="chip sel ${String(x.est||0)===v?"on":""}" data-tfe="${v}">${l}</button>`).join("")}</div></div></div>
   <div class="u-mt12 row2"><div class="u-flex-1"><div class="cap muted tfl">Ask</div>${comboHtml("tf-ask",x.ask||"","people","Who to reach out to")}</div><div class="u-flex-1"><div class="cap muted tfl">Remind on</div>${dateHtml("tf-rem",x.rem,"No reminder")}</div></div>
   <p class="u-mt12 hint">${esc(x.src||"Added by you")}</p></div></div>
  <div class="u-mt20 acts"><button class="btn2" data-tfsave>Save</button><button class="pick nochev" data-tfdone>Mark done</button><button class="u-mlauto link" data-tfdel>Delete</button></div></div>`; }

/* inbox */
const inboxCount=()=>LV.inboxN+ST.inbox.length+Object.keys(ST.ans).length;
function inboxHtml(){ const rows=[...(LV.inboxN?[{k:"File",t:LV.inboxN+" file"+(LV.inboxN===1?"":"s")+" waiting",s:"Read on the next pull"}]:[]),...ST.inbox.map((x,i)=>({k:"Pasted",t:x.t,s:"Pasted text",rm:"p"+i})),...Object.keys(ST.ans).map(i=>({k:"Answer",t:QALL[i].q,s:ST.ans[i],rm:"a"+i}))];
  return `<p class="u-mb6 muted">Mantis reads these on the next pull, then digests them into the cards.</p><ul class="rows">${rows.map(r=>`<li><span class="chip">${r.k}</span><span class="t"><span class="clamp">${esc(r.t)}</span><small class="clamp">${esc(r.s)}</small></span>${r.rm?`<button class="ibtn" data-ibx="${r.rm}" aria-label="Remove">${X}</button>`:""}</li>`).join("")}</ul><div class="acts"><button class="btn2" data-pull>Start a pull</button></div>`; }
var sbarHtml=()=>{ const n=ansCount(); return n?`<div class="sbar show" id="sbar"><span>${n} ${n===1?"answer":"answers"} in the inbox.</span><button class="link" data-inbox>View inbox</button><button class="link" data-pull>Start a pull</button></div>`:`<div class="sbar" id="sbar"></div>`; };
