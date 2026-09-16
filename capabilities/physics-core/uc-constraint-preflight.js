'use strict';

const crypto = require('crypto');
const Core = require('./source/axm-physics-core.js');
const TranslationMounts = require('./uc-translation-mounts.js');
const DistanceJoints = require('./uc-distance-joints.js');
const DistanceLimits = require('./uc-distance-limits.js');
const AxisLocks = require('./uc-axis-locks.js');
const AxisLimits = require('./uc-axis-limits.js');
const DirectionLocks = require('./uc-direction-locks.js');
const DirectionLimits = require('./uc-direction-limits.js');

const VERSION = '0.2.0';
const REPORT_SCHEMA = 'axm.uc-constraint-preflight/v0.2';
const DEFAULT_TOLERANCE = 1e-9;
const MAX_TOLERANCE = 1e6;

function clone(value) {
  if (Array.isArray(value)) return value.map(clone);
  if (value && typeof value === 'object') {
    const out = {};
    Object.keys(value).forEach(key => { out[key] = clone(value[key]); });
    return out;
  }
  return value;
}
function finite(value, fallback) { const number = Number(value); return Number.isFinite(number) ? number : fallback; }
function bounded(value, min, max, fallback) { return Math.max(min, Math.min(max, finite(value, fallback))); }
function round(value) { return Math.round(value * 1e9) / 1e9; }
function cleanZero(value) { return Math.abs(value) <= Number.EPSILON ? 0 : value; }
function directionKey(direction) { return cleanZero(direction.x).toString() + ',' + cleanZero(direction.y).toString(); }
function negateInterval(min, max) { return { min: -max, max: -min }; }

function canonicalPair(a, b) {
  return a.localeCompare(b) <= 0
    ? { a, b, flipped: false }
    : { a: b, b: a, flipped: true };
}

function canonicalDirection(direction) {
  const x = cleanZero(direction.x);
  const y = cleanZero(direction.y);
  const flipped = x < 0 || (x === 0 && y < 0);
  return flipped
    ? { direction: { x: -x, y: -y }, flipped: true }
    : { direction: { x, y }, flipped: false };
}

function canonicalProjectionEntry(input) {
  const pair = canonicalPair(input.a, input.b);
  const projected = canonicalDirection(input.direction);
  let min = input.min;
  let max = input.max;
  if (pair.flipped !== projected.flipped) {
    const negated = negateInterval(min, max);
    min = negated.min;
    max = negated.max;
  }
  const direction = projected.direction;
  return {
    key: pair.a + '\u0000' + pair.b + '\u0000' + directionKey(direction),
    a: pair.a,
    b: pair.b,
    direction: { x: direction.x, y: direction.y },
    min,
    max,
    family: input.family,
    id: input.id,
    source: input.source
  };
}

function exactProjectionEntry(family, item, direction, offset, source) {
  return canonicalProjectionEntry({
    family,
    id: item.id,
    a: item.a,
    b: item.b,
    direction,
    min: offset,
    max: offset,
    source
  });
}

function rangeProjectionEntry(family, item, direction, source) {
  return canonicalProjectionEntry({
    family,
    id: item.id,
    a: item.a,
    b: item.b,
    direction,
    min: item.minOffset,
    max: item.maxOffset,
    source
  });
}

function radialEntry(family, item, min, max, source) {
  const pair = canonicalPair(item.a, item.b);
  return {
    key: pair.a + '\u0000' + pair.b,
    a: pair.a,
    b: pair.b,
    min,
    max,
    family,
    id: item.id,
    source
  };
}

function normalizeAnalyzed(world, constraints) {
  constraints = constraints || {};
  return {
    mounts: TranslationMounts.normalizeMounts(constraints.mounts || [], world),
    distanceJoints: DistanceJoints.normalizeJoints(constraints.distanceJoints || [], world),
    distanceLimits: DistanceLimits.normalizeLimits(constraints.distanceLimits || [], world),
    axisLocks: AxisLocks.normalizeLocks(constraints.axisLocks || [], world),
    axisLimits: AxisLimits.normalizeLimits(constraints.axisLimits || [], world),
    directionLocks: DirectionLocks.normalizeLocks(constraints.directionLocks || [], world),
    directionLimits: DirectionLimits.normalizeLimits(constraints.directionLimits || [], world)
  };
}

