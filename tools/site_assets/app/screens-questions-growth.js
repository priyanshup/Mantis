/* v5 additions and overrides: ranking, stickers, message preview, answering, growth, feature reader */
Object.assign(ST,{sort:"mantis",manual:null,openName:undefined,ans:{},qx:new Set(),gv:"Proposed",gsel:new Set(),gdec:{},gadd:[],ft:"Overview",st:0,pg:0,drag:null,gform:{kind:"Win",areas:new Set(),when:"This quarter"}});
const SORTN={mantis:"Mantis order",due:"Due date",priority:"Priority",mine:"My order"};
const CLOCK='<svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 3h6"/></svg>';
const GRIP='<svg viewBox="0 0 24 24"><circle cx="9" cy="7" r="1.4"/><circle cx="15" cy="7" r="1.4"/><circle cx="9" cy="12" r="1.4"/><circle cx="15" cy="12" r="1.4"/><circle cx="9" cy="17" r="1.4"/><circle cx="15" cy="17" r="1.4"/></svg>';
const daysLate=x=>Math.round((TODAYD-new Date(x.due+"T12:00:00"))/864e5);
const stk=(n,short)=>`<span class="stk ${n>=5?"hot":""}${short?" short":""}" title="${n} ${n===1?"day":"days"} past its due date">${CLOCK}${short?n+"d late":n+" "+(n===1?"day":"days")+" late"}</span>`;
const stkG=c=>`<span class="stk sm" title="${c} overdue">${CLOCK}${c} late</span>`;
var trow=x=>`<li class="trow" data-k="${x.k}" data-over="${x.due&&x.due<REAL.today?1:0}">${rowBody(x)}</li>`;
const trowD=x=>`<li class="trow drag" draggable="true" data-k="${x.k}" data-over="${x.due&&x.due<REAL.today?1:0}">${rowBody(x,{chip:ST.flat})}<span class="grip" title="Drag to rank. Alt and arrow keys also work." aria-hidden="true">${GRIP}</span></li>`;


/* today */
const chaseText=n=>`Hi ${n.split(" ")[0]},\n\nA quick check on what I'm waiting for:\n${WANT[n].items.map(x=>"• "+x).join("\n")}\n\nThanks,`;

/* questions: expand for context, answer, store in the inbox */
const QCTX=[];
function qList(){ const f=QALL.map((q,i)=>[q,i]).filter(([q])=>(QF.who==="Anyone"||q.who===QF.who)&&(QF.feat==="All features"||q.feat===QF.feat)&&(QF.pri==="Any priority"||q.pri===QF.pri));
  if(!f.length) return `<p class="zero">No question matches. <button class="link" data-clearq>Clear the filters</button></p>`;
  const key={Who:"who",Feature:"feat",Meeting:"meet"}[ST.qGroup], groups={}; f.forEach(([q,i])=>(groups[q[key]]=groups[q[key]]||[]).push([q,i]));
  const qr=([q,i])=>{ const a=ST.ans[i], open=ST.qx.has(i); return `<li class="qr ${open?"open":""} ${a?"answered":""}"><button class="qrh" data-qx="${i}" aria-expanded="${open}"><span class="dot ${q.pri==="High"?"hi":""}"></span><span class="t clamp">${esc(q.q)}</span>${a?'<span class="chip ok">In inbox</span>':`<span class="when">${esc(ST.qGroup==="Who"?q.meet:q.who)}</span>`}${CHEV}</button>
    <div class="acc"><div class="in"><div class="qbody"><p class="ctx">${esc(QCTX[i][0])}</p><div class="pills">${QCTX[i][1].map(s=>`<span class="chip">${esc(s)}</span>`).join("")}<span class="chip">${esc(q.who)} might know</span></div>
    <label class="lbl" for="qa${i}">Your answer</label><textarea class="field" id="qa${i}" placeholder="Type what you know. It is saved to the inbox and read on the next pull.">${esc(a||"")}</textarea><div class="acts"><button class="btn2" data-qsave="${i}">${a?"Update answer":"Save to inbox"}</button><button class="link" data-qx="${i}">Close</button></div></div></div></div></li>`; };
  return Object.entries(groups).sort((a,b)=>b[1].length-a[1].length).map(([name,list])=>{ const who=ST.qGroup==="Who";
    return `<div class="qg"><div class="qgh"><span class="t">${esc(name)}<small>${list.length} ${list.length===1?"question":"questions"}${who?" · "+(NEXTM[name]||"No meeting this week"):""}</small></span>${who?`<button class="btnl" data-qchase="${esc(name)}">Copy message</button>`:""}</div><ul class="rows">${list.map(qr).join("")}</ul></div>`; }).join(""); }
const ansCount=()=>Object.keys(ST.ans).length;

