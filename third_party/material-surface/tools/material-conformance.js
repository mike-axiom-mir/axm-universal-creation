#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const core = require('../conformance-core.js');

function usage() {
  return `AXM Material Exchange Conformance v${core.VERSION}\n\n` +
    'Usage:\n' +
    '  node tools/material-conformance.js check-material-offer OFFER.json [--family ID --projection-out FILE] [--receipt-out FILE]\n' +
    '  node tools/material-conformance.js check-material-feedback FEEDBACK.json [--offer OFFER.json] [--receipt-out FILE]\n\n' +
    'Aliases: check-offer, check-feedback\n' +
    'Exit codes: 0 PASS, 2 HOLD/conformance failure, 1 usage/runtime error.\n';
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(path.resolve(file), 'utf8'));
}

function writeJson(file, value) {
  const target = path.resolve(file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function parseOptions(args) {
  const options = { positional: [] };
  for (let i = 0; i < args.length; i += 1) {
    const token = args[i];
    if (!token.startsWith('--')) {
      options.positional.push(token);
      continue;
    }
    if (['--family','--projection-out','--receipt-out','--offer'].includes(token)) {
      if (i + 1 >= args.length) throw new Error(`Missing value for ${token}.`);
      options[token.slice(2)] = args[++i];
      continue;
    }
    throw new Error(`Unknown option: ${token}`);
  }
  return options;
}

function outputReceipt(receipt, receiptOut) {
  if (receiptOut) writeJson(receiptOut, receipt);
  process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
  return receipt.status === 'PASS' ? 0 : 2;
}

function checkOffer(args) {
  const options = parseOptions(args);
  if (options.positional.length !== 1) throw new Error('check-material-offer requires exactly one offer JSON file.');
  if (options['projection-out'] && !options.family) throw new Error('--projection-out requires --family ID.');
  const offer = readJson(options.positional[0]);
  const checkedAt = new Date().toISOString();
  const receipt = core.conformOffer(offer, { checkedAt });
  if (options.family) {
    if (!receipt.offer) {
      receipt.projection = { status: 'HOLD', reason: 'Structural offer conformance failed; projection unavailable.' };
    } else {
      try {
        const projection = core.buildFamilyProjection(offer, options.family, { receipt });
        receipt.projection = {
          format: projection.format,
          version: projection.version,
          producerFamilyId: projection.producerFamilyId,
          status: projection.status,
          installable: projection.installable,
          holds: projection.holds,
          libraryEntries: projection.libraryBundle.entries.length,
          influenceLayers: projection.influenceWorkspace.recipes[0].stack.length
        };
        if (options['projection-out']) writeJson(options['projection-out'], projection);
      } catch (error) {
        receipt.status = 'HOLD';
        receipt.truthStatus = 'HOLD_MATERIAL_OFFER_CONFORMANCE';
        receipt.projection = { status: 'HOLD', reason: error.message || String(error) };
      }
    }
  }
  return outputReceipt(receipt, options['receipt-out']);
}

function checkFeedback(args) {
  const options = parseOptions(args);
  if (options.positional.length !== 1) throw new Error('check-material-feedback requires exactly one feedback JSON file.');
  const feedback = readJson(options.positional[0]);
  const offer = options.offer ? readJson(options.offer) : null;
  const receipt = core.conformFeedback(feedback, { offer, checkedAt: new Date().toISOString() });
  return outputReceipt(receipt, options['receipt-out']);
}

function main(argv) {
  const command = argv[0];
  if (!command || command === '--help' || command === '-h' || command === 'help') {
    process.stdout.write(usage());
    return 0;
  }
  if (command === 'check-material-offer' || command === 'check-offer') return checkOffer(argv.slice(1));
  if (command === 'check-material-feedback' || command === 'check-feedback') return checkFeedback(argv.slice(1));
  throw new Error(`Unknown command: ${command}\n\n${usage()}`);
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
}
