'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const core = require('../conformance-core.js');
const exchange = require('../exchange-core.js');

function fixture(name) {
  return JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'examples', 'conformance', name), 'utf8'));
}

const valid = fixture('valid-offer.json');
const validReceipt = core.conformOffer(valid, { checkedAt: '2026-09-12T10:30:00.000Z' });
assert.strictEqual(core.VERSION, '0.10.0');
assert.strictEqual(validReceipt.format, 'axm-material-conformance-receipt');
assert.strictEqual(validReceipt.status, 'PASS');
assert.strictEqual(validReceipt.truthStatus, 'PASS_EXACT_MATERIAL_OFFER_CONFORMANCE');
assert.strictEqual(validReceipt.summary.portableVerified, 1);
assert.strictEqual(validReceipt.summary.held, 0);
assert.strictEqual(validReceipt.entries[0].observedSha256, 'sha256:8d473d4ed6a3cbe533a061b79f1c4b25f1bab5524e5158629fea5b245ea92792');
assert.strictEqual(validReceipt.entries[0].sha256Match, true);
assert.strictEqual(validReceipt.entries[0].mimeMatch, true);
assert.strictEqual(validReceipt.entries[0].signatureMatch, true);

const repeatReceipt = core.conformOffer(JSON.parse(JSON.stringify(valid)), { checkedAt: 'later' });
assert.strictEqual(validReceipt.id, repeatReceipt.id, 'conformance identity must ignore check time');
assert.strictEqual(validReceipt.offer.fingerprint, repeatReceipt.offer.fingerprint);

const mismatch = core.conformOffer(fixture('hash-mismatch-offer.json'));
assert.strictEqual(mismatch.status, 'HOLD');
assert.deepStrictEqual(mismatch.entries[0].holds, ['sha256-mismatch']);
assert.strictEqual(mismatch.families[0].installable, false);

const missing = core.conformOffer(fixture('missing-bytes-offer.json'));
assert.strictEqual(missing.status, 'HOLD');
assert.deepStrictEqual(missing.entries[0].holds, ['no-portable-payload']);
assert.strictEqual(missing.summary.held, 1);

const duplicate = core.conformOffer(fixture('duplicate-id-offer.json'));
assert.strictEqual(duplicate.status, 'HOLD');
assert.strictEqual(duplicate.truthStatus, 'HOLD_STRUCTURAL_CONTRACT');
assert.match(duplicate.reason, /Duplicate material offer entry id/);

const dangling = core.conformOffer(fixture('dangling-family-offer.json'));
assert.strictEqual(dangling.status, 'HOLD');
assert.match(dangling.reason, /references missing entries/);

const unassigned = core.conformOffer(fixture('unassigned-offer.json'));
assert.strictEqual(unassigned.status, 'PASS');
assert.strictEqual(unassigned.entries[0].channel, 'unassigned');
assert.strictEqual(unassigned.entries[0].state, 'PASS_RECEIVER_HASHED');
assert.ok(unassigned.entries[0].observedSha256.startsWith('sha256:'));

const mimeMismatchOffer = JSON.parse(JSON.stringify(valid));
mimeMismatchOffer.entries[0].mime = 'image/jpeg';
const mimeMismatch = core.conformOffer(mimeMismatchOffer);
assert.strictEqual(mimeMismatch.status, 'HOLD');
assert.ok(mimeMismatch.entries[0].holds.includes('declared-mime-mismatch'));

const badSignatureOffer = JSON.parse(JSON.stringify(valid));
badSignatureOffer.entries[0].dataUrl = 'data:image/png;base64,aGVsbG8=';
badSignatureOffer.entries[0].sha256 = null;
const badSignature = core.conformOffer(badSignatureOffer);
assert.strictEqual(badSignature.status, 'HOLD');
assert.ok(badSignature.entries[0].holds.includes('image-signature-mismatch'));

