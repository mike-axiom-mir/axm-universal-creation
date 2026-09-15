'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../donors/collaboration-studio/source');
const studio = path.join(root, 'tools/studio');
const actions = require(path.join(studio, 'studio-actions.js')).ACTIONS;
assert.equal(actions.length, 84);
assert.equal(new Set(actions.map(a => a.id)).size, 84);
for (const suffix of ['layer.add','layer.clear','animation.add-frame','animation.export']) {
  assert(actions.some(a => a.id.endsWith(suffix)), suffix);
}
let count = 0;
for (const file of ['engine.html','index.html']) {
  const html = fs.readFileSync(path.join(studio,file),'utf8');
  for (const match of html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)) {
    new Function(match[1]); // Parse only. No DOM, network, user session or UI execution.
    count++;
  }
}
assert(count > 0);
console.log(`Recovered Studio: 84 unique actions and ${count} inline scripts parse. UI execution not claimed.`);
