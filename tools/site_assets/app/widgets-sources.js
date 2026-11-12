/* widgets-sources.js: the widgets on Sources, and the screen. layout.json decides where each one sits. */
UI.widget("sources.compose", () => composeHtml());
UI.widget("sources.recent", () => UI.cardHead("Recently read", { hint: "and the feature it fed" })
  + `<ul class="rows">${RECENT.map((r) => `<li><span class="t">${r.title}<small>${r.kind}</small></span><span class="chip">${r.feat}</span><span class="when">${r.date}</span></li>`).join("")}</ul>`);
UI.widget("sources.health", () => LV.healthHtml);
UI.widget("sources.pull", () => UI.cardHead("Pull from Jira and Confluence", { action: '<button class="link" data-act="filter-new">New filter</button>' })
  + `<p class="muted u-mb6">${LV.pullLine}</p><ul class="rows">${FILT.map((f) => `<li><button class="t" data-act="filter-edit" data-fid="${esc(f.id)}" aria-label="Edit ${esc(f.label)}">${esc(f.label)}<small>${f.kind} · ${f.found}</small></button><button class="sw${f.on ? " on" : ""}" role="switch" aria-checked="${f.on}" aria-label="${f.label}" data-fid="${f.id}"><i></i></button></li>`).join("")}</ul>`);

S.sources = () => `<div class="screen">${UI.head("Sources", { sub: "Add material, pull from Jira and Confluence, and see what was read.", action: '<button class="btn" data-pull>Start a pull</button>' })}
  ${UI.place("sources", null)}</div>`;
