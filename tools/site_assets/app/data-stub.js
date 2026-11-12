/* Empty containers for what the mock's scripts expect to find; live.js fills them from the live data. */
const REAL = { today: ((window.__LIVE || {}).tasks || {}).today || new Date().toISOString().slice(0, 10), tasks: [], overdue: 0, dueToday: 0 };
const EXTRA = { week: [], carried: 0, sugg: [], archN: 0, arch: [] };
const STORIES = [];
var UJ = "";
const GROWD = [];
const DECLINED = [];
