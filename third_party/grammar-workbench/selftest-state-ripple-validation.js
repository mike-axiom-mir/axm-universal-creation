'use strict';
const assert = require('assert');
const Ripple = require('./state-ripple-core.js');

let assertions = 0;
function ok(value, message) { assert.ok(value, message); assertions += 1; }
function eq(actual, expected, message) { assert.deepStrictEqual(actual, expected, message); assertions += 1; }
function throws(fn, part) { assert.throws(fn, error => String(error.message || error).includes(part)); assertions += 1; }

const valid = Ripple.createFabric({
  fabricId: 'validation-fixture',
  nodes: [{
    id: 'copy-input',
    reads: ['input.x'],
    writes: ['out.x'],
    dependsOn: [],
    effects: [],
    operations: [{ op: 'COPY', from: 'input.x', path: 'out.x' }]
  }]
});

ok(Ripple.validFabric(valid), 'factory-built fabric remains valid');
eq(Ripple.runAll(valid, { input: { x: 7 } }).finalState.out.x, 7, 'valid fabric still executes');

const forged = JSON.parse(JSON.stringify(valid));
forged.nodes[0].operations = [{ op: 'SET', path: 'undeclared.y', value: 99 }];
const nodeCore = { ...forged.nodes[0] };
delete nodeCore.nodeSha256;
forged.nodes[0].nodeSha256 = Ripple.sha256(nodeCore);
delete forged.fabricSha256;
forged.fabricSha256 = Ripple.sha256(forged);

ok(!Ripple.validFabric(forged), 'self-consistent outer digest cannot bypass declared-write validation');
throws(() => Ripple.runAll(forged, { input: { x: 7 } }), 'VALID_FABRIC_REQUIRED');

const graphForged = JSON.parse(JSON.stringify(valid));
graphForged.graph.order = ['ghost-node'];
graphForged.graph.incoming = { 'ghost-node': [] };
graphForged.graph.outgoing = { 'ghost-node': [] };
const graphCore = { order: graphForged.graph.order, incoming: graphForged.graph.incoming, outgoing: graphForged.graph.outgoing };
graphForged.graph.graphSha256 = Ripple.sha256(graphCore);
delete graphForged.fabricSha256;
graphForged.fabricSha256 = Ripple.sha256(graphForged);

ok(!Ripple.validFabric(graphForged), 'self-consistent graph digest cannot replace the deterministic rebuilt graph');
throws(() => Ripple.runAll(graphForged, { input: { x: 7 } }), 'VALID_FABRIC_REQUIRED');

console.log(JSON.stringify({
  result: 'GRAMMAR_GLASS_STATE_RIPPLE_VALIDATION_SELFTEST_PASS',
  assertions,
  authority: 'NONE'
}, null, 2));
