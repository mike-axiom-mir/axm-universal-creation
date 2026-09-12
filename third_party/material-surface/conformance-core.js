'use strict';

const crypto = require('node:crypto');
const exchange = require('./exchange-core.js');
const influence = require('./influence-core.js');
const library = require('./library-core.js');

const VERSION = '0.10.0';
const RECEIPT_FORMAT = 'axm-material-conformance-receipt';
const FIXED_PROJECTION_TIME = '1970-01-01T00:00:00.000Z';

function clone(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function sha256Bytes(bytes) {
  return `sha256:${crypto.createHash('sha256').update(bytes).digest('hex')}`;
}

function sha256Text(value) {
  return sha256Bytes(Buffer.from(String(value == null ? '' : value), 'utf8'));
}

function canonicalMime(value) {
  const mime = String(value || '').trim().toLowerCase();
  if (mime === 'image/jpg') return 'image/jpeg';
  return mime;
}

function parseImageDataUrl(value) {
  const match = /^data:image\/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/\r\n]+={0,2})$/i.exec(String(value || ''));
  if (!match) throw new TypeError('Portable material payload must be a base64 PNG/JPEG/WEBP data URL.');
  const compact = match[2].replace(/\s+/g, '');
  if (!compact || compact.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(compact)) {
    throw new TypeError('Portable material payload has malformed base64 bytes.');
  }
  const bytes = Buffer.from(compact, 'base64');
  if (!bytes.length) throw new TypeError('Portable material payload decoded to zero bytes.');
  return {
    mime: canonicalMime(`image/${match[1]}`),
    bytes
  };
}

function signatureMatches(mime, bytes) {
  const kind = canonicalMime(mime);
  if (kind === 'image/png') {
    const magic = [0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a];
    return bytes.length >= magic.length && magic.every((value, index) => bytes[index] === value);
  }
  if (kind === 'image/jpeg') {
    return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  }
  if (kind === 'image/webp') {
    return bytes.length >= 12 && bytes.subarray(0, 4).toString('ascii') === 'RIFF' && bytes.subarray(8, 12).toString('ascii') === 'WEBP';
  }
  return false;
}

function verifyEntry(entry) {
  const normalized = exchange.normalizeEntry(entry);
  const base = {
    entryId: normalized.id,
    channel: normalized.channel,
    declaredMime: canonicalMime(normalized.mime),
    payloadMime: null,
    byteLength: 0,
    declaredSha256: normalized.sha256,
    observedSha256: null,
    sha256Match: null,
    mimeMatch: null,
    signatureMatch: null,
    state: 'HOLD',
    holds: [],
    notes: []
  };

  if (!normalized.dataUrl) {
    base.holds.push('no-portable-payload');
    base.notes.push('Metadata/channel state remains valid exchange evidence, but no bytes are available for headless payload conformance.');
    return base;
  }

  let parsed;
  try {
    parsed = parseImageDataUrl(normalized.dataUrl);
  } catch (error) {
    base.holds.push('invalid-data-url-or-base64');
    base.notes.push(error.message);
    return base;
  }

  base.payloadMime = parsed.mime;
  base.byteLength = parsed.bytes.length;
  base.observedSha256 = sha256Bytes(parsed.bytes);
  base.mimeMatch = canonicalMime(normalized.mime) === parsed.mime;
  base.signatureMatch = signatureMatches(parsed.mime, parsed.bytes);
  if (!base.mimeMatch) base.holds.push('declared-mime-mismatch');
  if (!base.signatureMatch) base.holds.push('image-signature-mismatch');

  if (normalized.sha256) {
    base.sha256Match = normalized.sha256.toLowerCase() === base.observedSha256.toLowerCase();
    if (!base.sha256Match) base.holds.push('sha256-mismatch');
  } else {
    base.notes.push('Producer supplied no SHA-256; receiver computed an observed SHA-256 without claiming producer-side byte attestation.');
  }

  if (!base.holds.length) {
    base.state = normalized.sha256 ? 'PASS_PORTABLE_VERIFIED' : 'PASS_RECEIVER_HASHED';
  }
  return base;
}

function verificationMap(entryChecks) {
  const map = {};
  for (const check of entryChecks || []) {
    map[check.entryId] = {
      observedSha256: check.observedSha256,
      sha256Match: check.declaredSha256 ? check.sha256Match : null,
      mimeMatch: check.mimeMatch,
      signatureMatch: check.signatureMatch,
      conformanceState: check.state,
      holds: clone(check.holds || [])
    };
  }
  return map;
}

function receiptId(kind, basis) {
  return `conformance-${kind}-${sha256Text(exchange.stableStringify(basis)).slice('sha256:'.length, 'sha256:'.length + 16)}`;
}

