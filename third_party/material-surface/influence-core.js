(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMMaterialInfluenceCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = '0.5.0';
  const FORMAT = 'axm-material-influence-workspace';
  const CHANNELS = [
    'base-color','normal','roughness','metallic','ambient-occlusion','height','displacement',
    'emissive','opacity','color-mask','decal','microdetail','unassigned'
  ];
  const BLEND_MODES = ['normal','multiply','screen','overlay','soft-light','hard-light','add','subtract'];
  const VIEW_RIGS = [
    { id: 'flat', name: 'Flat inspection', mode: 'flat', truth: '2D flat material preview' },
    { id: 'tile-2x2', name: '2×2 tiling check', mode: 'tile-2x2', truth: '2D repetition preview' },
    { id: 'micro-close', name: 'Micro close-up', mode: 'micro-close', truth: 'center crop magnification' },
    { id: 'grazing-proxy', name: 'Grazing-angle proxy', mode: 'grazing-proxy', truth: '2D compressed proxy; not a 3D camera proof' }
  ];
  const LIGHT_RIGS = [
    { id: 'neutral-studio', name: 'Neutral studio', angle: 315, intensity: 0.55, ambient: 0.28, color: '#ffffff', shadow: 0.22, environment: 0.18 },
    { id: 'hard-side', name: 'Hard side light', angle: 0, intensity: 0.88, ambient: 0.10, color: '#ffffff', shadow: 0.52, environment: 0.08 },
    { id: 'warm-top', name: 'Warm top light', angle: 270, intensity: 0.70, ambient: 0.20, color: '#ffd39a', shadow: 0.34, environment: 0.12 },
    { id: 'cold-scifi', name: 'Cold sci-fi', angle: 30, intensity: 0.76, ambient: 0.16, color: '#80cfff', shadow: 0.42, environment: 0.22 },
    { id: 'dark-emissive', name: 'Dark emissive room', angle: 300, intensity: 0.16, ambient: 0.03, color: '#8aa7ff', shadow: 0.58, environment: 0.03 },
    { id: 'outdoor-day', name: 'Outdoor daylight proxy', angle: 300, intensity: 0.64, ambient: 0.42, color: '#e7f2ff', shadow: 0.18, environment: 0.36 },
    { id: 'showroom', name: 'Gloss showroom proxy', angle: 335, intensity: 0.82, ambient: 0.30, color: '#ffffff', shadow: 0.18, environment: 0.48 },
    { id: 'red-alert', name: 'Red alert', angle: 20, intensity: 0.72, ambient: 0.08, color: '#ff524a', shadow: 0.48, environment: 0.10 }
  ];
  const SHADER_DEFAULTS = {
    exposure: 1,
    saturation: 1,
    clearcoatLike: { enabled: false, strength: 0.35 },
    fresnelLike: { enabled: false, strength: 0.25 },
    emissiveBoost: { enabled: true, strength: 1 },
    roughnessResponse: { enabled: false, value: 0.5 }
  };

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function nowText(value) { return String(value || new Date().toISOString()); }
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
      const code = input.charCodeAt(index);
      hash ^= code & 0xff;
      hash = Math.imul(hash, 0x01000193);
      hash ^= (code >>> 8) & 0xff;
      hash = Math.imul(hash, 0x01000193);
    }
    return (`00000000${(hash >>> 0).toString(16)}`).slice(-8);
  }
  function number(value, fallback, min, max) {
    const parsed = Number(value);
    const base = Number.isFinite(parsed) ? parsed : fallback;
    return Math.max(min, Math.min(max, base));
  }
  function channel(value) {
    const normalized = String(value || 'unassigned').trim().toLowerCase().replace(/_/g, '-');
    return CHANNELS.includes(normalized) ? normalized : 'unassigned';
  }
  function blendMode(value) {
    const normalized = String(value || 'normal').trim().toLowerCase();
    return BLEND_MODES.includes(normalized) ? normalized : 'normal';
  }

  function normalizeLayer(raw, index) {
    const source = raw || {};
    const id = String(source.id || `layer-${index + 1}-${fnv1a(stableStringify({ entryId: source.entryId || '', index }))}`);
    return {
      id,
      entryId: String(source.entryId || ''),
      role: String(source.role || 'surface-layer'),
      targetChannel: channel(source.targetChannel),
      blendMode: blendMode(source.blendMode),
      opacity: number(source.opacity, 1, 0, 1),
      visible: source.visible !== false,
      maskEntryId: source.maskEntryId ? String(source.maskEntryId) : null,
      transform: {
        scale: number(source.transform && source.transform.scale, 1, 0.05, 16),
        rotation: number(source.transform && source.transform.rotation, 0, -3600, 3600),
        offsetX: number(source.transform && source.transform.offsetX, 0, -4096, 4096),
        offsetY: number(source.transform && source.transform.offsetY, 0, -4096, 4096)
      },
      tiling: {
        repeatX: number(source.tiling && source.tiling.repeatX, 1, 0.125, 32),
        repeatY: number(source.tiling && source.tiling.repeatY, 1, 0.125, 32)
      },
      note: String(source.note || '')
    };
  }

  function normalizeShader(raw) {
    const source = raw || {};
    function toggle(name, defaults, min, max) {
      const value = source[name] || {};
      return {
        enabled: value.enabled == null ? defaults.enabled : Boolean(value.enabled),
        strength: number(value.strength, defaults.strength, min, max)
      };
    }
    return {
      exposure: number(source.exposure, SHADER_DEFAULTS.exposure, 0.1, 4),
      saturation: number(source.saturation, SHADER_DEFAULTS.saturation, 0, 3),
      clearcoatLike: toggle('clearcoatLike', SHADER_DEFAULTS.clearcoatLike, 0, 1),
      fresnelLike: toggle('fresnelLike', SHADER_DEFAULTS.fresnelLike, 0, 1),
      emissiveBoost: toggle('emissiveBoost', SHADER_DEFAULTS.emissiveBoost, 0, 4),
      roughnessResponse: {
        enabled: source.roughnessResponse && source.roughnessResponse.enabled != null ? Boolean(source.roughnessResponse.enabled) : SHADER_DEFAULTS.roughnessResponse.enabled,
        value: number(source.roughnessResponse && source.roughnessResponse.value, SHADER_DEFAULTS.roughnessResponse.value, 0, 1)
      }
    };
  }

  function lightRigById(id) {
    return clone(LIGHT_RIGS.find((item) => item.id === id) || LIGHT_RIGS[0]);
  }
  function viewRigById(id) {
    return clone(VIEW_RIGS.find((item) => item.id === id) || VIEW_RIGS[0]);
  }
  function normalizeLightRig(raw) {
    const preset = lightRigById(raw && raw.id);
    const source = Object.assign({}, preset, raw || {});
    return {
      id: String(source.id || preset.id),
      name: String(source.name || preset.name),
      angle: number(source.angle, preset.angle, -3600, 3600),
      intensity: number(source.intensity, preset.intensity, 0, 2),
      ambient: number(source.ambient, preset.ambient, 0, 1),
      color: /^#[0-9a-f]{6}$/i.test(String(source.color || '')) ? String(source.color).toLowerCase() : preset.color,
      shadow: number(source.shadow, preset.shadow, 0, 1),
      environment: number(source.environment, preset.environment, 0, 1)
    };
  }

  function createRecipe(name, at) {
    const createdAt = nowText(at);
    const label = String(name || 'untitled material recipe').trim() || 'untitled material recipe';
    return {
      id: `recipe-${fnv1a(`${label}|${createdAt}`)}`,
      name: label,
      createdAt,
      updatedAt: createdAt,
      familyIds: [],
      stack: [],
      lightRig: normalizeLightRig(LIGHT_RIGS[0]),
      viewRig: viewRigById('flat'),
      shader: normalizeShader(SHADER_DEFAULTS),
      notes: ''
    };
  }

  function createWorkspace(at) {
    const createdAt = nowText(at);
    const recipe = createRecipe('material recipe 1', createdAt);
    return {
      format: FORMAT,
      version: VERSION,
      id: `influence-${fnv1a(createdAt)}`,
      createdAt,
      updatedAt: createdAt,
      activeRecipeId: recipe.id,
      recipes: [recipe],
      librarySnapshot: { entries: [], families: [], observedAt: null, source: 'none' },
      experiments: [],
      truthBoundary: {
        preview: 'Lighting/view/shader modules are bounded 2D preview influences, not a physically based renderer.',
        routing: 'Channel targets come from explicit recipe/library state; no pixel semantics are silently inferred.',
        causality: 'Recorded controls and observed preview deltas are evidence of this tool path, not universal physical causality.'
      }
    };
  }

  function activeRecipe(workspace) {
    return workspace.recipes.find((recipe) => recipe.id === workspace.activeRecipeId) || workspace.recipes[0] || null;
  }
  function touch(workspace, recipe, at) {
    const stamp = nowText(at);
    workspace.updatedAt = stamp;
    if (recipe) recipe.updatedAt = stamp;
  }
  function addLayer(recipe, raw, at) {
    if (!recipe || !raw || !raw.entryId) throw new TypeError('A recipe and entryId are required.');
    const layer = normalizeLayer(Object.assign({}, raw, { id: raw.id || `layer-${fnv1a(`${raw.entryId}|${recipe.stack.length}|${nowText(at)}`)}` }), recipe.stack.length);
    recipe.stack.push(layer);
    recipe.updatedAt = nowText(at);
    return clone(layer);
  }
  function updateLayer(recipe, layerId, patch, at) {
    const index = recipe.stack.findIndex((layer) => layer.id === layerId);
    if (index < 0) throw new TypeError(`Unknown recipe layer: ${layerId}`);
    const merged = Object.assign({}, recipe.stack[index], clone(patch || {}));
    if (patch && patch.transform) merged.transform = Object.assign({}, recipe.stack[index].transform, patch.transform);
    if (patch && patch.tiling) merged.tiling = Object.assign({}, recipe.stack[index].tiling, patch.tiling);
    recipe.stack[index] = normalizeLayer(merged, index);
    recipe.updatedAt = nowText(at);
    return clone(recipe.stack[index]);
  }
  function moveLayer(recipe, layerId, delta, at) {
    const index = recipe.stack.findIndex((layer) => layer.id === layerId);
    if (index < 0) throw new TypeError(`Unknown recipe layer: ${layerId}`);
    const target = Math.max(0, Math.min(recipe.stack.length - 1, index + Number(delta || 0)));
    if (target === index) return false;
    const [layer] = recipe.stack.splice(index, 1);
    recipe.stack.splice(target, 0, layer);
    recipe.updatedAt = nowText(at);
    return true;
  }
  function removeLayer(recipe, layerId, at) {
    const before = recipe.stack.length;
    recipe.stack = recipe.stack.filter((layer) => layer.id !== layerId);
    recipe.updatedAt = nowText(at);
    return before !== recipe.stack.length;
  }
  function duplicateRecipe(workspace, recipeId, at) {
    const source = workspace.recipes.find((recipe) => recipe.id === recipeId);
    if (!source) throw new TypeError(`Unknown recipe: ${recipeId}`);
    const stamp = nowText(at);
    const copy = clone(source);
    copy.id = `recipe-${fnv1a(`${source.id}|copy|${stamp}`)}`;
    copy.name = `${source.name} copy`;
    copy.createdAt = stamp;
    copy.updatedAt = stamp;
    copy.stack = copy.stack.map((layer, index) => normalizeLayer(Object.assign({}, layer, { id: `layer-${fnv1a(`${copy.id}|${layer.entryId}|${index}`)}` }), index));
    workspace.recipes.push(copy);
    workspace.activeRecipeId = copy.id;
    touch(workspace, copy, stamp);
    return clone(copy);
  }
  function setLightPreset(recipe, presetId, at) {
    recipe.lightRig = normalizeLightRig(lightRigById(presetId));
    recipe.updatedAt = nowText(at);
    return clone(recipe.lightRig);
  }
  function patchLightRig(recipe, patch, at) {
    recipe.lightRig = normalizeLightRig(Object.assign({}, recipe.lightRig, patch || {}));
    recipe.updatedAt = nowText(at);
    return clone(recipe.lightRig);
  }
  function setViewRig(recipe, viewId, at) {
    recipe.viewRig = viewRigById(viewId);
    recipe.updatedAt = nowText(at);
    return clone(recipe.viewRig);
  }
  function patchShader(recipe, patch, at) {
    const merged = Object.assign({}, recipe.shader, clone(patch || {}));
    ['clearcoatLike','fresnelLike','emissiveBoost','roughnessResponse'].forEach((key) => {
      if (patch && patch[key]) merged[key] = Object.assign({}, recipe.shader[key], patch[key]);
    });
    recipe.shader = normalizeShader(merged);
    recipe.updatedAt = nowText(at);
    return clone(recipe.shader);
  }

  function recipeState(recipe) {
    return {
      id: recipe.id,
      name: recipe.name,
      familyIds: clone(recipe.familyIds || []),
      stack: clone(recipe.stack || []),
      lightRig: clone(recipe.lightRig),
      viewRig: clone(recipe.viewRig),
      shader: clone(recipe.shader),
      notes: recipe.notes || ''
    };
  }
  function recipeFingerprint(recipe) { return fnv1a(stableStringify(recipeState(recipe))); }

  function diffValues(before, after, limit) {
    const rows = [];
    function visit(a, b, path) {
      if (rows.length >= (limit || 250)) return;
      if (stableStringify(a) === stableStringify(b)) return;
      const aObject = a && typeof a === 'object';
      const bObject = b && typeof b === 'object';
      if (!aObject || !bObject || Array.isArray(a) !== Array.isArray(b)) {
        rows.push({ path: path || '$', before: clone(a), after: clone(b) });
        return;
      }
      if (Array.isArray(a) && Array.isArray(b)) {
        const max = Math.max(a.length, b.length);
        for (let index = 0; index < max; index += 1) visit(a[index], b[index], `${path}[${index}]`);
        return;
      }
      const keys = [...new Set([...Object.keys(a || {}), ...Object.keys(b || {})])].sort();
      keys.forEach((key) => visit(a && a[key], b && b[key], path ? `${path}.${key}` : key));
    }
    visit(before, after, '');
    return rows;
  }

  function compareRecipeStates(a, b) {
    const before = recipeState(a);
    const after = recipeState(b);
    const changedPaths = diffValues(before, after, 500);
    const counts = { stack: 0, lightRig: 0, viewRig: 0, shader: 0, other: 0 };
    changedPaths.forEach((row) => {
      const rootName = row.path.split(/[.[]/)[0];
      if (Object.prototype.hasOwnProperty.call(counts, rootName)) counts[rootName] += 1;
      else counts.other += 1;
    });
    return {
      beforeFingerprint: recipeFingerprint(a),
      afterFingerprint: recipeFingerprint(b),
      changed: changedPaths.length > 0,
      changedPaths,
      counts
    };
  }

  function validateWorkspace(raw) {
    if (!raw || typeof raw !== 'object') return { ok: false, reason: 'Influence workspace must be an object.' };
    if (raw.format !== FORMAT || raw.version !== VERSION) return { ok: false, reason: `Expected ${FORMAT}/${VERSION}.` };
    if (!Array.isArray(raw.recipes) || !raw.recipes.length) return { ok: false, reason: 'Influence workspace requires at least one recipe.' };
    const ids = new Set();
    for (let recipeIndex = 0; recipeIndex < raw.recipes.length; recipeIndex += 1) {
      const recipe = raw.recipes[recipeIndex];
      if (!recipe || typeof recipe !== 'object' || !recipe.id) return { ok: false, reason: `Recipe ${recipeIndex} is invalid.` };
      if (ids.has(recipe.id)) return { ok: false, reason: `Duplicate recipe id: ${recipe.id}` };
      ids.add(recipe.id);
      if (!Array.isArray(recipe.stack)) return { ok: false, reason: `Recipe ${recipe.id} stack must be an array.` };
      const layerIds = new Set();
      for (let index = 0; index < recipe.stack.length; index += 1) {
        const layer = normalizeLayer(recipe.stack[index], index);
        if (!layer.entryId) return { ok: false, reason: `Recipe ${recipe.id} has a layer without entryId.` };
        if (layerIds.has(layer.id)) return { ok: false, reason: `Recipe ${recipe.id} has duplicate layer id ${layer.id}.` };
        layerIds.add(layer.id);
      }
    }
    if (!ids.has(raw.activeRecipeId)) return { ok: false, reason: 'activeRecipeId does not resolve.' };
    return { ok: true };
  }

  return {
    VERSION,
    FORMAT,
    CHANNELS: CHANNELS.slice(),
    BLEND_MODES: BLEND_MODES.slice(),
    VIEW_RIGS: clone(VIEW_RIGS),
    LIGHT_RIGS: clone(LIGHT_RIGS),
    SHADER_DEFAULTS: clone(SHADER_DEFAULTS),
    clone,
    stableStringify,
    fnv1a,
    normalizeLayer,
    normalizeShader,
    normalizeLightRig,
    lightRigById,
    viewRigById,
    createRecipe,
    createWorkspace,
    activeRecipe,
    addLayer,
    updateLayer,
    moveLayer,
    removeLayer,
    duplicateRecipe,
    setLightPreset,
    patchLightRig,
    setViewRig,
    patchShader,
    recipeState,
    recipeFingerprint,
    diffValues,
    compareRecipeStates,
    validateWorkspace
  };
});