function buildProjectionEntries(normalized) {
  const entries = [];
  normalized.mounts.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactProjectionEntry('translation-mounts', item, { x: 1, y: 0 }, item.offset.x, 'mount-x'));
    entries.push(exactProjectionEntry('translation-mounts', item, { x: 0, y: 1 }, item.offset.y, 'mount-y'));
  });
  normalized.axisLocks.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactProjectionEntry('axis-locks', item, item.axis === 'x' ? { x: 1, y: 0 } : { x: 0, y: 1 }, item.offset, 'axis-' + item.axis));
  });
  normalized.axisLimits.forEach(item => {
    if (!item.enabled) return;
    entries.push(rangeProjectionEntry('axis-limits', item, item.axis === 'x' ? { x: 1, y: 0 } : { x: 0, y: 1 }, 'axis-' + item.axis));
  });
  normalized.directionLocks.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactProjectionEntry('direction-locks', item, item.direction, item.offset, 'fixed-direction'));
  });
  normalized.directionLimits.forEach(item => {
    if (!item.enabled) return;
    entries.push(rangeProjectionEntry('direction-limits', item, item.direction, 'fixed-direction'));
  });
  return entries.sort((left, right) =>
    left.key.localeCompare(right.key) ||
    left.family.localeCompare(right.family) ||
    left.id.localeCompare(right.id) ||
    left.source.localeCompare(right.source)
  );
}

function buildRadialEntries(normalized) {
  const entries = [];
  normalized.distanceJoints.forEach(item => {
    if (!item.enabled) return;
    entries.push(radialEntry('distance-joints', item, item.length, item.length, 'center-distance-equality'));
  });
  normalized.distanceLimits.forEach(item => {
    if (!item.enabled) return;
    entries.push(radialEntry('distance-limits', item, item.minLength, item.maxLength, 'center-distance-range'));
  });
  return entries.sort((left, right) =>
    left.key.localeCompare(right.key) ||
    left.family.localeCompare(right.family) ||
    left.id.localeCompare(right.id) ||
    left.source.localeCompare(right.source)
  );
}

function analyzeProjectionGroups(entries, tolerance) {
  const grouped = new Map();
  entries.forEach(entry => {
    if (!grouped.has(entry.key)) grouped.set(entry.key, []);
    grouped.get(entry.key).push(entry);
  });

  const groups = [];
  const conflicts = [];
  Array.from(grouped.keys()).sort().forEach(key => {
    const items = grouped.get(key);
    let min = -Infinity;
    let max = Infinity;
    items.forEach(item => {
      min = Math.max(min, item.min);
      max = Math.min(max, item.max);
    });
    const first = items[0];
    const conflict = min > max + tolerance;
    const summary = {
      a: first.a,
      b: first.b,
      direction: { x: round(first.direction.x), y: round(first.direction.y) },
      constraintCount: items.length,
      intersection: {
        min: Number.isFinite(min) ? round(min) : min,
        max: Number.isFinite(max) ? round(max) : max
      },
      conflict,
      constraints: items.map(item => ({
        family: item.family,
        id: item.id,
        source: item.source,
        min: Number.isFinite(item.min) ? round(item.min) : item.min,
        max: Number.isFinite(item.max) ? round(item.max) : item.max
      }))
    };
    groups.push(summary);
    if (conflict) {
      conflicts.push({
        code: 'CONFLICTING_TRANSLATION_INTERVALS',
        a: summary.a,
        b: summary.b,
        direction: clone(summary.direction),
        intersection: clone(summary.intersection),
        constraintIds: summary.constraints.map(item => item.id),
        families: Array.from(new Set(summary.constraints.map(item => item.family))).sort()
      });
    }
  });
  return { groups, conflicts };
}

function analyzeRadialGroups(entries, tolerance) {
  const grouped = new Map();
  entries.forEach(entry => {
    if (!grouped.has(entry.key)) grouped.set(entry.key, []);
    grouped.get(entry.key).push(entry);
  });

  const groups = [];
  const conflicts = [];
  Array.from(grouped.keys()).sort().forEach(key => {
    const items = grouped.get(key);
    let min = -Infinity;
    let max = Infinity;
    items.forEach(item => {
      min = Math.max(min, item.min);
      max = Math.min(max, item.max);
    });
    const first = items[0];
    const conflict = min > max + tolerance;
    const summary = {
      a: first.a,
      b: first.b,
      constraintCount: items.length,
      intersection: {
        min: Number.isFinite(min) ? round(min) : min,
        max: Number.isFinite(max) ? round(max) : max
      },
      conflict,
      constraints: items.map(item => ({
        family: item.family,
        id: item.id,
        source: item.source,
        min: Number.isFinite(item.min) ? round(item.min) : item.min,
        max: Number.isFinite(item.max) ? round(item.max) : item.max
      }))
    };
    groups.push(summary);
    if (conflict) {
      conflicts.push({
        code: 'CONFLICTING_DISTANCE_INTERVALS',
        a: summary.a,
        b: summary.b,
        intersection: clone(summary.intersection),
        constraintIds: summary.constraints.map(item => item.id),
        families: Array.from(new Set(summary.constraints.map(item => item.family))).sort()
      });
    }
  });
  return { groups, conflicts };
}

