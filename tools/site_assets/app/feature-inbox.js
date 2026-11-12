/* feature-inbox.js: files go to the inbox for the next pull: Choose a file, or drop one on the box (Sources tab). Saved through POST api/inbox. */
(() => {
  const OK = /\.(md|txt|vtt|srt|docx|pdf|html?|xlsx|pptx)$/i;
  const base64 = (file) => new Promise((ok, bad) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(",")[1] || ""); r.onerror = () => bad(new Error("Could not read " + file.name)); r.readAsDataURL(file); });
  const send = async (files) => {
    const list = [...files]; if (!list.length) return;
    let sent = 0;
    for (const f of list) {
      if (!OK.test(f.name)) { toast(`${f.name}: Mantis reads notes, Word, PDF, web pages, spreadsheets and decks.`); continue; }
      if (f.size > 15e6) { toast(`${f.name} is over 15 MB.`); continue; }
      try { await Api.post("api/inbox", { name: f.name, data: await base64(f) }); sent++; LV.inboxN = (LV.inboxN || 0) + 1; } catch (e) { toast(e.message); }
    }
    if (sent) { toast(`${sent} file${sent === 1 ? "" : "s"} in the inbox. Read on the next pull.`); updInbox(); }
  };
  UI.action("inbox-choose", () => { const i = $("#cfile"); if (i) i.click(); });
  UI.action("close-layer", () => close());
  document.addEventListener("change", (e) => { if (e.target.id === "cfile") { send(e.target.files); e.target.value = ""; } });
  document.addEventListener("dragover", (e) => { const d = e.target.closest && e.target.closest("#drop"); if (d) { e.preventDefault(); d.classList.add("over"); } });
  document.addEventListener("dragleave", (e) => { const d = e.target.closest && e.target.closest("#drop"); if (d) d.classList.remove("over"); });
  document.addEventListener("drop", (e) => { const d = e.target.closest && e.target.closest("#drop"); if (d) { e.preventDefault(); d.classList.remove("over"); send(e.dataTransfer.files); } });
})();