const projection = core.buildFamilyProjection(valid, 'family', { receipt: validReceipt });
assert.strictEqual(projection.status, 'PASS');
assert.strictEqual(projection.installable, true);
assert.strictEqual(projection.libraryBundle.entries.length, 1);
assert.strictEqual(projection.libraryBundle.entries[0].source.conformance.state, 'PASS_PORTABLE_VERIFIED');
assert.strictEqual(projection.influenceWorkspace.format, 'axm-material-influence-workspace');
assert.strictEqual(projection.influenceWorkspace.recipes[0].stack.length, 1);
assert.strictEqual(projection.influenceWorkspace.recipes[0].stack[0].targetChannel, 'base-color');

const missingOffer = fixture('missing-bytes-offer.json');
const missingProjection = core.buildFamilyProjection(missingOffer, 'family', { receipt: missing });
assert.strictEqual(missingProjection.installable, false);
assert.strictEqual(missingProjection.influenceWorkspace.recipes[0].stack[0].targetChannel, 'height');
assert.strictEqual(missingProjection.influenceWorkspace.librarySnapshot.entries[0].dataUrl, null);

const feedback = exchange.makeFeedback({
  offer: valid,
  familyId: 'family',
  verification: validReceipt.verification,
  createdAt: '2026-09-12T10:40:00.000Z',
  notes: 'Round-trip conformance fixture.'
});
const feedbackReceipt = core.conformFeedback(feedback, { offer: valid, checkedAt: '2026-09-12T10:41:00.000Z' });
assert.strictEqual(feedbackReceipt.status, 'PASS');
assert.strictEqual(feedbackReceipt.feedback.offerId, valid.id);
assert.strictEqual(feedbackReceipt.relatedOffer.fingerprint, validReceipt.offer.fingerprint);

const badFeedback = JSON.parse(JSON.stringify(feedback));
badFeedback.offer.fingerprint = 'deadbeef';
const badFeedbackReceipt = core.conformFeedback(badFeedback, { offer: valid });
assert.strictEqual(badFeedbackReceipt.status, 'HOLD');
assert.ok(badFeedbackReceipt.holds.includes('feedback-offer-fingerprint-mismatch'));

const detachedFeedbackReceipt = core.conformFeedback(feedback);
assert.strictEqual(detachedFeedbackReceipt.status, 'PASS');
assert.ok(detachedFeedbackReceipt.warnings.some((warning) => /No related offer supplied/.test(warning)));

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'axm-material-conformance-'));
const projectionOut = path.join(temp, 'projection.json');
const validPath = path.join(__dirname, '..', 'examples', 'conformance', 'valid-offer.json');
const mismatchPath = path.join(__dirname, '..', 'examples', 'conformance', 'hash-mismatch-offer.json');
const cli = path.join(__dirname, '..', 'tools', 'material-conformance.js');

const cliPass = spawnSync(process.execPath, [cli, 'check-material-offer', validPath, '--family', 'family', '--projection-out', projectionOut], { encoding: 'utf8' });
assert.strictEqual(cliPass.status, 0, cliPass.stderr);
assert.strictEqual(JSON.parse(cliPass.stdout).status, 'PASS');
assert.strictEqual(fs.existsSync(projectionOut), true);
assert.strictEqual(JSON.parse(fs.readFileSync(projectionOut, 'utf8')).installable, true);

const cliHold = spawnSync(process.execPath, [cli, 'check-material-offer', mismatchPath], { encoding: 'utf8' });
assert.strictEqual(cliHold.status, 2, cliHold.stderr);
assert.strictEqual(JSON.parse(cliHold.stdout).status, 'HOLD');

const feedbackPath = path.join(temp, 'feedback.json');
fs.writeFileSync(feedbackPath, JSON.stringify(feedback), 'utf8');
const cliFeedback = spawnSync(process.execPath, [cli, 'check-material-feedback', feedbackPath, '--offer', validPath], { encoding: 'utf8' });
assert.strictEqual(cliFeedback.status, 0, cliFeedback.stderr);
assert.strictEqual(JSON.parse(cliFeedback.stdout).status, 'PASS');

fs.rmSync(temp, { recursive: true, force: true });

assert.match(validReceipt.truthBoundary.authority, /never installs, promotes, merges, or rewrites/);
console.log('AXM material conformance tests: PASS');
