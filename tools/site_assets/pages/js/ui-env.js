/* ui-env: reduced-motion, root element and the typing test. */
Mantis.define("ui-env", [], () => {
  const calm = matchMedia("(prefers-reduced-motion: reduce)");
  const root = document.documentElement;
  const typing = () => { const a = document.activeElement; return !!a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable); };
  return { calm, root, typing };
});
