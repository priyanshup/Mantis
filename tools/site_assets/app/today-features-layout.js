/* v11: week back in the right column (whole week, vertical), Features as a ruled list, plainer people lines */


const raiseRow=(i,j,a)=>`<li class="trow ${ST.raised.has(i+"-"+j)?"done":""}"><button class="ck" data-raise="${i}-${j}" aria-pressed="${ST.raised.has(i+"-"+j)}" aria-label="Mark as raised">${CK}</button><span class="t clamp">${esc(a[0])}</span><span class="when">${esc(a[1])}</span></li>`;
const RAISE_SHOWN = 5;   // rows of "To raise" visible before the "N more" button
function meetDetail(i){ const m=MEET[i], names=m.w.slice(0,4).join(", ")+(m.w.length>4?` and ${m.w.length-4} more`:"");
  return `<div class="card-h"><h2>${esc(m.n)}</h2><span class="mono muted">${m.d} ${m.t}</span><button class="link" data-act="meeting-edit" data-id="${esc(m.id)}">Edit</button></div><p class="u-maxw-60ch muted">${esc(m.why)}</p>
  <p class="u-m-10-0-0 mono muted">${esc(names)}</p>
  <h2 class="u-m-22-0-4">To raise</h2>${m.ag.length?`<ul class="rows">${m.ag.slice(0,RAISE_SHOWN).map((a,j)=>raiseRow(i,j,a)).join("")}</ul>${m.ag.length>RAISE_SHOWN?`<div class="acc more-acc"><div class="in"><ul class="rows">${m.ag.slice(RAISE_SHOWN).map((a,j)=>raiseRow(i,j+RAISE_SHOWN,a)).join("")}</ul></div></div><button class="more" data-more data-t="${m.ag.length-RAISE_SHOWN} more">${m.ag.length-RAISE_SHOWN} more</button>`:""}`:`<p class="zero">Nothing waiting for this meeting.</p>`}
  <div class="u-mt18"><button class="pick nochev" data-take>Add takeaways</button></div>
  <div class="acc" id="take"><div class="in"><div class="u-pt12"><input class="field" aria-label="Title" value="${esc(m.n)}, ${DATES[m.d]}"><textarea class="u-mt8 u-minh-110 field" data-grow aria-label="Takeaways" placeholder="What was said or decided. Mantis turns it into follow-ups and answers."></textarea><div class="acts"><button class="btn2" data-savetake>Save takeaways</button></div></div></div></div>`; }
document.addEventListener("click",e=>{ const b=e.target.closest&&e.target.closest(".frow[data-f]"); if(b&&b.dataset.f==="Promotions") location.hash="promotions"; });
