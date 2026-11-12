/* _registry.js: the module registry for the content pages. It loads first; every other file in this folder is one module.
   A module says what it needs: Mantis.define("name", ["core"], (core) => { ...; return { what, others, may, use }; }).
   It gets only those modules, so nothing reaches into another module's variables. One module failing is logged and does not stop the rest. */
const Mantis = (() => {
  const mods = {};
  const define = (name, needs, build) => {
    try {
      const args = needs.map((n) => { if (!(n in mods)) throw new Error(`needs "${n}", which this page does not load or which failed`); return mods[n]; });
      mods[name] = build(...args) || {};
    } catch (e) { console.error(`Mantis module "${name}":`, e); }
  };
  return { define };
})();