/* growth */
const KINDS=["Win","Step","Learning"], WHENS=["This quarter","Next quarter","2027"];
const gOf=x=>x.past?"Wins to record":(x.kind==="learning"?"Things to learn":"Steps to take");
const heldTill=x=>!!x.hold&&x.hold>REAL.today;
function gLists(){ const items=GROWD.map((x,i)=>({...x,i})), proposed=items.filter(x=>x.state==="proposed"), later=proposed.filter(heldTill);
  return {prop:proposed.filter(x=>!heldTill(x)), later, declined:DECLINED, hidden:later.length+DECLINED.length, prog:items.filter(x=>x.state==="open"), done:items.filter(x=>x.state==="done")}; }
const X_ICON='<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
function gRow(x,sel){ return `<li class="gr ${ST.qx.has("g"+x.i)?"open":""}"><button class="ck" data-gs="${x.i}" aria-pressed="${sel}" aria-label="Select">${CK}</button><button class="grh" data-gx="${x.i}" aria-expanded="${ST.qx.has("g"+x.i)}"><span class="t clamp">${esc(x.title)}</span>${CHEV}</button><button class="gdis" data-act="growth-dismiss" data-id="${esc(x.id)}" aria-label="Dismiss: Mantis will not propose it again" title="Dismiss. Mantis will not propose it again.">${X_ICON}</button><div class="acc grw"><div class="in"><p class="ctx">${esc(x.why||"No note recorded.")}</p><div class="pills">${x.areas.map(a=>`<span class="chip">${a}</span>`).join("")}</div></div></div></li>`; }
const gGroups=L=>{ const groups={}; L.prop.forEach(x=>(groups[gOf(x)]=groups[gOf(x)]||[]).push(x)); return ["Wins to record","Steps to take","Things to learn"].filter(k=>groups[k]).map(k=>[k,groups[k]]); };
function gHidden(L){ const hd=(window.__LIVE.growth||{}).hold_days||14, dd=(window.__LIVE.growth||{}).declined_days||30;
  const note=`<p class="gnote">Not now sets a proposal aside for ${hd} days, then it comes back on its own. Dismissed ones stay here for ${dd} days so you can change your mind; after that they are gone and Mantis does not propose them again.</p>`;
  if(!L.later.length&&!L.declined.length) return note+`<p class="zero">Nothing is hidden.</p>`;
  const sec=(label,n,rows)=>`<div class="gg"><div class="ggh"><span class="cap muted">${label}</span><span class="mono muted">${n}</span></div><ul class="rows">${rows}</ul></div>`;
  return note+(L.later.length?sec("Not now",L.later.length,L.later.map(x=>`<li class="gr static held"><span class="t clamp">${esc(x.title)}</span><span class="when">Back ${fmt(x.hold)}</span><button class="link" data-act="growth-unhold" data-id="${esc(x.id)}">Bring back</button></li>`).join("")):"")
    +(L.declined.length?sec("Dismissed",L.declined.length,L.declined.map(x=>`<li class="gr static held"><span class="t clamp">${esc(x.title)}</span><span class="when">Kept until ${fmt(x.until)}</span><button class="link" data-act="growth-restore" data-id="${esc(x.id)}">Restore</button></li>`).join("")):""); }
function gListHtml(){ const L=gLists();
  if(ST.gv==="Proposed"){ if(!L.prop.length) return `<p class="zero">Nothing left to review. New proposals appear after a pull.${L.hidden?` ${L.hidden} set aside or dismissed: see Hidden.`:""}</p>`;
    return gGroups(L).map(([k,list])=>{ const all=list.length>1, every=list.every(x=>ST.gsel.has(x.i));
      return `<div class="gg"><div class="ggh"><span class="cap muted">${k}</span><span class="mono muted">${list.length}</span>${all?`<button class="link" data-act="growth-select-all" data-group="${k}">${every?"Deselect all":`Select all ${list.length}`}</button>`:""}</div><ul class="rows">${list.map(x=>gRow(x,ST.gsel.has(x.i))).join("")}</ul></div>`; }).join("")
      +`<div class="gbar ${ST.gsel.size?"show":""}" id="gbar"><span><b>${ST.gsel.size}</b> selected</span><button class="btn2" data-act="growth-add-selected">Add selected</button><button class="link" data-act="growth-later">Not now</button><button class="link danger" data-act="growth-dismiss-selected">Dismiss</button></div>`; }
  if(ST.gv==="Hidden") return gHidden(L);
  const list=ST.gv==="In progress"?L.prog:L.done; if(!list.length) return `<p class="zero">${ST.gv==="Done"?"Wins you record and steps you finish appear here.":"Steps and learning you take on appear here."}</p>`;
  return `<ul class="rows">${list.map(x=>`<li class="gr static"><span class="t clamp">${esc(x.title)}${x.when?`<small>${esc(x.when)}</small>`:""}</span><span class="pills">${x.areas.slice(0,2).map(a=>`<span class="chip">${a}</span>`).join("")}</span></li>`).join("")}</ul>`; }
