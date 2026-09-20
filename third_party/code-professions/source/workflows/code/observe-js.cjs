'use strict';
const fs = require('node:fs');
const functions = require('./module.js');
const cases = JSON.parse(fs.readFileSync('cases.json', 'utf8'));
const rows = cases.map(row => {
  const before = JSON.stringify(row.args);
  let result;
  try { result = {actual: functions[row.function](...row.args)}; }
  catch (error) { result = {error: String(error.message)}; }
  return {id: row.id, ...result, inputUnchanged: before === JSON.stringify(row.args)};
});
process.stdout.write(JSON.stringify({runtime: 'node:' + process.version, cases: rows}));