function countDisabled(normalized) {
  return Object.values(normalized).reduce((sum, items) => sum + items.filter(item => !item.enabled).length, 0);
}

function reportChecksum(report) {
  const basis = {
    schema: report.schema,
    version: report.version,
    valid: report.valid,
    conflictFree: report.conflictFree,
    tolerance: report.tolerance,
    counts: report.counts,
    groups: report.groups,
    radialGroups: report.radialGroups,
    conflicts: report.conflicts,
    unsupportedFamilies: report.unsupportedFamilies,
    errors: report.errors
  };
  return crypto.createHash('sha256').update(JSON.stringify(basis)).digest('hex');
}

function analyze(world, constraints, options) {
  options = options || {};
  const coreValidation = Core.validate(world);
  const errors = (coreValidation.errors || []).slice();
  let normalized = {
    mounts: [],
    distanceJoints: [],
    distanceLimits: [],
    axisLocks: [],
    axisLimits: [],
    directionLocks: [],
    directionLimits: []
  };
  if (coreValidation.ok) {
    try { normalized = normalizeAnalyzed(world, constraints); }
    catch (error) { errors.push(error.message); }
  }

  const tolerance = bounded(options.tolerance, 0, MAX_TOLERANCE, DEFAULT_TOLERANCE);
  const projectionEntries = errors.length ? [] : buildProjectionEntries(normalized);
  const radialEntries = errors.length ? [] : buildRadialEntries(normalized);
  const projected = analyzeProjectionGroups(projectionEntries, tolerance);
  const radial = analyzeRadialGroups(radialEntries, tolerance);
  const conflicts = projected.conflicts.concat(radial.conflicts);
  const unsupportedFamilies = [];
  const report = {
    schema: REPORT_SCHEMA,
    version: VERSION,
    ok: errors.length === 0 && conflicts.length === 0,
    valid: errors.length === 0,
    conflictFree: errors.length === 0 && conflicts.length === 0,
    tolerance,
    counts: {
      normalizedConstraints: Object.values(normalized).reduce((sum, items) => sum + items.length, 0),
      analyzedProjectionEntries: projectionEntries.length,
      projectionGroups: projected.groups.length,
      analyzedRadialEntries: radialEntries.length,
      radialGroups: radial.groups.length,
      conflicts: conflicts.length,
      projectionConflicts: projected.conflicts.length,
      radialConflicts: radial.conflicts.length,
      disabledConstraints: countDisabled(normalized),
      unsupportedConstraints: 0
    },
    groups: projected.groups,
    radialGroups: radial.groups,
    conflicts,
    unsupportedFamilies,
    errors,
    evidence: [
      projectionEntries.length + ' enabled projected translation interval(s) canonicalized in deterministic pair/direction order',
      projected.groups.length + ' exact normalized projection group(s) intersected with tolerance ' + tolerance,
      radialEntries.length + ' enabled center-distance interval(s) canonicalized in deterministic body-pair order',
      radial.groups.length + ' exact same-pair radial distance group(s) intersected with tolerance ' + tolerance,
      conflicts.length + ' provable local constraint conflict(s) found'
    ],
    limitations: [
      'This preflight is a conservative local check for translation mounts plus axis/fixed-direction locks and limits that share exactly the same normalized projection, and for distance joints/limits that constrain exactly the same body pair.',
      'It does not prove global constraint satisfiability, convergence, stability or physical correctness.',
      'Distance analysis proves only same-body-pair scalar distance interval contradictions; it does not reason across triangles, loops, coupled directions or other multi-constraint geometry.',
      'Near-parallel but non-identical directions are intentionally kept in separate groups to avoid inventing equivalence.',
      'Disabled constraints are validated for source/body integrity but excluded from conflict intersections.',
      'The report does not change world state, solver order, collision behavior or the donor physics source.',
      'This is game/prototype correctness evidence, not scientific validation.'
    ]
  };
  report.checksum = reportChecksum(report);
  return report;
}

function validate(world, constraints, options) {
  const report = analyze(world, constraints, options);
  return {
    ok: report.ok,
    valid: report.valid,
    conflictFree: report.conflictFree,
    errors: clone(report.errors),
    conflicts: clone(report.conflicts),
    checksum: report.checksum,
    warnings: clone(report.limitations)
  };
}

module.exports = {
  VERSION,
  REPORT_SCHEMA,
  DEFAULT_TOLERANCE,
  MAX_TOLERANCE,
  canonicalPair,
  canonicalDirection,
  analyze,
  validate
};
