'use strict';

const crypto = require('crypto');
const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Preflight = require('./uc-constraint-preflight.js');

const VERSION = '0.1.0';
const STEP_SCHEMA = 'axm.uc-constraint-preflight-guard-step/v0.1';

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function decisionChecksum(payload) {
  const basis = {
    schema: payload.schema,
    version: payload.version,
    accepted: payload.accepted,
    blocked: payload.blocked,
    reason: payload.reason,
    worldChecksumBefore: payload.worldChecksumBefore,
    worldChecksumAfter: payload.worldChecksumAfter,
    composerValidation: payload.composerValidation,
    preflightChecksum: payload.preflight && payload.preflight.checksum,
    preflightConflictCount: payload.preflight && payload.preflight.counts ? payload.preflight.counts.conflicts : null,
    preflightUnsupportedCount: payload.preflight && payload.preflight.counts ? payload.preflight.counts.unsupportedConstraints : null
  };
  return crypto.createHash('sha256').update(JSON.stringify(basis)).digest('hex');
}

function resultBase(world, composerValidation, preflight) {
  const checksum = Core.checksum(world);
  return {
    schema: STEP_SCHEMA,
    version: VERSION,
    world: clone(world),
    composerValidation: clone(composerValidation),
    preflight: clone(preflight),
    worldChecksumBefore: checksum,
    worldChecksumAfter: checksum,
    coreStepExecuted: false,
    composer: null,
    limitations: [
      'This is an opt-in fail-closed wrapper around the existing constraint composer; the composer itself is unchanged.',
      'Only invalid composer input or conflicts proven by the conservative projected-translation preflight are blocked.',
      'Distance joints and distance limits remain outside the preflight proof and are delegated when otherwise valid; unsupported does not mean conflicting.',
      'A successful preflight is not proof of global satisfiability, convergence, stability or physical correctness.',
      'The accepted path delegates to the existing seven-family composer and therefore retains its fixed ordering, bounded-pass and contact-evidence boundaries.',
      'The imported donor source is not modified by this wrapper.',
      'This is game/prototype correctness evidence, not scientific validation.'
    ]
  };
}

function step(world, constraints, dt, options) {
  options = options || {};
  const composerOptions = options.composer || {};
  const preflightOptions = options.preflight || {};
  const composerValidation = Composer.validate(world, constraints);
  const preflight = Preflight.analyze(world, constraints, preflightOptions);
  const base = resultBase(world, composerValidation, preflight);

  if (!composerValidation.ok) {
    const blocked = Object.assign(base, {
      ok: false,
      accepted: false,
      blocked: true,
      reason: 'INVALID_CONSTRAINTS',
      evidence: [
        'Constraint composer validation rejected the input before donor integration.',
        'World state remained unchanged at checksum ' + base.worldChecksumBefore,
        'No donor-core step was executed.'
      ]
    });
    blocked.decisionChecksum = decisionChecksum(blocked);
    return blocked;
  }

  if (!preflight.conflictFree) {
    const blocked = Object.assign(base, {
      ok: false,
      accepted: false,
      blocked: true,
      reason: 'PROVABLE_LOCAL_CONFLICT',
      evidence: [
        preflight.conflicts.length + ' conservative projected-translation conflict(s) blocked before donor integration.',
        'World state remained unchanged at checksum ' + base.worldChecksumBefore,
        'No donor-core step was executed.'
      ]
    });
    blocked.decisionChecksum = decisionChecksum(blocked);
    return blocked;
  }

  const composer = Composer.step(world, constraints, dt, composerOptions);
  const accepted = Object.assign(base, {
    ok: composer.ok === true,
    accepted: true,
    blocked: false,
    reason: 'ACCEPTED',
    world: composer.world,
    worldChecksumAfter: Core.checksum(composer.world),
    coreStepExecuted: true,
    composer,
    evidence: [
      'Constraint composer validation passed.',
      preflight.counts.conflicts + ' conservative projected-translation conflict(s) found by preflight.',
      preflight.counts.unsupportedConstraints + ' nonlinear distance constraint(s) remained outside the local preflight proof without being treated as conflicts.',
      'Accepted input delegated exactly once to the existing constraint composer.',
      'Final world checksum ' + Core.checksum(composer.world)
    ]
  });
  accepted.decisionChecksum = decisionChecksum(accepted);
  return accepted;
}

module.exports = {
  VERSION,
  STEP_SCHEMA,
  decisionChecksum,
  step
};
