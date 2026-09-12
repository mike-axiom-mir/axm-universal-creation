'use strict';
const assert = require('assert');
const core = require('../premade-composer-core.js');
const pack = require('../premade-pack.js');
const manifest = require('../assets/premade/v0.11/manifest.json');

assert.strictEqual(core.VERSION, '0.12.0');
assert.strictEqual(core.FORMAT, 'axm-premade-composition');
assert.strictEqual(pack.version, manifest.version);
assert.deepStrictEqual(pack.assets.map((asset)=>asset.id), manifest.assets.map((asset)=>asset.id));
assert.strictEqual(pack.binaryPack.sha256, manifest.binaryPack.sha256);

const globeCells = pack.assets.filter((asset)=>asset.grid).reduce((sum,asset)=>sum + asset.grid.rows * asset.grid.columns, 0);
assert.strictEqual(globeCells, 166);

const color = core.byId(pack, 'color-globes');
const lastColor = core.gridCellRect(pack, color, 7, 11);
assert.strictEqual(lastColor.semanticCell, true);
assert.ok(lastColor.x + lastColor.width <= 512);
assert.ok(lastColor.y + lastColor.height <= 512);
assert.throws(()=>core.gridCellRect(pack,color,8,0), /row/);

const crop = core.normalizedCropRect(pack, {x:.25,y:.5,width:.25,height:.25});
assert.deepStrictEqual(crop, {x:128,y:256,width:128,height:128,semanticCell:false});

const recipeA = core.seededRecipe('same-seed', pack, {overlayCount:5,basePool:'material'});
const recipeB = core.seededRecipe('same-seed', pack, {overlayCount:5,basePool:'material'});
const recipeC = core.seededRecipe('other-seed', pack, {overlayCount:5,basePool:'material'});
assert.deepStrictEqual(recipeA, recipeB, 'same seed must produce identical recipe state');
assert.notStrictEqual(core.recipeFingerprint(recipeA,pack), core.recipeFingerprint(recipeC,pack), 'different seeds should change composition state');
assert.strictEqual(recipeA.canvas.transparent, true);
assert.strictEqual(recipeA.layers.length, 6);
assert.strictEqual(recipeA.layers[0].assetId, 'material-globes');
assert.ok(recipeA.layers.slice(1).every((layer)=>layer.crop && layer.provenance.semanticSegmentationClaim === false));

const plan = core.compilePlan(recipeA, pack);
assert.strictEqual(plan.format, 'axm-premade-render-plan');
assert.strictEqual(plan.pack.archiveSha256, manifest.binaryPack.sha256);
assert.ok(plan.layers[0].resourcePath.includes('/globes/material/'));
assert.strictEqual(plan.layers[0].sourceRect.semanticCell, true);
assert.ok(plan.layers.slice(1).every((layer)=>layer.sourceRect.semanticCell === false));

const blank = core.createRecipe('blank','x');
assert.strictEqual(core.validateRecipe(blank,pack).ok,true);
blank.canvas.transparent = false;
assert.strictEqual(core.validateRecipe(blank,pack).ok,false);

const manual = core.createRecipe('manual','m');
manual.layers.push(core.normalizeLayer({assetId:'rust-corrosion',crop:{x:0,y:0,width:.25,height:.25},blendMode:'overlay',opacity:.5},0,pack));
manual.layers.push(core.normalizeLayer({assetId:'radial-holograms',crop:{x:.5,y:.5,width:.166,height:.166},blendMode:'screen',opacity:.6},1,pack));
const manualPlan = core.compilePlan(manual,pack);
assert.strictEqual(manualPlan.layers.length,2);
assert.strictEqual(manualPlan.layers[0].blendMode,'overlay');
assert.strictEqual(manualPlan.layers[1].blendMode,'screen');
assert.match(core.stableStringify(manual.truthBoundary), /does not auto-promote/);
assert.match(core.stableStringify(manual.truthBoundary), /not semantic object segmentation/);

const noFx = core.seededRecipe('no-fx', pack, {overlayCount:8,includeFx:false,includeDecals:false});
assert.ok(noFx.layers.slice(1).every((layer)=>core.byId(pack,layer.assetId).kind === 'overlay-atlas'));

console.log('AXM premade composer core tests: PASS');
