'use strict';

const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');
const Isolation = require('./uc-constraint-collision-isolation.js');

const VERSION = '0.2.0';
const STEP_SCHEMA = 'axm.uc-constraint-activity-step/v0.1';
const FAMILY_KEYS = Object.freeze(['mounts', 'distanceJoints', 'distanceLimits', 'axisLocks']);

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function emptyFamilies() {
  return { mounts: [], distanceJoints: [], distanceLimits: [], axisLocks: [] };
}

function partition(normalized) {
  const active = emptyFamilies();
  const disabled = emptyFamilies();
  FAMILY_KEYS.forEach(key => {
    (normalized[key] || []).forEach(item => {
      (item.enabled === false ? disabled[key] : active[key]).push(item);
    });
  });
  return { active, disabled };
}

function familyDiagnostics(partitioned) {
  const activeIds = {}; const disabledIds = {};
  let activeCount = 0; let disabledCount = 0;
  FAMILY_KEYS.forEach(key => {
    activeIds[key] = partitioned.active[key].map(item => item.id);
    disabledIds[key] = partitioned.disabled[key].map(item => item.id);
    activeCount += activeIds[key].length;
    disabledCount += disabledIds[key].length;
  });
  return { activeCount, disabledCount, activeIds, disabledIds };
}

function prepare(world, constraints) {
  const normalized = Composer.normalizeConstraints(world, constraints || {});
  const partitioned = partition(normalized);
  return { normalized, active: partitioned.active, disabled: partitioned.disabled, diagnostics: familyDiagnostics(partitioned) };
}

function validate(world, constraints) {
  const composer = Composer.validate(world, constraints || {});
  const errors = (composer.errors || []).slice();
  let prepared = null;
  if (composer.ok) {
    try { prepared = prepare(world, constraints || {}); } catch (error) { errors.push(error.message); }
  }
  return {
    ok: errors.length === 0,
    errors,
    activeCount: prepared ? prepared.diagnostics.activeCount : 0,
    disabledCount: prepared ? prepared.diagnostics.disabledCount : 0,
    warnings: (composer.warnings || []).concat([
      'Disabled mounts, distance joints, distance limits and axis locks are still normalized and validated for source/body-reference integrity, but this gate excludes them from solver residuals and collision-isolation topology before delegation.',
      'This is an additive safe front door; direct calls to the lower-level composer/isolation modules retain their existing compatibility behavior.',
      'The donor physics source remains untouched.'
    ])
  };
}

function step(world, constraints, dt, options) {
  options = options || {};
  const validation = validate(world, constraints || {});
  if (!validation.ok) throw new Error(validation.errors.join('; '));
  const prepared = prepare(world, constraints || {});
  const isolated = options.isolateCollisions === true;
  const delegated = isolated
    ? Isolation.step(world, prepared.active, dt, options.isolation || {})
    : Composer.step(world, prepared.active, dt, options.composer || {});
  const checksum = Core.checksum(delegated.world);
  const mode = isolated ? 'ISOLATED_COMPOSER' : 'COMPOSER';
  return {
    schema: STEP_SCHEMA,
    ok: true,
    mode,
    world: delegated.world,
    normalizedConstraints: clone(prepared.normalized),
    activeConstraints: clone(prepared.active),
    activityDiagnostics: {
      activeCount: prepared.diagnostics.activeCount,
      disabledCount: prepared.diagnostics.disabledCount,
      activeIds: clone(prepared.diagnostics.activeIds),
      disabledIds: clone(prepared.diagnostics.disabledIds),
      disabledExcludedFromSolve: true,
      disabledExcludedFromIsolationTopology: true,
      delegateSchema: delegated.schema,
      finalChecksum: checksum
    },
    composerDiagnostics: clone(delegated.composerDiagnostics),
    isolationDiagnostics: isolated ? clone(delegated.isolationDiagnostics) : null,
    core: clone(delegated.core),
    evidence: [
      prepared.diagnostics.activeCount + ' enabled constraint(s) delegated to the physics solver',
      prepared.diagnostics.disabledCount + ' disabled constraint(s) retained in normalized evidence but excluded from solving and isolation topology',
      'Delegation mode ' + mode + ' executed exactly one donor-core physics step through the established composer path',
      'Final state checksum ' + checksum
    ].concat(clone(delegated.evidence || [])),
    limitations: [
      'This gate provides explicit disabled-constraint semantics without silently rewriting the existing lower-level composer or isolation entrypoints.',
      'Disabled constraints are still required to reference valid bodies because normalization/source-integrity validation occurs before activity filtering.',
      'Axis-lock activity filtering does not imply rotating axes, angular limits or motor semantics.',
      'The gate does not add angular inertia, rotating anchors, hinge, full slider/prismatic, rotational weld, motor or gear semantics.',
      'Collision isolation remains component-wide for enabled constraint edges when isolation mode is requested.',
      'This is game/prototype physics evidence, not scientific validation.'
    ].concat(clone(delegated.limitations || []))
  };
}

module.exports = { VERSION, STEP_SCHEMA, FAMILY_KEYS, partition, prepare, validate, step };
