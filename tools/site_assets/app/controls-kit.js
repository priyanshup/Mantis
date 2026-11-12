/* v8 controls kit: themed combobox, date picker, auto-growing text. Replaces every native select, datalist and date input. */
const MONTHS_LONG=["January","February","March","April","May","June","July","August","September","October","November","December"], DOW=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const CAL_ICON='<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/></svg>';
function fmtLong(iso){ if(!iso) return ""; const d=new Date(iso+"T12:00:00"), y=d.getFullYear()!==TODAYD.getFullYear()?" "+d.getFullYear():""; return `${DOW[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]}${y}`; }
function dateHtml(id,iso,ph){ return `<button type="button" class="field dpb" id="${id}" data-date="${id}" data-v="${iso||""}" data-ph="${esc(ph)}" aria-haspopup="dialog"><span class="${iso?"":"ph"}">${iso?fmtLong(iso):esc(ph)}</span>${CAL_ICON}</button>`; }
function setDate(btn,iso){ btn.dataset.v=iso||""; const s=btn.querySelector("span"); s.textContent=iso?fmtLong(iso):btn.dataset.ph; s.classList.toggle("ph",!iso); }
const CHEV_SVG='<svg class="chev" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>';
function comboHtml(id,value,kind,ph){ return `<div class="cb"><input class="field" id="${id}" data-combo="${kind}" value="${esc(value)}" placeholder="${esc(ph)}" autocomplete="off" role="combobox" aria-expanded="false">${CHEV_SVG}</div>`; }
function comboRows(kind,q,all){ const ql=q.trim().toLowerCase(); let rows;
  if(kind==="groups"){ const names=groupNames(); rows=[...names.map(n=>[n,"Group"]),...FEATS.map(f=>f.title).filter(n=>!names.includes(n)).map(n=>[n,"Feature card"])]; } else rows=PEOPLE.map(p=>[p.name,p.role]);
  const f=all||!ql?rows.slice():rows.filter(r=>r[0].toLowerCase().includes(ql)||r[1].toLowerCase().includes(ql)); const exact=rows.some(r=>r[0].toLowerCase()===ql);
  if(q.trim()&&!exact&&!all) f.push([q.trim(),kind==="groups"?"Create new group":"Use this name"]); return f; }
function comboHtmlRows(rows,cur){ if(!rows.length) return `<p class="u-p-8-10 zero">Nothing yet. Keep typing.</p>`; const ci=rows.findIndex(r=>r[0]===cur), sel=ci>=0?ci:0;
  return rows.map((r,i)=>`<button type="button" data-cv="${esc(r[0])}" class="${i===sel?"sel":""} ${r[0]===cur?"cur":""}">${r[1].startsWith("Create")?"Create “"+esc(r[0])+"”":esc(r[0])}<span class="hint">${esc(r[1])}</span></button>`).join(""); }
function growEl(el){ el.style.height="auto"; el.style.height=Math.min(el.scrollHeight+2,340)+"px"; }
