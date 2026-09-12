(function () {
  'use strict';

  const core = window.AXMPremadeComposerCore;
  const pack = window.AXMPremadePack;
  if (!core || !pack) throw new Error('Premade Composer requires premade pack and composer core.');
  const workspaceGrid = document.querySelector('.workspace-grid');
  if (!workspaceGrid) return;

  let recipe = core.createRecipe('premade composition', '0');
  let selectedLayerId = null;
  const imageCache = new Map();
  let lastReceipt = null;
  let renderGeneration = 0;
  const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const panel = document.createElement('section');
  panel.className = 'panel premade-composer-panel';
  panel.innerHTML = `
    <div class="panel-heading">
      <div><h2>Asset Composer</h2></div>
      <span class="count-pill">24 sheets</span>
    </div>
    <div class="truth-note">24 original sheets. Select a globe or crop an ingredient, then blend layers. Sources have opaque black backgrounds; screen blending can suit light effects. Grid crops are approximate.</div>

    <div class="premade-toolbar">
      <label>Seed<input id="premadeSeed" value="axm-001" /></label>
      <label>Base<select id="premadeBase"><option value="mixed">mixed globes</option><option value="material">material</option><option value="weathered">weathered</option><option value="color">color</option><option value="energy">energy</option></select></label>
      <label>Extra layers<input id="premadeCount" type="number" min="0" max="8" value="4" /></label>
      <label><span>Include FX</span><input id="premadeFx" type="checkbox" checked /></label>
      <label><span>Include decals</span><input id="premadeDecals" type="checkbox" checked /></label>
      <button class="button primary" id="premadeGenerate">Generate from seed</button>
      <button class="button" id="premadeBlank">Blank recipe</button>
    </div>

    <div class="premade-layout">
      <section class="premade-subpanel">
        <div class="influence-subheading"><strong>Add ingredient</strong><span>${pack.assets.length} atlases</span></div>
        <label>Atlas<select id="premadeAsset"></select></label>
        <div class="premade-layer-controls">
          <label>Row<input id="premadeRow" type="number" min="0" value="0" /></label>
          <label>Column<input id="premadeColumn" type="number" min="0" value="0" /></label>
          <label>Crop X<input id="premadeCropX" type="number" min="0" max="1" step="0.01" value="0" /></label>
          <label>Crop Y<input id="premadeCropY" type="number" min="0" max="1" step="0.01" value="0" /></label>
          <label>Crop W<input id="premadeCropW" type="number" min="0.01" max="1" step="0.01" value="1" /></label>
          <label>Crop H<input id="premadeCropH" type="number" min="0.01" max="1" step="0.01" value="1" /></label>
        </div>
        <button class="button accent" id="premadeAdd">Add layer</button>
        <div class="premade-status" id="premadePackStatus">Pack path: ${pack.rootPath}</div>
        <hr />
        <div class="influence-subheading"><strong>Layers</strong><span id="premadeLayerCount">0</span></div>
        <div class="premade-layer-list" id="premadeLayers"></div>
      </section>

      <section class="premade-subpanel">
        <div class="influence-subheading"><strong>Composition preview</strong><span id="premadeFingerprint">--------</span></div>
        <div class="premade-canvas-wrap"><canvas id="premadeCanvas" width="1024" height="1024"></canvas></div>
        <div class="premade-actions">
          <button class="button primary" id="premadeRender">Render</button>
          <button class="button" id="premadeExportPng">Export PNG</button>
          <button class="button" id="premadeExportRecipe">Export recipe JSON</button>
          <label class="button" for="premadeImportRecipe">Import recipe</label>
          <input id="premadeImportRecipe" type="file" accept="application/json,.json" hidden />
        </div>
        <div id="premadeRenderStatus" class="premade-status">idle</div>
      </section>

      <section class="premade-subpanel">
        <div class="influence-subheading"><strong>Selected layer</strong><span id="premadeSelected">none</span></div>
        <div id="premadeInspector" class="premade-layer-controls"></div>
        <hr />
        <div class="influence-subheading"><strong>Render receipt</strong><span>local evidence</span></div>
        <pre id="premadeReceipt" class="state-output premade-receipt"></pre>
      </section>
    </div>
  `;
  workspaceGrid.appendChild(panel);

  const el = Object.fromEntries([
    'Seed','Base','Count','Fx','Decals','Generate','Blank','Asset','Row','Column','CropX','CropY','CropW','CropH','Add','PackStatus','Layers','LayerCount','Canvas','Fingerprint','Render','ExportPng','ExportRecipe','ImportRecipe','RenderStatus','Selected','Inspector','Receipt'
  ].map((name) => [name[0].toLowerCase() + name.slice(1), panel.querySelector(`#premade${name}`)]));

  const BLEND_TO_CANVAS = { normal:'source-over', multiply:'multiply', screen:'screen', overlay:'overlay', 'soft-light':'soft-light', 'hard-light':'hard-light', lighter:'lighter', difference:'difference' };

  pack.assets.forEach((asset) => {
    const option = document.createElement('option');
    option.value = asset.id;
    option.textContent = `${asset.id} · ${asset.kind}`;
    el.asset.appendChild(option);
  });

  function asset() { return core.byId(pack, el.asset.value); }
  function refreshAssetControls() {
    const current = asset();
    const grid = current && current.grid;
    el.row.value = '0'; el.column.value = '0';
    el.row.disabled = !grid;
    el.column.disabled = !grid;
    [el.cropX,el.cropY,el.cropW,el.cropH].forEach((node) => { node.disabled = Boolean(grid); });
    if (grid) {
      el.row.max = String(grid.rows - 1);
      el.column.max = String(grid.columns - 1);
    }
  }

  function download(name, blob) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function selectedLayer() { return recipe.layers.find((layer) => layer.id === selectedLayerId) || null; }

  function renderLayerList() {
    el.layers.innerHTML = '';
    el.layerCount.textContent = String(recipe.layers.length);
    recipe.layers.forEach((layer, index) => {
      const row = document.createElement('div');
      row.className = `premade-layer${layer.id === selectedLayerId ? ' active' : ''}`;
      row.innerHTML = `<div><strong>${escapeHtml(layer.name)}</strong><br><small>${layer.assetId} · ${layer.blendMode} · ${Math.round(layer.opacity*100)}%</small></div><small>${index + 1}</small>`;
      row.addEventListener('click', () => { selectedLayerId = layer.id; renderLayerList(); renderInspector(); });
      el.layers.appendChild(row);
    });
    renderInspector();
  }

  function input(label, key, value, attrs) {
    return `<label>${label}<input data-field="${key}" value="${value}" ${attrs || ''}></label>`;
  }

  function renderInspector() {
    const layer = selectedLayer();
    if (!layer) { el.selected.textContent = 'none'; el.inspector.innerHTML = '<div class="wide premade-status">Select a layer.</div>'; return; }
    el.selected.textContent = layer.assetId;
    el.inspector.innerHTML = `
      <label>Visible<select data-field="visible"><option value="true" ${layer.visible?'selected':''}>yes</option><option value="false" ${!layer.visible?'selected':''}>no</option></select></label>
      <label>Blend<select data-field="blendMode">${core.BLEND_MODES.map((mode)=>`<option ${mode===layer.blendMode?'selected':''}>${mode}</option>`).join('')}</select></label>
      ${input('Opacity','opacity',layer.opacity,'type="number" min="0" max="1" step="0.05"')}
      ${input('X','x',layer.transform.x,'type="number" step="0.01"')}
      ${input('Y','y',layer.transform.y,'type="number" step="0.01"')}
      ${input('Width','width',layer.transform.width,'type="number" min="0.02" max="4" step="0.02"')}
      ${input('Height','height',layer.transform.height,'type="number" min="0.02" max="4" step="0.02"')}
      ${input('Rotation','rotation',layer.transform.rotation,'type="number" step="1"')}
      <button class="button" data-action="up">Move up</button><button class="button" data-action="down">Move down</button>
      <button class="button danger wide" data-action="remove">Remove layer</button>`;

    el.inspector.querySelectorAll('[data-field]').forEach((node) => node.addEventListener('change', () => {
      const target = selectedLayer(); if (!target) return;
      const field = node.dataset.field;
      if (field === 'visible') target.visible = node.value === 'true';
      else if (field === 'blendMode') target.blendMode = node.value;
      else if (field === 'opacity') target.opacity = Number(node.value);
      else target.transform[field] = Number(node.value);
      recipe.layers = recipe.layers.map((item,index)=>core.normalizeLayer(item,index,pack));
      renderLayerList(); renderPreview();
    }));
    el.inspector.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => {
      const index = recipe.layers.findIndex((item) => item.id === selectedLayerId);
      if (index < 0) return;
      if (button.dataset.action === 'remove') { recipe.layers.splice(index,1); selectedLayerId = recipe.layers[0] && recipe.layers[0].id || null; }
      if (button.dataset.action === 'up' && index < recipe.layers.length - 1) [recipe.layers[index],recipe.layers[index+1]]=[recipe.layers[index+1],recipe.layers[index]];
      if (button.dataset.action === 'down' && index > 0) [recipe.layers[index],recipe.layers[index-1]]=[recipe.layers[index-1],recipe.layers[index]];
      renderLayerList(); renderPreview();
    }));
  }

  function loadImage(path) {
    if (imageCache.has(path)) return imageCache.get(path);
    const promise = new Promise((resolve,reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`missing runtime asset: ${path}`));
      image.src = path;
    });
    imageCache.set(path, promise);
    return promise;
  }

  async function renderPreview() {
    const generation = ++renderGeneration;
    let plan;
    try { plan = core.compilePlan(recipe, pack); }
    catch (error) { el.renderStatus.textContent = error.message; return null; }
    const surface = document.createElement('canvas');
    const ctx = surface.getContext('2d');
    const width = plan.canvas.width, height = plan.canvas.height;
    surface.width = width; surface.height = height;
    ctx.clearRect(0,0,width,height);
    const rendered = [], held = [];
    for (const layer of plan.layers) {
      if (!layer.visible) continue;
      try {
        const image = await loadImage(layer.resourcePath);
        const s = layer.sourceRect, t = layer.transform;
        const dw = t.width * width, dh = t.height * height;
        ctx.save();
        ctx.globalAlpha = layer.opacity;
        ctx.globalCompositeOperation = BLEND_TO_CANVAS[layer.blendMode] || 'source-over';
        ctx.translate(t.x * width, t.y * height);
        ctx.rotate(t.rotation * Math.PI / 180);
        ctx.scale(t.mirrorX ? -1 : 1, t.mirrorY ? -1 : 1);
        ctx.drawImage(image, s.x, s.y, s.width, s.height, -dw/2, -dh/2, dw, dh);
        ctx.restore();
        rendered.push(layer.id);
      } catch (error) { held.push({ layerId: layer.id, assetId: layer.assetId, reason: error.message }); }
    }
    if (generation !== renderGeneration) return null;
    el.canvas.width = width; el.canvas.height = height;
    el.canvas.getContext('2d').drawImage(surface, 0, 0);
    lastReceipt = {
      format:'axm-premade-composition-receipt', version:core.VERSION,
      recipeId:plan.recipeId, recipeFingerprint:plan.recipeFingerprint,
      packVersion:pack.version, archiveSha256:pack.binaryPack.sha256,
      sourceAlpha:false, transparentCanvas:true, renderedLayers:rendered, heldLayers:held,
      truthBoundary:'Canvas composition evidence only; missing runtime files remain HOLD and non-grid atlas crops are not semantic segmentation.'
    };
    el.fingerprint.textContent = plan.recipeFingerprint;
    el.renderStatus.innerHTML = held.length ? `<span class="premade-held">rendered ${rendered.length}, HOLD ${held.length}</span>` : `rendered ${rendered.length} layers`;
    el.receipt.textContent = JSON.stringify(lastReceipt,null,2);
    return lastReceipt;
  }

  el.asset.addEventListener('change', refreshAssetControls);
  el.add.addEventListener('click', () => {
    const current = asset(); if (!current) return;
    const raw = { assetId: current.id, opacity:1, blendMode: current.kind === 'fx-atlas' ? 'screen' : 'normal', transform:{x:.5,y:.5,width:.75,height:.75,rotation:0} };
    if (current.grid) raw.cell = { row:Number(el.row.value)||0, column:Number(el.column.value)||0 };
    else raw.crop = { x:Number(el.cropX.value)||0, y:Number(el.cropY.value)||0, width:Number(el.cropW.value)||1, height:Number(el.cropH.value)||1 };
    const layer = core.normalizeLayer(raw, recipe.layers.length, pack);
    recipe.layers.push(layer); selectedLayerId = layer.id; renderLayerList(); renderPreview();
  });
  el.generate.addEventListener('click', () => {
    recipe = core.seededRecipe(el.seed.value, pack, { basePool:el.base.value, overlayCount:Number(el.count.value)||0, includeFx:el.fx.checked, includeDecals:el.decals.checked });
    selectedLayerId = recipe.layers[0] && recipe.layers[0].id || null; renderLayerList(); renderPreview();
  });
  el.blank.addEventListener('click', () => { recipe = core.createRecipe('premade composition', el.seed.value); selectedLayerId = null; renderLayerList(); renderPreview(); });
  el.render.addEventListener('click', renderPreview);
  el.exportPng.addEventListener('click', async () => { const receipt = await renderPreview(); if (!receipt || receipt.heldLayers.length) return; el.canvas.toBlob((blob)=>blob && download(`${recipe.id}.png`, blob), 'image/png'); });
  el.exportRecipe.addEventListener('click', () => download(`${recipe.id}.json`, new Blob([JSON.stringify(recipe,null,2)], {type:'application/json'})));
  el.importRecipe.addEventListener('change', async () => {
    const file = el.importRecipe.files && el.importRecipe.files[0]; if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      const validation = core.validateRecipe(parsed, pack); if (!validation.ok) throw new Error(validation.reason);
      if (!Number.isInteger(parsed.canvas.width) || !Number.isInteger(parsed.canvas.height) || parsed.canvas.width < 16 || parsed.canvas.height < 16 || parsed.canvas.width > 4096 || parsed.canvas.height > 4096 || parsed.layers.length > 64) throw new Error('Use a 16–4096 pixel canvas and at most 64 layers.');
      recipe = parsed; selectedLayerId = recipe.layers[0] && recipe.layers[0].id || null; renderLayerList(); await renderPreview();
    } catch (error) { el.renderStatus.textContent = `import failed: ${error.message}`; }
    el.importRecipe.value = '';
  });

  refreshAssetControls();
  renderLayerList();
  el.count.value = '0'; el.base.value = 'energy'; el.generate.click();
})();
