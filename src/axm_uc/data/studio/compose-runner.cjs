// UC adapter; executes the unchanged Apache-2.0 donor compositor.
'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const C = require('./raster-compositor.js');
function sha(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
try {
  const input = fs.readFileSync(0);
  if (input.length > 32 * 1024 * 1024) throw new Error('request exceeds byte bound');
  const request = JSON.parse(input.toString('utf8'));
  if (request.catalog === true) {
    process.stdout.write(JSON.stringify({blends:C.BLEND_MODES, filters:C.FILTER_TYPES, donor_version:C.VERSION}));
  } else {
    const recipe = C.normalizeRecipe(request.recipe);
    if (recipe.canvas.alpha !== true) throw new Error('alpha:false has no flattening implementation; add an opaque bottom layer');
    const sources = Object.create(null);
    let sourceBytes = 0, work = 0;
    for (const [id, src] of Object.entries(request.sources || {})) {
      const bytes = Buffer.from(src.rgba_base64, 'base64');
      sourceBytes += bytes.length;
      if (sourceBytes > 16 * 1024 * 1024) throw new Error('source pixel budget exceeded');
      sources[id] = {width:src.width, height:src.height, rgba:new Uint8Array(bytes), digest:sha(bytes)};
    }
    function cost(filters, pixels) {
      return pixels * (1 + filters.reduce((n, f) => n + (f.type === 'blur' ? 8*(2*f.radius+1) : f.type === 'sharpen' ? 32 : 4), 0));
    }
    for (const layer of recipe.layers) {
      const src = layer.source_artifact_id ? sources[layer.source_artifact_id] : recipe.canvas;
      if (!src) throw new Error('missing source: '+layer.source_artifact_id);
      if (layer.mask) {
        const mask = sources[layer.mask.source_artifact_id];
        if (!mask || mask.width !== src.width || mask.height !== src.height) throw new Error('mask dimensions must equal layer dimensions');
      }
      work += cost(layer.filters, src.width*src.height);
    }
    work += cost(recipe.global_filters, recipe.canvas.width*recipe.canvas.height);
    if (work > 160000000) throw new Error('filter work budget exceeded');
    const result = C.compose(recipe, sources);
    process.stdout.write(JSON.stringify({width:result.width,height:result.height,
      rgba_base64:Buffer.from(result.rgba).toString('base64'),recipe:result.recipe,
      donor_receipt:result.receipt,estimated_filter_work:work,
      donor_sha256:sha(fs.readFileSync(require.resolve('./raster-compositor.js')))}));
  }
} catch (error) { process.stderr.write(String(error.message || error)+'\n'); process.exitCode = 2; }
