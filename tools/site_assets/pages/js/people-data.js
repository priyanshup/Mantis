/* people-data: what the drawer and the palette take from the people modules, in one place. */
Mantis.define("people-data", ["people-live", "people-brief", "people-follow"], (m_live, m_brief, m_follow) => {
  const { X, xOn, loadX, dShort } = m_live;
  const { briefLinks } = m_brief;
  const { fuRow, stepRow } = m_follow;
  return { X, briefLinks, xOn, loadX, dShort, fuRow, stepRow };
});
