(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMMaterialExchangeCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = '0.9.0';
  const OFFER_FORMAT = 'axm-material-offer';
  const FEEDBACK_FORMAT = 'axm-material-feedback';
  const CHANNELS = [
    'base-color','normal','roughness','metallic','ambient-occlusion','height','displacement',
    'emissive','opacity','color-mask','decal','microdetail','unassigned'
  ];

  function clone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }

  function stableStringify(value) {
    function normalize(input) {
      if (input === null || typeof input !== 'object') return input;
      if (Array.isArray(input)) return input.map(normalize);
      const out = {};
      Object.keys(input).sort().forEach((key) => { out[key] = normalize(input[key]); });
      return out;
    }
    return JSON.stringify(normalize(value));
  }

  function fnv1a(text) {
    const input = String(text == null ? '' : text);
    let hash = 0x811c9dc5;
    for (let index = 0; index < input.length; index += 1) {
      const code = input.charCodeAt(index);
      hash ^= code & 0xff;
      hash = Math.imul(hash, 0x01000193);
      hash ^= (code >>> 8) & 0xff;
      hash = Math.imul(hash, 0x01000193);
    }
    return (`00000000${(hash >>> 0).toString(16)}`).slice(-8);
  }

  function text(value, fallback) {
    const result = String(value == null ? '' : value).trim();
    return result || String(fallback == null ? '' : fallback);
  }

  function normalizeChannel(value) {
    const normalized = text(value, 'unassigned').toLowerCase().replace(/_/g, '-');
    return CHANNELS.includes(normalized) ? normalized : 'unassigned';
  }

  function isSha256(value) {
    return /^sha256:[0-9a-f]{64}$/i.test(String(value || ''));
  }

  function isImageDataUrl(value) {
    return /^data:image\/(png|jpeg|jpg|webp);base64,/i.test(String(value || ''));
  }

  function normalizeProducer(raw) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const system = text(source.system);
    if (!system) throw new TypeError('Material offer producer.system is required.');
    return {
      system,
      repo: text(source.repo) || null,
      sourceId: text(source.sourceId) || null,
      sourceDigest: text(source.sourceDigest) || null,
      stateKind: text(source.stateKind) || null,
      version: text(source.version) || null,
      adapter: text(source.adapter) || null
    };
  }

  function normalizeEntry(raw) {
    if (!raw || typeof raw !== 'object') throw new TypeError('Material offer entry must be an object.');
    const id = text(raw.id);
    if (!id) throw new TypeError('Material offer entry.id is required.');
    const sha256 = text(raw.sha256) || null;
    if (sha256 && !isSha256(sha256)) throw new TypeError(`Entry ${id} sha256 must use sha256:<64 hex>.`);
    const dataUrl = typeof raw.dataUrl === 'string' && raw.dataUrl ? raw.dataUrl : null;
    if (dataUrl && !isImageDataUrl(dataUrl)) throw new TypeError(`Entry ${id} dataUrl must be a base64 PNG/JPEG/WEBP image data URL.`);
    return {
      id,
      name: text(raw.name, id),
      channel: normalizeChannel(raw.channel || raw.channelHint),
      mime: text(raw.mime, dataUrl && /^data:image\/jpeg/i.test(dataUrl) ? 'image/jpeg' : dataUrl && /^data:image\/webp/i.test(dataUrl) ? 'image/webp' : 'image/png').toLowerCase(),
      width: Math.max(0, Math.round(Number(raw.width) || 0)),
      height: Math.max(0, Math.round(Number(raw.height) || 0)),
      dataUrl,
      sha256,
      source: clone(raw.source || {}),
      tags: Array.isArray(raw.tags) ? [...new Set(raw.tags.map((tag) => text(tag)).filter(Boolean))].sort() : [],
      note: text(raw.note) || null
    };
  }

  function normalizeFamily(raw) {
    if (!raw || typeof raw !== 'object') throw new TypeError('Material offer family must be an object.');
    const id = text(raw.id);
    if (!id) throw new TypeError('Material offer family.id is required.');
    const entryIds = [...new Set((Array.isArray(raw.entryIds) ? raw.entryIds : []).map((value) => text(value)).filter(Boolean))].sort();
    if (!entryIds.length) throw new TypeError(`Material offer family ${id} requires at least one entryId.`);
    return {
      id,
      name: text(raw.name, id),
      purpose: text(raw.purpose) || '',
      entryIds,
      tags: Array.isArray(raw.tags) ? [...new Set(raw.tags.map((tag) => text(tag)).filter(Boolean))].sort() : [],
      source: clone(raw.source || {})
    };
  }

  function validateOffer(raw) {
    try {
      if (!raw || typeof raw !== 'object') return { ok: false, reason: 'Material offer must be an object.' };
      if (raw.format !== OFFER_FORMAT || raw.version !== VERSION) return { ok: false, reason: `Expected ${OFFER_FORMAT}/${VERSION}.` };
      const producer = normalizeProducer(raw.producer);
      void producer;
      if (!Array.isArray(raw.entries) || !raw.entries.length) return { ok: false, reason: 'Material offer requires at least one entry.' };
      if (!Array.isArray(raw.families) || !raw.families.length) return { ok: false, reason: 'Material offer requires at least one family.' };
      const entries = raw.entries.map(normalizeEntry);
      const entryIds = new Set();
      for (const entry of entries) {
        if (entryIds.has(entry.id)) return { ok: false, reason: `Duplicate material offer entry id: ${entry.id}` };
        entryIds.add(entry.id);
      }
      const familyIds = new Set();
      const families = raw.families.map(normalizeFamily);
      for (const family of families) {
        if (familyIds.has(family.id)) return { ok: false, reason: `Duplicate material offer family id: ${family.id}` };
        familyIds.add(family.id);
        const missing = family.entryIds.filter((entryId) => !entryIds.has(entryId));
        if (missing.length) return { ok: false, reason: `Material offer family ${family.id} references missing entries: ${missing.join(', ')}` };
      }
      return { ok: true };
    } catch (error) {
      return { ok: false, reason: error && error.message ? error.message : String(error) };
    }
  }

  function normalizeOffer(raw) {
    const validation = validateOffer(raw);
    if (!validation.ok) throw new TypeError(validation.reason);
    const producer = normalizeProducer(raw.producer);
    const entries = raw.entries.map(normalizeEntry).sort((a, b) => a.id.localeCompare(b.id));
    const families = raw.families.map(normalizeFamily).sort((a, b) => a.id.localeCompare(b.id));
    const createdAt = text(raw.createdAt) || null;
    const identityBasis = {
      producer,
      entries: entries.map((entry) => ({ id: entry.id, channel: entry.channel, sha256: entry.sha256, payloadHash: entry.dataUrl ? fnv1a(entry.dataUrl) : null })),
      families: families.map((family) => ({ id: family.id, entryIds: family.entryIds }))
    };
    return {
      format: OFFER_FORMAT,
      version: VERSION,
      id: text(raw.id) || `offer-${fnv1a(stableStringify(identityBasis))}`,
      createdAt,
      producer,
      entries,
      families,
      evidence: clone(raw.evidence || {}),
      truthBoundary: clone(raw.truthBoundary || {
        producer: 'The producer declares source identity and channel meaning; this receiver does not infer missing semantics from appearance.',
        payload: 'Portable image bytes can be verified independently when a SHA-256 is supplied.',
        quality: 'An offer is an interchange claim, not aesthetic quality or physical-material certification.'
      })
    };
  }

  function offerFingerprint(raw) {
    const offer = normalizeOffer(raw);
    return fnv1a(stableStringify({
      format: offer.format,
      version: offer.version,
      id: offer.id,
      producer: offer.producer,
      entries: offer.entries.map((entry) => ({ id: entry.id, channel: entry.channel, sha256: entry.sha256, dataUrlHash: entry.dataUrl ? fnv1a(entry.dataUrl) : null })),
      families: offer.families
    }));
  }

  function classifyEntry(entry, verification) {
    const row = normalizeEntry(entry);
    const observed = verification && verification[row.id] || null;
    if (!row.dataUrl) return { entryId: row.id, state: 'hold', reason: 'no-portable-payload', hashVerification: row.sha256 ? 'not-verifiable-without-payload' : 'not-provided' };
    if (row.sha256 && observed && observed.sha256Match === false) return { entryId: row.id, state: 'hold', reason: 'sha256-mismatch', hashVerification: 'mismatch' };
    if (row.sha256 && observed && observed.sha256Match === true) return { entryId: row.id, state: 'portable-verified', reason: null, hashVerification: 'verified' };
    if (row.sha256) return { entryId: row.id, state: 'portable-unverified', reason: 'sha256-not-yet-verified', hashVerification: 'pending' };
    return { entryId: row.id, state: 'portable-unhashed', reason: null, hashVerification: 'not-provided' };
  }

  function intakePlan(rawOffer, verification) {
    const offer = normalizeOffer(rawOffer);
    const states = offer.entries.map((entry) => classifyEntry(entry, verification));
    const byId = new Map(states.map((state) => [state.entryId, state]));
    const families = offer.families.map((family) => {
      const entryStates = family.entryIds.map((id) => byId.get(id));
      const holds = entryStates.filter((state) => state.state === 'hold').length;
      const pending = entryStates.filter((state) => state.state === 'portable-unverified').length;
      return {
        id: family.id,
        name: family.name,
        entries: family.entryIds.length,
        holds,
        pending,
        portable: family.entryIds.length - holds,
        state: holds ? 'partial-hold' : pending ? 'portable-awaiting-verification' : 'portable'
      };
    });
    return {
      offerId: offer.id,
      offerFingerprint: offerFingerprint(offer),
      producer: clone(offer.producer),
      entries: states,
      families,
      summary: {
        entries: states.length,
        portable: states.filter((state) => state.state !== 'hold').length,
        verified: states.filter((state) => state.state === 'portable-verified').length,
        pending: states.filter((state) => state.state === 'portable-unverified').length,
        held: states.filter((state) => state.state === 'hold').length,
        families: families.length,
        readyFamilies: families.filter((family) => family.state === 'portable').length
      }
    };
  }

  function familyById(rawOffer, familyId) {
    const offer = normalizeOffer(rawOffer);
    return offer.families.find((family) => family.id === familyId) || null;
  }

  function familyEntries(rawOffer, familyId) {
    const offer = normalizeOffer(rawOffer);
    const family = offer.families.find((item) => item.id === familyId);
    if (!family) throw new TypeError(`Unknown offer family: ${familyId}`);
    const ids = new Set(family.entryIds);
    return offer.entries.filter((entry) => ids.has(entry.id));
  }

  function libraryEntryId(rawOffer, entryId) {
    const offer = normalizeOffer(rawOffer);
    const entry = offer.entries.find((item) => item.id === entryId);
    if (!entry) throw new TypeError(`Unknown offer entry: ${entryId}`);
    return `material-xchg-${fnv1a(`${offerFingerprint(offer)}|${entry.id}`)}`;
  }

  function libraryFamilyId(rawOffer, familyId) {
    const offer = normalizeOffer(rawOffer);
    const family = offer.families.find((item) => item.id === familyId);
    if (!family) throw new TypeError(`Unknown offer family: ${familyId}`);
    return `family-xchg-${fnv1a(`${offerFingerprint(offer)}|${family.id}`)}`;
  }

  function toLibraryBundle(rawOffer, familyId, verification, at) {
    const offer = normalizeOffer(rawOffer);
    const family = offer.families.find((item) => item.id === familyId);
    if (!family) throw new TypeError(`Unknown offer family: ${familyId}`);
    const entries = familyEntries(offer, familyId).map((entry) => {
      const state = classifyEntry(entry, verification);
      return {
        libraryId: libraryEntryId(offer, entry.id),
        name: entry.name,
        kind: entry.channel,
        mime: entry.mime,
        width: entry.width,
        height: entry.height,
        bytes: null,
        dataUrl: entry.dataUrl,
        source: Object.assign({}, clone(entry.source || {}), {
          method: 'axm-cross-machine-material-exchange',
          exchangeVersion: VERSION,
          offerId: offer.id,
          offerFingerprint: offerFingerprint(offer),
          producer: clone(offer.producer),
          producerEntryId: entry.id,
          declaredSha256: entry.sha256,
          receiverState: state.state,
          receiverHashVerification: state.hashVerification
        }),
        usage: {
          channelHint: entry.channel,
          channelBasis: 'producer-declared-v0.9-material-offer',
          note: entry.note || 'Channel meaning was explicitly declared by the producing system.'
        },
        tags: [...new Set([...(entry.tags || []), 'axm-material-exchange', `v${VERSION}`, `producer:${offer.producer.system}`, `offer:${offer.id}`])].sort(),
        addedAt: at || null,
        updatedAt: at || null
      };
    });
    return {
      entries,
      family: {
        id: libraryFamilyId(offer, family.id),
        name: family.name,
        purpose: family.purpose || `Cross-machine material family offered by ${offer.producer.system}.`,
        entryIds: entries.map((entry) => entry.libraryId).sort(),
        tags: [...new Set([...(family.tags || []), 'axm-material-exchange', `v${VERSION}`, `producer:${offer.producer.system}`, `offer:${offer.id}`])].sort(),
        createdAt: at || null,
        updatedAt: at || null,
        exchange: {
          offerId: offer.id,
          offerFingerprint: offerFingerprint(offer),
          producerFamilyId: family.id,
          producer: clone(offer.producer)
        }
      },
      intake: intakePlan(offer, verification)
    };
  }

  function summarizeEvaluationSession(session) {
    if (!session || typeof session !== 'object') return null;
    const candidates = Array.isArray(session.candidates) ? session.candidates : [];
    return {
      format: session.format || null,
      version: session.version || null,
      id: session.id || null,
      source: clone(session.source || {}),
      mode: session.mode || null,
      resolution: Number(session.resolution) || null,
      geometries: clone(session.geometries || []),
      lightRigIds: clone(session.lightRigIds || []),
      selectedCandidateId: session.selectedCandidateId || null,
      candidates: candidates.map((candidate) => ({
        id: candidate.id,
        name: candidate.name,
        rank: candidate.rank || null,
        descriptorHash: candidate.descriptorHash || null,
        sourceKind: candidate.run && candidate.run.sourceKind || null,
        technicalScore: candidate.run && candidate.run.technicalScore,
        minimumTechnicalScore: candidate.run && candidate.run.minimumTechnicalScore,
        completionShare: candidate.run && candidate.run.completionShare,
        holds: candidate.run && candidate.run.holds,
        observationCount: candidate.run && candidate.run.observationCount,
        uniqueFramebufferHashes: candidate.run && candidate.run.uniqueFramebufferHashes,
        scoreBoundary: candidate.run && candidate.run.scoreBoundary || null
      })),
      truthBoundary: clone(session.truthBoundary || {})
    };
  }

  function makeFeedback(options) {
    const source = options || {};
    const offer = normalizeOffer(source.offer);
    const family = offer.families.find((item) => item.id === source.familyId);
    if (!family) throw new TypeError(`Unknown offer family: ${source.familyId}`);
    const evaluation = summarizeEvaluationSession(source.evaluationSession);
    const createdAt = text(source.createdAt) || null;
    const basis = {
      offerId: offer.id,
      offerFingerprint: offerFingerprint(offer),
      familyId: family.id,
      evaluationId: evaluation && evaluation.id,
      installReceipt: source.installReceipt || null
    };
    return {
      format: FEEDBACK_FORMAT,
      version: VERSION,
      id: `feedback-${fnv1a(stableStringify(basis))}`,
      createdAt,
      offer: {
        id: offer.id,
        fingerprint: offerFingerprint(offer),
        familyId: family.id,
        producer: clone(offer.producer)
      },
      evaluator: {
        system: 'axm-material-surface-fabric',
        version: VERSION,
        evaluationFormat: evaluation && evaluation.format,
        evaluationVersion: evaluation && evaluation.version
      },
      verification: clone(source.verification || {}),
      evaluation,
      installReceipt: clone(source.installReceipt || null),
      notes: text(source.notes) || null,
      truthBoundary: {
        evidence: 'Feedback reports receiver-side payload verification and bounded local renderer-path evidence only.',
        ranking: 'Technical renderer health is not beauty, realism, PBR correctness, physical truth, taste, or universal material quality.',
        authority: 'Feedback never grants automatic promotion authority to the producer or receiver; installation/adoption stays explicit in each machine.',
        source: 'Producer source identity remains separate from receiver observations and is not rewritten by feedback.'
      }
    };
  }

  function validateFeedback(raw) {
    if (!raw || typeof raw !== 'object') return { ok: false, reason: 'Material feedback must be an object.' };
    if (raw.format !== FEEDBACK_FORMAT || raw.version !== VERSION) return { ok: false, reason: `Expected ${FEEDBACK_FORMAT}/${VERSION}.` };
    if (!raw.offer || !text(raw.offer.id) || !text(raw.offer.familyId) || !text(raw.offer.fingerprint)) return { ok: false, reason: 'Material feedback offer reference is incomplete.' };
    if (!raw.evaluator || text(raw.evaluator.system) !== 'axm-material-surface-fabric') return { ok: false, reason: 'Material feedback evaluator identity is invalid.' };
    return { ok: true };
  }

  return {
    VERSION,
    OFFER_FORMAT,
    FEEDBACK_FORMAT,
    CHANNELS: CHANNELS.slice(),
    clone,
    stableStringify,
    fnv1a,
    text,
    normalizeChannel,
    isSha256,
    isImageDataUrl,
    normalizeProducer,
    normalizeEntry,
    normalizeFamily,
    validateOffer,
    normalizeOffer,
    offerFingerprint,
    classifyEntry,
    intakePlan,
    familyById,
    familyEntries,
    libraryEntryId,
    libraryFamilyId,
    toLibraryBundle,
    summarizeEvaluationSession,
    makeFeedback,
    validateFeedback
  };
});
