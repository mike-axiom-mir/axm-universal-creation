'use strict';

const assert = require('assert');
const Ripple = require('./state-ripple-core.js');

let assertions = 0;
function ok(value, message) { assert.ok(value, message); assertions += 1; }
function eq(actual, expected, message) { assert.deepStrictEqual(actual, expected, message); assertions += 1; }
function throws(fn, part) { assert.throws(fn, error => String(error.message || error).includes(part)); assertions += 1; }

function resealEntry(entry) {
  const core = { ...entry };
  delete core.cacheEntrySha256;
  return { ...core, cacheEntrySha256: Ripple.sha256(core) };
}

function resealBaseline(baseline, cache) {
  const core = { ...baseline, cache };
  delete core.baselineSha256;
  return { ...core, baselineSha256: Ripple.sha256(core) };
}

const fabric = Ripple.createFabric({
  fabricId: 'baseline-admission-fixture',
  nodes: [{
    id: 'copy-input',
    reads: ['input.x'],
    writes: ['output.safe'],
    dependsOn: [],
    effects: [],
    operations: [{ op: 'COPY', from: 'input.x', path: 'output.safe' }]
  }]
});

const input = { input: { x: 7 } };
const full = Ripple.runAll(fabric, input);
ok(Ripple.validBaseline(fabric, full.baseline), 'factory baseline remains valid');

const original = full.baseline.cache['copy-input'];
const escapedWrites = [{ path: 'output.escaped', value: { present: true, value: 99 } }];
const transplanted = resealEntry({
  ...original,
  nodeId: 'foreign-node',
  nodeSha256: '0'.repeat(64),
  writeValues: escapedWrites,
  outputSha256: Ripple.sha256({ writeValues: escapedWrites, emittedSignals: [] })
});
const forged = resealBaseline(full.baseline, { 'copy-input': transplanted });

eq(Ripple.validBaseline(fabric, forged), false, 'self-consistent foreign cache entry is rejected');
throws(() => Ripple.sparseUpdate(fabric, input, forged, { wakeBudget: 0, expectedBaselineSha256: full.baseline.baselineSha256 }), 'CURRENT_BASELINE_REQUIRED');

const wrongOutput = resealEntry({ ...original, outputSha256: 'f'.repeat(64) });
const wrongOutputBaseline = resealBaseline(full.baseline, { 'copy-input': wrongOutput });
eq(Ripple.validBaseline(fabric, wrongOutputBaseline), false, 'cache output identity must bind its exact patch and signals');

const undeclaredSignal = ['fabric.escalated'];
const signalEntry = resealEntry({
  ...original,
  emittedSignals: undeclaredSignal,
  outputSha256: Ripple.sha256({ writeValues: original.writeValues, emittedSignals: undeclaredSignal })
});
const signalBaseline = resealBaseline(full.baseline, { 'copy-input': signalEntry });
eq(Ripple.validBaseline(fabric, signalBaseline), false, 'cache signals must match the node operation contract');

const nonPortableWrites = [{ path: 'output.safe', value: { present: true, value: Number.NaN } }];
const nonPortableEntry = resealEntry({
  ...original,
  writeValues: nonPortableWrites,
  outputSha256: Ripple.sha256({ writeValues: nonPortableWrites, emittedSignals: [] })
});
const nonPortableBaseline = resealBaseline(full.baseline, { 'copy-input': nonPortableEntry });
eq(Ripple.validBaseline(fabric, nonPortableBaseline), false, 'non-portable cache values cannot hide behind JSON hash equivalence');

const declaredButFalseWrites = [{ path: 'output.safe', value: { present: true, value: 99 } }];
const declaredButFalseEntry = resealEntry({
  ...original,
  writeValues: declaredButFalseWrites,
  outputSha256: Ripple.sha256({ writeValues: declaredButFalseWrites, emittedSignals: [] })
});
const declaredButFalseBaseline = resealBaseline(full.baseline, { 'copy-input': declaredButFalseEntry });
ok(Ripple.validBaseline(fabric, declaredButFalseBaseline), 'self-consistent same-node cache remains structurally valid without external origin evidence');
throws(
  () => Ripple.sparseUpdate(fabric, input, declaredButFalseBaseline, { wakeBudget: 0, expectedBaselineSha256: full.baseline.baselineSha256 }),
  'BASELINE_PIN_MISMATCH'
);
throws(
  () => Ripple.sparseUpdate(fabric, input, declaredButFalseBaseline, { wakeBudget: 0 }),
  'BASELINE_PIN_REQUIRED'
);
const pinned = Ripple.sparseUpdate(fabric, input, full.baseline, { wakeBudget: 0, expectedBaselineSha256: full.baseline.baselineSha256 });
eq(pinned.result, 'STATE_RIPPLE_SPARSE_UPDATE_COMPLETE', 'trusted factory baseline admits unchanged cache reuse');
eq(pinned.finalState.output.safe, 7, 'trusted cache cannot replace the declared COPY result with re-sealed bytes');

const portableCopy = JSON.parse(JSON.stringify(full.baseline));
ok(Ripple.validBaseline(fabric, portableCopy), 'portable copy remains structurally valid');
const admittedCopy = Ripple.sparseUpdate(fabric, input, portableCopy, { wakeBudget: 0, expectedBaselineSha256: full.baseline.baselineSha256 });
eq(admittedCopy.finalState.output.safe, 7, 'independently pinned portable baseline can be reused');

console.log(JSON.stringify({
  result: 'GRAMMAR_GLASS_STATE_RIPPLE_BASELINE_ADMISSION_SELFTEST_PASS',
  assertions,
  authority: 'NONE'
}, null, 2));