function gFormHtml(){ const f=ST.gform; return `<div class="u-mb12 seg">${KINDS.map(k=>`<button data-gk="${k}" aria-pressed="${f.kind===k}">${k==="Win"?"A win":k==="Step"?"A step to take":"Something to learn"}</button>`).join("")}</div>
  <input class="field" id="gtitle" aria-label="What" placeholder="${f.kind==="Win"?"What did you do? Say the result.":f.kind==="Step"?"What will you do, and why does it matter?":"What do you want to learn?"}">
  <textarea class="u-mt8 u-minh-84 field" id="gwhy" aria-label="Why" placeholder="Evidence or context (optional)"></textarea>
  <div class="u-m-14-0-8 cap muted">Areas</div><div class="pills" id="gareas">${AREAS.map(a=>`<button class="chip sel ${f.areas.has(a.name)?"on":""}" data-garea="${a.name}">${a.name}</button>`).join("")}</div>
  ${f.kind!=="Win"?`<div class="u-m-14-0-8 cap muted">When</div><div class="pills" id="gwhen">${WHENS.map(w=>`<button class="chip sel ${f.when===w?"on":""}" data-gwhen="${w}">${w}</button>`).join("")}</div>`:""}
  <div class="u-mt16 acts"><button class="btn2" data-act="growth-add">${f.kind==="Win"?"Add to my record":"Add as a goal"}</button></div>`; }
const gHead=()=>{ const L=gLists(); return `<b id="gl">${L.prop.length} ${L.prop.length===1?"proposal waits":"proposals wait"} for you.</b> ${L.prog.length} in progress, ${L.done.length} done${L.hidden?`, ${L.hidden} hidden`:""}.`; };

/* feature page: tabs, reader */
function md(src){ const lines=src.replace(/^---[\s\S]*?\n---\n?/,"").split("\n"); let out="",list=false,tbl=false; const inl=s=>esc(s).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/`(.+?)`/g,"<code>$1</code>"), closeL=()=>{ if(list){ out+="</ul>"; list=false; } if(tbl){ out+="</tbody></table>"; tbl=false; } };
  lines.forEach(l=>{ let m; if(/^\s*\|/.test(l)){ if(/^\s*\|[\s:|-]+\|\s*$/.test(l)) return; const c=l.trim().replace(/^\||\|$/g,"").split("|").map(x=>inl(x.trim())); if(!tbl){ closeL(); out+="<table><thead><tr>"+c.map(x=>`<th>${x}</th>`).join("")+"</tr></thead><tbody>"; tbl=true; } else out+="<tr>"+c.map(x=>`<td>${x}</td>`).join("")+"</tr>"; return; }
    if(tbl) closeL(); if(m=l.match(/^(#{1,4})\s+(.*)/)){ closeL(); out+=`<h4 class="mdh">${inl(m[2])}</h4>`; return; } if(m=l.match(/^\s*[-*]\s+(.*)/)){ if(!list){ out+="<ul>"; list=true; } out+=`<li>${inl(m[1])}</li>`; return; }
    if(!l.trim()){ closeL(); return; } closeL(); out+=`<p>${inl(l)}</p>`; }); closeL(); return out; }
const EPIC={key:"",title:"",type:"Epic",sections:[]};
const storyObj=s=>({key:s.key,title:s.title,type:"Story",sections:[["Story","text",s.asa],["Background","text",s.bg],["Acceptance criteria","list",s.ac],["Edge cases","list",s.edge],["Out of scope","list",s.oos],["Open questions","list",s.oq]]});
const FITEMS=()=>[EPIC,...STORIES.map(storyObj)];
function readerHtml(o){ const secs=o.sections.filter(s=>s[2]&&s[2].length), body=s=>s[1]==="list"?s[2].map(x=>"- "+x).join("\n"):s[2], all=[o.key+"  "+o.title,...secs.map(s=>s[0]+"\n"+body(s))].join("\n\n");
  return `<div class="rd-top"><span class="chip">${o.key}</span><span class="chip">${o.type}</span></div><h2 class="rd-t">${esc(o.title)}</h2>
  <div class="rd-a"><button class="btn2" data-copy="${esc(all)}">Copy all</button><span class="hint">Copies ${all.split("\n").length} lines: the title and every section below.</span><a class="link" href="#promotions">Open in Jira</a></div>
  ${secs.map(s=>`<section class="rd-s"><div class="rd-sh"><h4>${s[0]}</h4><button class="link" data-copy="${esc(s[0]+"\n"+body(s))}">Copy</button></div>${s[1]==="list"?`<ul>${s[2].map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:`<p>${esc(s[2])}</p>`}</section>`).join("")}`; }