function structuralHold(kind, reason, checkedAt) {
  const basis = { kind, reason };
  return {
    format: RECEIPT_FORMAT,
    version: VERSION,
    id: receiptId(kind, basis),
    checkedAt: checkedAt || null,
    inputKind: kind,
    status: 'HOLD',
    truthStatus: 'HOLD_STRUCTURAL_CONTRACT',
    reason,
    exchangeContract: `${exchange.OFFER_FORMAT}/${exchange.VERSION} + ${exchange.FEEDBACK_FORMAT}/${exchange.VERSION}`,
    truthBoundary: {
      conformance: 'A HOLD preserves failed or incomplete interchange state; it is never rewritten into a pass.',
      quality: 'Conformance verifies contract/byte integrity only, not beauty, realism, PBR correctness, physical truth, or usefulness.',
      authority: 'A conformance PASS does not install, promote, merge, or rewrite canonical state in any producer or receiver.'
    }
  };
}

function conformOffer(rawOffer, options) {
  const source = options || {};
  const structural = exchange.validateOffer(rawOffer);
  if (!structural.ok) return structuralHold('offer', structural.reason, source.checkedAt);

  const offer = exchange.normalizeOffer(rawOffer);
  const entryChecks = offer.entries.map(verifyEntry);
  const checkMap = new Map(entryChecks.map((row) => [row.entryId, row]));
  const families = offer.families.map((family) => {
    const members = family.entryIds.map((entryId) => checkMap.get(entryId));
    const holds = members.flatMap((row) => row && row.holds || []);
    return {
      id: family.id,
      name: family.name,
      entryIds: family.entryIds.slice(),
      status: holds.length ? 'HOLD' : 'PASS',
      holds: [...new Set(holds)].sort(),
      installable: holds.length === 0
    };
  });
  const heldEntries = entryChecks.filter((row) => row.state === 'HOLD');
  const unhashedEntries = entryChecks.filter((row) => row.state === 'PASS_RECEIVER_HASHED');
  const fingerprint = exchange.offerFingerprint(offer);
  const basis = {
    offerId: offer.id,
    fingerprint,
    entries: entryChecks.map((row) => ({ id: row.entryId, state: row.state, observedSha256: row.observedSha256, holds: row.holds })),
    families: families.map((row) => ({ id: row.id, status: row.status }))
  };
  const status = heldEntries.length ? 'HOLD' : 'PASS';
  return {
    format: RECEIPT_FORMAT,
    version: VERSION,
    id: receiptId('offer', basis),
    checkedAt: source.checkedAt || null,
    inputKind: 'offer',
    status,
    truthStatus: status === 'PASS' ? 'PASS_EXACT_MATERIAL_OFFER_CONFORMANCE' : 'HOLD_MATERIAL_OFFER_CONFORMANCE',
    offer: {
      id: offer.id,
      fingerprint,
      producer: clone(offer.producer),
      entries: offer.entries.length,
      families: offer.families.length
    },
    entries: entryChecks,
    families,
    summary: {
      entries: entryChecks.length,
      portableVerified: entryChecks.filter((row) => row.state === 'PASS_PORTABLE_VERIFIED').length,
      receiverHashed: unhashedEntries.length,
      held: heldEntries.length,
      families: families.length,
      passFamilies: families.filter((row) => row.status === 'PASS').length,
      heldFamilies: families.filter((row) => row.status === 'HOLD').length
    },
    verification: verificationMap(entryChecks),
    truthBoundary: {
      conformance: 'PASS means the v0.9 offer structure and available portable bytes satisfy this v0.10 headless verifier. Metadata-only entries remain HOLD.',
      hashes: 'Receiver-computed SHA-256 proves the bytes observed by this verifier. When no producer hash exists it does not prove producer-side attestation.',
      image: 'Image signature checks identify declared container type only; they are not full image decode, semantic, visual-quality, or PBR validation.',
      quality: 'Conformance is not beauty, realism, PBR correctness, physical truth, taste, or universal material quality.',
      authority: 'PASS never installs, promotes, merges, or rewrites canonical state automatically.'
    }
  };
}

