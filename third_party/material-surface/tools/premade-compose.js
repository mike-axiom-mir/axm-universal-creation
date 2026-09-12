#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');
const core = require('../premade-composer-core.js');
const pack = require('../premade-pack.js');

function usage(code=0){
  const text = [
    'AXM premade deterministic composer', '',
    'Usage:',
    '  node tools/premade-compose.js seed SEED [--base mixed|material|weathered|color|energy] [--layers N] [--no-fx] [--no-decals] [--out FILE]',
    '  node tools/premade-compose.js plan RECIPE.json [--out FILE]'
  ].join('\n');
  (code ? process.stderr : process.stdout).write(`${text}\n`);
  process.exit(code);
}

function write(value, out){
  const text = `${JSON.stringify(value,null,2)}\n`;
  if (out) { fs.mkdirSync(path.dirname(path.resolve(out)), {recursive:true}); fs.writeFileSync(out,text,'utf8'); }
  else process.stdout.write(text);
}

const [command, ...args] = process.argv.slice(2);
if (!command || command === '-h' || command === '--help') usage();

if (command === 'seed') {
  const seed = args[0]; if (seed == null) usage(1);
  let basePool='mixed', overlayCount=4, includeFx=true, includeDecals=true, out=null;
  for (let i=1;i<args.length;i+=1){
    if (args[i] === '--base') basePool = args[++i];
    else if (args[i] === '--layers') overlayCount = Number(args[++i]);
    else if (args[i] === '--no-fx') includeFx=false;
    else if (args[i] === '--no-decals') includeDecals=false;
    else if (args[i] === '--out') out=args[++i];
    else usage(1);
  }
  const recipe = core.seededRecipe(seed,pack,{basePool,overlayCount,includeFx,includeDecals});
  write({recipe, plan:core.compilePlan(recipe,pack)}, out);
} else if (command === 'plan') {
  const input = args[0]; if (!input) usage(1);
  let out=null;
  for (let i=1;i<args.length;i+=1){ if (args[i] === '--out') out=args[++i]; else usage(1); }
  const recipe = JSON.parse(fs.readFileSync(input,'utf8'));
  write(core.compilePlan(recipe,pack),out);
} else usage(1);
