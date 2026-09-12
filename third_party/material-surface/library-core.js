(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMMaterialLibraryCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = '0.4.0';
  const LIBRARY_FORMAT = 'axm-material-library';
  const DONOR_FORMAT = 'axm-material-donor-pack';
  const DONOR_VERSION = '0.2.0';
  const CHANNELS = [
    'base-color','normal','roughness','metallic','ambient-occlusion','height','displacement',
    'emissive','opacity','color-mask','decal','microdetail','unassigned'
  ];

  function clone(value) { return JSON.parse(JSON.stringify(value)); }

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

  function fnv1aText(text) {
    const input = String(text == null ? '' : text);
    let hash = 0x811c9dc5;
    for (let i = 0; i < input.length; i += 1) {
      const code = input.charCodeAt(i);
      hash ^= code & 0xff;
      hash = Math.imul(hash, 0x01000193);
      hash ^= (code >>> 8) & 0xff;
      hash = Math.imul(hash, 0x01000193);
    }
    return (`00000000${(hash >>> 0).toString(16)}`).slice(-8);
  }

  function text(value, fallback) {
    const out = String(value == null ? '' : value).trim();
    return out || fallback || '';
  }

  function sanitizeChannel(value) {
    const normalized = text(value, 'unassigned').toLowerCase().replace(/_/g, '-');
    return CHANNELS.includes(normalized) ? normalized : 'unassigned';
  }

  function suggestChannel(raw) {
    const kind = text(raw && raw.kind).toLowerCase();
    const name = text(raw && raw.name).toLowerCase();
    const haystack = `${kind} ${name}`;
    if (/normal|nrm/.test(haystack)) return 'normal';
    if (/rough/.test(haystack)) return 'roughness';
    if (/metallic/.test(haystack)) return 'metallic';
    if (/ambient|\bao\b/.test(haystack)) return 'ambient-occlusion';
    if (/height/.test(haystack)) return 'height';
    if (/displace/.test(haystack)) return 'displacement';
    if (/emiss/.test(haystack)) return 'emissive';
    if (/opacity|alpha/.test(haystack)) return 'opacity';
    if (/mask/.test(haystack)) return 'color-mask';
    if (/decal|label|sign|overlay|scratch|grime|wear|dirt|rust/.test(haystack)) return 'decal';
    if (/micro|detail/.test(haystack)) return 'microdetail';
    if (kind === 'texture' || /base|albedo|diffuse|paint/.test(haystack)) return 'base-color';
    return 'unassigned';
  }

  function payloadDescriptor(dataUrl) {
    if (typeof dataUrl !== 'string' || !dataUrl) return { portable: false, length: 0, hash: null };
    return { portable: true, length: dataUrl.length, hash: fnv1aText(dataUrl) };
  }

  function stableEntryId(raw) {
    const descriptor = payloadDescriptor(raw && raw.dataUrl);
    const basis = {
      mime: text(raw && raw.mime, 'application/octet-stream').toLowerCase(),
      width: Number(raw && raw.width) || 0,
      height: Number(raw && raw.height) || 0,
      payloadHash: descriptor.hash,
      fallbackName: descriptor.hash ? null : text(raw && raw.name, 'unnamed')
    };
    return `material-${fnv1aText(stableStringify(basis))}`;
  }

  function normalizeEntry(raw, now) {
    if (!raw || typeof raw !== 'object') throw new TypeError('Material library entry must be an object.');
    const descriptor = payloadDescriptor(raw.dataUrl);
    const suggested = suggestChannel(raw);
    const channel = sanitizeChannel(raw.usage && raw.usage.channelHint || raw.channelHint || suggested);
    const basis = raw.usage && raw.usage.channelBasis || (channel === suggested ? 'workspace-kind-or-name-hint' : 'operator-declared');
    return {
      id: text(raw.libraryId || raw.id) || stableEntryId(raw),
      name: text(raw.name, 'unnamed-material'),
      kind: text(raw.kind, 'texture'),
      mime: text(raw.mime, 'application/octet-stream').toLowerCase(),
      width: Number(raw.width) || 0,
      height: Number(raw.height) || 0,
      bytes: Number.isFinite(Number(raw.bytes)) ? Number(raw.bytes) : null,
      dataUrl: typeof raw.dataUrl === 'string' ? raw.dataUrl : null,
      payload: descriptor,
      source: clone(raw.source || { method: 'unknown' }),
      usage: {
        channelHint: channel,
        channelBasis: text(basis, 'operator-declared'),
        note: text(raw.usage && raw.usage.note, '')
      },
      tags: Array.isArray(raw.tags) ? [...new Set(raw.tags.map((item) => text(item)).filter(Boolean))].sort() : [],
      addedAt: text(raw.addedAt || raw.importedAt, now),
      updatedAt: text(raw.updatedAt, now)
    };
  }

  function createLibrary(now) {
    const at = text(now, new Date().toISOString());
    return {
      format: LIBRARY_FORMAT,
      version: VERSION,
      id: `library-${fnv1aText(at)}`,
      createdAt: at,
      updatedAt: at,
      entries: [],
      families: [],
      truthBoundary: {
        channelHints: 'Hints are operator-editable routing metadata, not physical-material recognition.',
        bytes: 'Portable entries preserve local image data URLs when available.',
        semantics: 'Names, tags and families aid reuse but do not prove material physics or artistic quality.'
      }
    };
  }

  function validateLibrary(value) {
    if (!value || typeof value !== 'object') return { ok: false, reason: 'Library must be an object.' };
    if (value.format !== LIBRARY_FORMAT) return { ok: false, reason: 'Not an AXM material library.' };
    if (!Array.isArray(value.entries) || !Array.isArray(value.families)) return { ok: false, reason: 'Library entries/families are missing.' };
    return { ok: true };
  }

  function upsertEntries(library, rawEntries, now) {
    const validation = validateLibrary(library);
    if (!validation.ok) throw new TypeError(validation.reason);
    if (!Array.isArray(rawEntries)) throw new TypeError('Material entries must be an array.');
    const at = text(now, new Date().toISOString());
    const byId = new Map(library.entries.map((entry) => [entry.id, clone(entry)]));
    const added = [];
    const updated = [];
    rawEntries.forEach((raw) => {
      const normalized = normalizeEntry(raw, at);
      const existing = byId.get(normalized.id);
      if (existing) {
        normalized.addedAt = existing.addedAt || normalized.addedAt;
        normalized.updatedAt = at;
        byId.set(normalized.id, normalized);
        updated.push(normalized.id);
      } else {
        byId.set(normalized.id, normalized);
        added.push(normalized.id);
      }
    });
    library.entries = [...byId.values()].sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
    library.updatedAt = at;
    return { added, updated, total: library.entries.length };
  }

  function setEntryChannel(library, entryId, channel, now) {
    const entry = library.entries.find((item) => item.id === entryId);
    if (!entry) throw new TypeError(`Unknown material entry: ${entryId}`);
    entry.usage = entry.usage || {};
    entry.usage.channelHint = sanitizeChannel(channel);
    entry.usage.channelBasis = 'operator-declared';
    entry.updatedAt = text(now, new Date().toISOString());
    library.updatedAt = entry.updatedAt;
    return clone(entry);
  }

  function createFamily(library, raw, now) {
    if (!raw || typeof raw !== 'object') throw new TypeError('Family input must be an object.');
    const name = text(raw.name);
    if (!name) throw new TypeError('Material family name is required.');
    const entryIds = [...new Set((raw.entryIds || []).map((item) => text(item)).filter(Boolean))].sort();
    if (!entryIds.length) throw new TypeError('Material family requires at least one entry.');
    const known = new Set(library.entries.map((entry) => entry.id));
    const missing = entryIds.filter((id) => !known.has(id));
    if (missing.length) throw new TypeError(`Material family references unknown entries: ${missing.join(', ')}`);
    const at = text(now, new Date().toISOString());
    const id = text(raw.id) || `family-${fnv1aText(stableStringify({ name, entryIds }))}`;
    const family = {
      id,
      name,
      purpose: text(raw.purpose, ''),
      entryIds,
      tags: Array.isArray(raw.tags) ? [...new Set(raw.tags.map((item) => text(item)).filter(Boolean))].sort() : [],
      createdAt: text(raw.createdAt, at),
      updatedAt: at
    };
    library.families = library.families.filter((item) => item.id !== id);
    library.families.push(family);
    library.families.sort((a, b) => a.name.localeCompare(b.name) || a.id.localeCompare(b.id));
    library.updatedAt = at;
    return clone(family);
  }

  function removeEntry(library, entryId, now) {
    const before = library.entries.length;
    library.entries = library.entries.filter((entry) => entry.id !== entryId);
    library.families = library.families.map((family) => Object.assign({}, family, {
      entryIds: family.entryIds.filter((id) => id !== entryId),
      updatedAt: text(now, new Date().toISOString())
    })).filter((family) => family.entryIds.length);
    library.updatedAt = text(now, new Date().toISOString());
    return before !== library.entries.length;
  }

  function compactExperiment(experiment) {
    if (!experiment || typeof experiment !== 'object') return null;
    return {
      format: experiment.format || null,
      version: experiment.version || null,
      id: experiment.id || null,
      captures: Array.isArray(experiment.captures) ? experiment.captures.map((capture) => ({
        id: capture.id,
        label: capture.label,
        parentTraceId: capture.parentTraceId || null,
        declaredAction: capture.declaredAction || null,
        declaredParams: capture.declaredParams || null,
        buildHash: capture.topState && capture.topState.buildHash || null,
        pixelHash: capture.pixelState && capture.pixelState.pixelHash || null,
        fileHash: capture.fileState && capture.fileState.byteHash || null
      })) : [],
      transitions: Array.isArray(experiment.transitions) ? experiment.transitions.map((transition) => ({
        id: transition.id,
        fromTraceId: transition.fromTraceId,
        toTraceId: transition.toTraceId,
        declaredAction: transition.declaredAction || null,
        declaredParams: transition.declaredParams || null,
        observed: transition.observed ? {
          buildChangedPaths: transition.observed.build && transition.observed.build.count || 0,
          changedPixelShare: transition.observed.pixels && transition.observed.pixels.spatial && transition.observed.pixels.spatial.changedShare || 0,
          changedBounds: transition.observed.pixels && transition.observed.pixels.spatial && transition.observed.pixels.spatial.changedBounds || null,
          fileChangedPaths: transition.observed.file && transition.observed.file.count || 0
        } : null
      })) : []
    };
  }

  function makeDonorPack(options) {
    const library = options && options.library;
    const validation = validateLibrary(library);
    if (!validation.ok) throw new TypeError(validation.reason);
    const selected = new Set(Array.isArray(options.selectedEntryIds) && options.selectedEntryIds.length ? options.selectedEntryIds : library.entries.map((entry) => entry.id));
    const entries = library.entries.filter((entry) => selected.has(entry.id)).map(clone);
    const entryIds = new Set(entries.map((entry) => entry.id));
    const families = library.families.filter((family) => family.entryIds.some((id) => entryIds.has(id))).map((family) => Object.assign({}, clone(family), {
      entryIds: family.entryIds.filter((id) => entryIds.has(id))
    })).filter((family) => family.entryIds.length);
    const exportedAt = text(options && options.exportedAt, new Date().toISOString());
    const packId = `donor-${fnv1aText(stableStringify({ entries: entries.map((entry) => ({ id: entry.id, payload: entry.payload })), families }))}`;
    return {
      format: DONOR_FORMAT,
      version: DONOR_VERSION,
      id: packId,
      exportedAt,
      purpose: 'Portable reusable material/texture ingredients for explicit downstream AXM adapters.',
      library: {
        sourceFormat: LIBRARY_FORMAT,
        sourceVersion: library.version,
        sourceLibraryId: library.id,
        entries,
        families
      },
      assets: entries.map((entry) => ({
        id: entry.id,
        name: entry.name,
        kind: entry.kind,
        mime: entry.mime,
        width: entry.width,
        height: entry.height,
        bytes: entry.bytes,
        source: clone(entry.source),
        dataUrl: entry.dataUrl,
        usage: clone(entry.usage),
        tags: clone(entry.tags)
      })),
      workspace: clone(options && options.workspace || {}),
      layers: clone(options && options.layers || []),
      experiment: compactExperiment(options && options.experiment),
      truthBoundary: {
        provenance: 'Recorded source metadata and exact portable image payloads are preserved when available.',
        routing: 'Channel hints are explicit routing hints, not physical-material recognition.',
        downstream: 'A consumer must validate the pack and state what it did with each entry; export alone does not prove compatibility.'
      }
    };
  }

  function importDonorPack(pack, now) {
    if (!pack || typeof pack !== 'object' || pack.format !== DONOR_FORMAT) throw new TypeError('Not an AXM material donor pack.');
    const rawEntries = pack.library && Array.isArray(pack.library.entries) ? pack.library.entries : Array.isArray(pack.assets) ? pack.assets : null;
    if (!rawEntries) throw new TypeError('Donor pack contains no reusable entries/assets.');
    const at = text(now, new Date().toISOString());
    const entries = rawEntries.map((entry) => normalizeEntry(Object.assign({}, entry, {
      source: Object.assign({}, clone(entry.source || {}), {
        donorPackId: pack.id || null,
        donorPackVersion: pack.version || null,
        donorExportedAt: pack.exportedAt || null
      })
    }), at));
    const known = new Set(entries.map((entry) => entry.id));
    const families = pack.library && Array.isArray(pack.library.families) ? pack.library.families.map((family) => ({
      id: text(family.id) || `family-${fnv1aText(stableStringify(family))}`,
      name: text(family.name, 'imported-family'),
      purpose: text(family.purpose, ''),
      entryIds: [...new Set((family.entryIds || []).filter((id) => known.has(id)))].sort(),
      tags: Array.isArray(family.tags) ? [...new Set(family.tags.map((tag) => text(tag)).filter(Boolean))].sort() : [],
      createdAt: text(family.createdAt, at),
      updatedAt: at
    })).filter((family) => family.entryIds.length) : [];
    return {
      entries,
      families,
      receipt: {
        packId: pack.id || null,
        packVersion: pack.version || null,
        entries: entries.length,
        families: families.length,
        portableEntries: entries.filter((entry) => entry.payload.portable).length
      }
    };
  }

  return {
    VERSION,
    LIBRARY_FORMAT,
    DONOR_FORMAT,
    DONOR_VERSION,
    CHANNELS: CHANNELS.slice(),
    clone,
    stableStringify,
    fnv1aText,
    sanitizeChannel,
    suggestChannel,
    payloadDescriptor,
    stableEntryId,
    normalizeEntry,
    createLibrary,
    validateLibrary,
    upsertEntries,
    setEntryChannel,
    createFamily,
    removeEntry,
    makeDonorPack,
    importDonorPack
  };
});
