(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMPremadeComposerCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = '0.12.0';
  const FORMAT = 'axm-premade-composition';
  const BLEND_MODES = ['normal','multiply','screen','overlay','soft-light','hard-light','lighter','difference'];

  function clone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }
  function clamp(value, min, max) {
    const number = Number(value);
    const safe = Number.isFinite(number) ? number : min;
    return Math.max(min, Math.min(max, safe));
  }
  function stableStringify(value) {
    function normalize(input) {
      if (input === null || typeof input !== 'object') return input;
      if (Array.isArray(input)) return input.map(normalize);
      const output = {};
      Object.keys(input).sort().forEach((key) => { output[key] = normalize(input[key]); });
      return output;
    }
    return JSON.stringify(normalize(value));
  }
  function fnv1a(text) {
    const input = String(text == null ? '' : text);
    let hash = 0x811c9dc5;
    for (let index = 0; index < input.length; index += 1) {
      hash ^= input.charCodeAt(index) & 0xff;
      hash = Math.imul(hash, 0x01000193);
    }
    return (`00000000${(hash >>> 0).toString(16)}`).slice(-8);
  }
  function xorshift(seedText) {
    let state = parseInt(fnv1a(seedText), 16) >>> 0;
    if (!state) state = 0x6d2b79f5;
    return function next() {
      state ^= state << 13;
      state ^= state >>> 17;
      state ^= state << 5;
      return (state >>> 0) / 4294967296;
    };
  }
  function pick(list, rand) {
    if (!list.length) throw new Error('Cannot pick from an empty list.');
    return list[Math.min(list.length - 1, Math.floor(rand() * list.length))];
  }
  function byId(pack, id) {
    return pack && Array.isArray(pack.assets) ? pack.assets.find((asset) => asset.id === id) || null : null;
  }
  function runtimeSize(pack) {
    const dims = pack && pack.binaryPack && pack.binaryPack.runtimeDimensions;
    return Array.isArray(dims) && dims.length === 2 ? [Number(dims[0]) || 512, Number(dims[1]) || 512] : [512, 512];
  }
  function resourcePath(pack, asset) {
    const rootPath = String(pack.rootPath || 'assets/premade/v0.11').replace(/\/$/, '');
    return `${rootPath}/${asset.category}/${asset.file}`;
  }
  function gridCellRect(pack, asset, row, column) {
    if (!asset || !asset.grid) throw new TypeError('gridCellRect requires a grid atlas.');
    const rows = Number(asset.grid.rows);
    const columns = Number(asset.grid.columns);
    if (!Number.isInteger(row) || row < 0 || row >= rows) throw new RangeError(`row must be 0..${rows - 1}`);
    if (!Number.isInteger(column) || column < 0 || column >= columns) throw new RangeError(`column must be 0..${columns - 1}`);
    const [width, height] = runtimeSize(pack);
    const x0 = Math.floor(column * width / columns);
    const x1 = Math.floor((column + 1) * width / columns);
    const y0 = Math.floor(row * height / rows);
    const y1 = Math.floor((row + 1) * height / rows);
    return { x: x0, y: y0, width: x1 - x0, height: y1 - y0, semanticCell: true };
  }
  function normalizedCropRect(pack, crop) {
    const [width, height] = runtimeSize(pack);
    const x = clamp(crop && crop.x, 0, 1);
    const y = clamp(crop && crop.y, 0, 1);
    const w = clamp(crop && crop.width, 0.01, 1 - x);
    const h = clamp(crop && crop.height, 0.01, 1 - y);
    const x0 = Math.floor(x * width);
    const y0 = Math.floor(y * height);
    const x1 = Math.max(x0 + 1, Math.floor((x + w) * width));
    const y1 = Math.max(y0 + 1, Math.floor((y + h) * height));
    return { x: x0, y: y0, width: x1 - x0, height: y1 - y0, semanticCell: false };
  }
  function coarseWindow(asset, rand) {
    const divisions = asset.kind === 'fx-atlas' ? 6 : asset.kind === 'decal-atlas' ? 4 : 4;
    const row = Math.floor(rand() * divisions);
    const column = Math.floor(rand() * divisions);
    return {
      x: column / divisions,
      y: row / divisions,
      width: 1 / divisions,
      height: 1 / divisions,
      samplingGrid: `${divisions}x${divisions}`
    };
  }
  function normalizeBlend(value) {
    const mode = String(value || 'normal').toLowerCase();
    return BLEND_MODES.includes(mode) ? mode : 'normal';
  }
  function normalizeLayer(raw, index, pack) {
    const source = raw || {};
    const transform = source.transform || {};
    const assetId = String(source.assetId || '');
    const asset = byId(pack, assetId);
    if (!asset) throw new TypeError(`Unknown premade asset: ${assetId}`);
    let cell = null;
    let crop = null;
    if (asset.grid) {
      const row = Number.isInteger(source.cell && source.cell.row) ? source.cell.row : 0;
      const column = Number.isInteger(source.cell && source.cell.column) ? source.cell.column : 0;
      gridCellRect(pack, asset, row, column);
      cell = { row, column };
    } else if (source.crop) {
      crop = {
        x: clamp(source.crop.x, 0, 1),
        y: clamp(source.crop.y, 0, 1),
        width: clamp(source.crop.width, 0.01, 1),
        height: clamp(source.crop.height, 0.01, 1),
        samplingGrid: source.crop.samplingGrid || null
      };
      normalizedCropRect(pack, crop);
    }
    return {
      id: String(source.id || `layer-${index + 1}-${fnv1a(`${assetId}|${index}`)}`),
      name: String(source.name || assetId),
      assetId,
      cell,
      crop,
      visible: source.visible !== false,
      opacity: clamp(source.opacity == null ? 1 : source.opacity, 0, 1),
      blendMode: normalizeBlend(source.blendMode),
      transform: {
        x: clamp(transform.x == null ? 0.5 : transform.x, -2, 3),
        y: clamp(transform.y == null ? 0.5 : transform.y, -2, 3),
        width: clamp(transform.width == null ? 0.75 : transform.width, 0.02, 4),
        height: clamp(transform.height == null ? 0.75 : transform.height, 0.02, 4),
        rotation: clamp(transform.rotation || 0, -3600, 3600),
        mirrorX: Boolean(transform.mirrorX),
        mirrorY: Boolean(transform.mirrorY)
      },
      provenance: clone(source.provenance || {})
    };
  }
  function createRecipe(name, seed) {
    const label = String(name || 'premade composition').trim() || 'premade composition';
    const seedText = String(seed == null ? '0' : seed);
    return {
      format: FORMAT,
      version: VERSION,
      id: `premade-${fnv1a(`${label}|${seedText}`)}`,
      name: label,
      seed: seedText,
      canvas: { width: 1024, height: 1024, transparent: true },
      layers: [],
      notes: '',
      truthBoundary: {
        alpha: 'Composition preserves source alpha and transparent output unless the caller deliberately changes it.',
        segmentation: 'Non-grid atlas crops are deterministic sampling windows, not semantic object segmentation.',
        physical: 'Generated ingredients and their composition are visual state, not measured material physics.',
        authority: 'Seeded generation proposes a composition; it does not auto-promote or rewrite canonical material state.'
      }
    };
  }
  function validateRecipe(recipe, pack) {
    try {
      if (!recipe || recipe.format !== FORMAT || recipe.version !== VERSION) return { ok: false, reason: `Expected ${FORMAT}/${VERSION}.` };
      if (!recipe.canvas || recipe.canvas.transparent !== true) return { ok: false, reason: 'v0.12 premade compositions require transparent output state.' };
      if (!Array.isArray(recipe.layers)) return { ok: false, reason: 'layers must be an array.' };
      recipe.layers.forEach((layer, index) => normalizeLayer(layer, index, pack));
      return { ok: true };
    } catch (error) {
      return { ok: false, reason: error && error.message ? error.message : String(error) };
    }
  }
  function sourceRectForLayer(pack, asset, layer) {
    if (asset.grid) return gridCellRect(pack, asset, layer.cell.row, layer.cell.column);
    if (layer.crop) return normalizedCropRect(pack, layer.crop);
    const [width, height] = runtimeSize(pack);
    return { x: 0, y: 0, width, height, semanticCell: false };
  }
  function compilePlan(rawRecipe, pack) {
    const validation = validateRecipe(rawRecipe, pack);
    if (!validation.ok) throw new TypeError(validation.reason);
    const recipe = clone(rawRecipe);
    const layers = recipe.layers.map((raw, index) => {
      const layer = normalizeLayer(raw, index, pack);
      const asset = byId(pack, layer.assetId);
      return Object.assign(layer, {
        assetKind: asset.kind,
        category: asset.category,
        tags: clone(asset.tags || []),
        resourcePath: resourcePath(pack, asset),
        sourceRect: sourceRectForLayer(pack, asset, layer)
      });
    });
    const basis = {
      format: recipe.format,
      version: recipe.version,
      seed: recipe.seed,
      canvas: recipe.canvas,
      layers: layers.map((layer) => ({
        assetId: layer.assetId,
        cell: layer.cell,
        crop: layer.crop,
        visible: layer.visible,
        opacity: layer.opacity,
        blendMode: layer.blendMode,
        transform: layer.transform
      }))
    };
    return {
      format: 'axm-premade-render-plan',
      version: VERSION,
      recipeId: recipe.id,
      recipeFingerprint: fnv1a(stableStringify(basis)),
      canvas: clone(recipe.canvas),
      pack: { format: pack.format, version: pack.version, archiveSha256: pack.binaryPack && pack.binaryPack.sha256 || null },
      layers,
      truthBoundary: clone(recipe.truthBoundary)
    };
  }
  function seededRecipe(seed, pack, options) {
    const settings = Object.assign({ overlayCount: 3, includeFx: true, includeDecals: true, basePool: 'mixed' }, options || {});
    const rand = xorshift(String(seed));
    const recipe = createRecipe(`seed ${seed}`, seed);
    const globes = pack.assets.filter((asset) => asset.kind === 'globe-atlas');
    let baseChoices = globes;
    if (settings.basePool && settings.basePool !== 'mixed') {
      const filtered = globes.filter((asset) => asset.category.endsWith(`/${settings.basePool}`));
      if (filtered.length) baseChoices = filtered;
    }
    const base = pick(baseChoices, rand);
    const baseRow = Math.floor(rand() * base.grid.rows);
    const baseColumn = Math.floor(rand() * base.grid.columns);
    recipe.layers.push(normalizeLayer({
      id: 'base-globe', name: `${base.id} ${baseRow}:${baseColumn}`, assetId: base.id,
      cell: { row: baseRow, column: baseColumn }, blendMode: 'normal', opacity: 1,
      transform: { x: 0.5, y: 0.5, width: 0.78, height: 0.78, rotation: 0 },
      provenance: { rule: 'seeded-base-globe' }
    }, 0, pack));

    const candidates = pack.assets.filter((asset) => {
      if (asset.kind === 'overlay-atlas') return true;
      if (asset.kind === 'decal-atlas') return settings.includeDecals;
      if (asset.kind === 'fx-atlas') return settings.includeFx;
      return false;
    });
    const used = new Set();
    const count = Math.max(0, Math.min(8, Number(settings.overlayCount) || 0));
    for (let index = 0; index < count && candidates.length; index += 1) {
      let asset = pick(candidates, rand);
      for (let retry = 0; retry < 8 && used.has(asset.id) && used.size < candidates.length; retry += 1) asset = pick(candidates, rand);
      used.add(asset.id);
      const crop = coarseWindow(asset, rand);
      const fx = asset.kind === 'fx-atlas';
      const blendChoices = fx ? ['screen','lighter'] : asset.kind === 'decal-atlas' ? ['normal','overlay'] : ['overlay','multiply','soft-light','screen'];
      recipe.layers.push(normalizeLayer({
        id: `seed-layer-${index + 1}`, name: asset.id, assetId: asset.id, crop,
        blendMode: pick(blendChoices, rand), opacity: fx ? 0.35 + rand() * 0.5 : 0.2 + rand() * 0.55,
        transform: {
          x: 0.35 + rand() * 0.3,
          y: 0.35 + rand() * 0.3,
          width: 0.5 + rand() * 0.65,
          height: 0.5 + rand() * 0.65,
          rotation: -35 + rand() * 70,
          mirrorX: rand() > 0.7,
          mirrorY: rand() > 0.85
        },
        provenance: { rule: 'seeded-coarse-atlas-window', semanticSegmentationClaim: false }
      }, recipe.layers.length, pack));
    }
    return recipe;
  }
  function recipeFingerprint(recipe, pack) {
    return compilePlan(recipe, pack).recipeFingerprint;
  }

  return {
    VERSION, FORMAT, BLEND_MODES: BLEND_MODES.slice(), clone, clamp, stableStringify, fnv1a, xorshift,
    byId, runtimeSize, resourcePath, gridCellRect, normalizedCropRect, coarseWindow,
    normalizeLayer, createRecipe, validateRecipe, compilePlan, seededRecipe, recipeFingerprint
  };
});
