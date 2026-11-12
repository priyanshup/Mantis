/* start.js: runs last. Every function exists by now, so the first screen is drawn once, with the final versions.
   Observers that call functions defined in several files start here, not earlier: the loader adds script tags to the page, and an
   observer started too soon ran before its functions existed and threw (the "Something went wrong" flash on load). */
new MutationObserver(m=>{ cancelAnimationFrame(segRaf); segRaf=requestAnimationFrame(()=>{ initSegs(); updCd(); }); }).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["aria-pressed"]});
initSegs(); updCd();
show(location.hash.slice(1));