function buildFamilyProjection(rawOffer, familyId, options) {
  const source = options || {};
  const receipt = source.receipt || conformOffer(rawOffer, { checkedAt: source.checkedAt || null });
  if (receipt.inputKind !== 'offer' || !receipt.offer) throw new TypeError('A structurally valid material offer is required for projection.');
  const offer = exchange.normalizeOffer(rawOffer);
  const familyReceipt = receipt.families.find((row) => row.id === familyId);
  if (!familyReceipt) throw new TypeError(`Unknown offer family: ${familyId}`);
  const stamp = source.at || FIXED_PROJECTION_TIME;
  const bundle = exchange.toLibraryBundle(offer, familyId, receipt.verification, stamp);
  const checks = new Map(receipt.entries.map((row) => [row.entryId, row]));
  bundle.entries.forEach((entry) => {
    const producerEntryId = entry.source && entry.source.producerEntryId;
    const check = checks.get(producerEntryId);
    entry.source.conformance = check ? {
      version: VERSION,
      state: check.state,
      observedSha256: check.observedSha256,
      holds: clone(check.holds)
    } : { version: VERSION, state: 'HOLD', holds: ['missing-conformance-check'] };
  });
  bundle.family.exchange.conformance = {
    version: VERSION,
    status: familyReceipt.status,
    holds: clone(familyReceipt.holds),
    installable: familyReceipt.installable
  };

  const workspace = influence.createWorkspace(stamp);
  const recipe = influence.activeRecipe(workspace);
  recipe.name = `${bundle.family.name} — v0.10 conformance projection`;
  recipe.familyIds = [bundle.family.id];
  recipe.notes = 'Headless projection of an exact v0.9 material offer family. Layer channels remain producer-declared; conformance does not assert physical material meaning.';
  for (const entry of bundle.entries) {
    influence.addLayer(recipe, {
      entryId: entry.libraryId,
      targetChannel: entry.usage.channelHint,
      blendMode: 'normal',
      opacity: 1,
      visible: true,
      role: 'v0.10-conformance-offer-channel'
    }, stamp);
  }
  workspace.librarySnapshot = {
    entries: bundle.entries.map((entry) => library.normalizeEntry(entry, stamp)),
    families: [clone(bundle.family)],
    observedAt: stamp,
    source: 'v0.10-headless-material-conformance'
  };
  workspace.updatedAt = stamp;
  workspace.truthBoundary.conformance = 'This workspace is a deterministic receiver-side projection of offered state. HOLD entries stay represented; projection is not installation or acceptance.';
  const validation = influence.validateWorkspace(workspace);
  if (!validation.ok) throw new TypeError(`Projected influence workspace failed validation: ${validation.reason}`);

  return {
    format: 'axm-material-conformance-projection',
    version: VERSION,
    offerId: offer.id,
    offerFingerprint: receipt.offer.fingerprint,
    producerFamilyId: familyId,
    status: familyReceipt.status,
    installable: familyReceipt.installable,
    holds: clone(familyReceipt.holds),
    libraryBundle: bundle,
    influenceWorkspace: workspace,
    truthBoundary: {
      projection: 'Library and Influence state are detached receiver projections using existing v0.4/v0.5 contracts.',
      authority: 'Projection does not persist, install, evaluate, or rewrite anything by itself.'
    }
  };
}

function conformFeedback(rawFeedback, options) {
  const source = options || {};
  const structural = exchange.validateFeedback(rawFeedback);
  if (!structural.ok) return structuralHold('feedback', structural.reason, source.checkedAt);

  const holds = [];
  const warnings = [];
  let relatedOffer = null;
  if (source.offer) {
    const offerValidation = exchange.validateOffer(source.offer);
    if (!offerValidation.ok) holds.push(`related-offer-invalid:${offerValidation.reason}`);
    else {
      const offer = exchange.normalizeOffer(source.offer);
      const fingerprint = exchange.offerFingerprint(offer);
      relatedOffer = { id: offer.id, fingerprint };
      if (rawFeedback.offer.id !== offer.id) holds.push('feedback-offer-id-mismatch');
      if (rawFeedback.offer.fingerprint !== fingerprint) holds.push('feedback-offer-fingerprint-mismatch');
      if (!offer.families.some((family) => family.id === rawFeedback.offer.familyId)) holds.push('feedback-family-reference-missing');
    }
  } else {
    warnings.push('No related offer supplied; feedback reference integrity was not independently round-trip checked.');
  }
  if (!rawFeedback.truthBoundary || !rawFeedback.truthBoundary.authority) {
    warnings.push('Feedback has no explicit truthBoundary.authority text; v0.9 structural validation still passes, but authority intent is less inspectable.');
  }

  const basis = {
    feedbackId: rawFeedback.id || null,
    offer: rawFeedback.offer,
    evaluator: rawFeedback.evaluator,
    holds
  };
  const status = holds.length ? 'HOLD' : 'PASS';
  return {
    format: RECEIPT_FORMAT,
    version: VERSION,
    id: receiptId('feedback', basis),
    checkedAt: source.checkedAt || null,
    inputKind: 'feedback',
    status,
    truthStatus: status === 'PASS' ? 'PASS_MATERIAL_FEEDBACK_CONFORMANCE' : 'HOLD_MATERIAL_FEEDBACK_CONFORMANCE',
    feedback: {
      id: rawFeedback.id || null,
      offerId: rawFeedback.offer.id,
      offerFingerprint: rawFeedback.offer.fingerprint,
      familyId: rawFeedback.offer.familyId,
      evaluator: clone(rawFeedback.evaluator)
    },
    relatedOffer,
    holds,
    warnings,
    truthBoundary: {
      conformance: 'Feedback PASS verifies the v0.9 feedback structure and, when an offer is supplied, exact offer/family/fingerprint references.',
      evidence: 'Feedback evaluation content remains bounded receiver evidence; this verifier does not upgrade it into physical or aesthetic truth.',
      authority: 'Feedback is evidence, not producer canonical authority, and conformance never applies it automatically.'
    }
  };
}

module.exports = {
  VERSION,
  RECEIPT_FORMAT,
  FIXED_PROJECTION_TIME,
  clone,
  sha256Bytes,
  sha256Text,
  canonicalMime,
  parseImageDataUrl,
  signatureMatches,
  verifyEntry,
  verificationMap,
  conformOffer,
  buildFamilyProjection,
  conformFeedback
};
