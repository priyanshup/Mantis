// Syntax-check many scripts in one Node process: node syntax-check.js file1.js file2.js ...
// Prints one JSON object {file: "message"} for files that do not parse (empty {} when all do). Used by tools/selftest.py:
// starting node once per file took about a second each on this machine, so the self-test took nearly a minute.
const fs = require("fs");
const vm = require("vm");
const bad = {};
for (const file of process.argv.slice(2)) {
  try {
    new vm.Script(fs.readFileSync(file, "utf8"), { filename: file });
  } catch (e) {
    bad[file] = String(e && e.message || e).slice(0, 300);
  }
}
process.stdout.write(JSON.stringify(bad));
