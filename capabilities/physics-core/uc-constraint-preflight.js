'use strict';

const crypto = require('crypto');
const Core = require('./source/axm-physics-core.js');
const TranslationMounts = require('./uc-translation-mounts.js');
const AxisLocks = require('./uc-axis-locks.js');
const AxisLimits = require('./uc-axis-limits.js');
const DirectionLocks = require('./uc-direction-locks.js');
const DirectionLimits = require('./uc-direction-limits.js');

const VERSION = '0.1.0';
const REPORT_SCHEMA = 'axm.uc-constraint-preflight/v0.1';
const DEFAULT_TOLERANCE = 1e-9;
const MAX_TOLERANCE = 1e6;

function clone(value) { return JSON.parse(JSON.stringify(value)); }
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

function canonicalEntry(input) {
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

function exactEntry(family, item, direction, offset, source) {
  return canonicalEntry({
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

function rangeEntry(family, item, direction, source) {
  return canonicalEntry({
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

function normalizeAnalyzed(world, constraints) {
  constraints = constraints || {};
  return {
    mounts: TranslationMounts.normalizeMounts(constraints.mounts || [], world),
    axisLocks: AxisLocks.normalizeLocks(constraints.axisLocks || [], world),
    axisLimits: AxisLimits.normalizeLimits(constraints.axisLimits || [], world),
    directionLocks: DirectionLocks.normalizeLocks(constraints.directionLocks || [], world),
    directionLimits: DirectionLimits.normalizeLimits(constraints.directionLimits || [], world)
  };
}

function buildEntries(normalized) {
  const entries = [];
  normalized.mounts.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactEntry('translation-mounts', item, { x: 1, y: 0 }, item.offset.x, 'mount-x'));
    entries.push(exactEntry('translation-mounts', item, { x: 0, y: 1 }, item.offset.y, 'mount-y'));
  });
  normalized.axisLocks.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactEntry('axis-locks', item, item.axis === 'x' ? { x: 1, y: 0 } : { x: 0, y: 1 }, item.offset, 'axis-' + item.axis));
  });
  normalized.axisLimits.forEach(item => {
    if (!item.enabled) return;
    entries.push(rangeEntry('axis-limits', item, item.axis === 'x' ? { x: 1, y: 0 } : { x: 0, y: 1 }, 'axis-' + item.axis));
  });
  normalized.directionLocks.forEach(item => {
    if (!item.enabled) return;
    entries.push(exactEntry('direction-locks', item, item.direction, item.offset, 'fixed-direction'));
  });
  normalized.directionLimits.forEach(item => {
    if (!item.enabled) return;
    entries.push(rangeEntry('direction-limits', item, item.direction, 'fixed-direction'));
  });
  return entries.sort((left, right) =>
    left.key.localeCompare(right.key) ||
    left.family.localeCompare(right.family) ||
    left.id.localeCompare(right.id) ||
    left.source.localeCompare(right.source)
  );
}

function analyzeGroups(entries, tolerance) {
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

function countDisabled(normalized) {
  return Object.values(normalized).reduce((sum, items) => sum + items.filter(item => !item.enabled).length, 0);
}

function unsupported(constraints) {
  constraints = constraints || {};
  const rows = [];
  const distanceJoints = Array.isArray(constraints.distanceJoints) ? constraints.distanceJoints.length : 0;
  const distanceLimits = Array.isArray(constraints.distanceLimits) ? constraints.distanceLimits.length : 0;
  if (distanceJoints) rows.push({ family: 'distance-joints', count: distanceJoints, reason: 'nonlinear radial equality is outside v0.1 projected-interval proof' });
  if (distanceLimits) rows.push({ family: 'distance-limits', count: distanceLimits, reason: 'nonlinear radial range is outside v0.1 projected-interval proof' });
  return rows;
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
  let normalized = { mounts: [], axisLocks: [], axisLimits: [], directionLocks: [], directionLimits: [] };
  if (coreValidation.ok) {
    try { normalized = normalizeAnalyzed(world, constraints); }
    catch (error) { errors.push(error.message); }
  }

  const tolerance = bounded(options.tolerance, 0, MAX_TOLERANCE, DEFAULT_TOLERANCE);
  const entries = errors.length ? [] : buildEntries(normalized);
  const grouped = analyzeGroups(entries, tolerance);
  const unsupportedFamilies = unsupported(constraints);
  const report = {
    schema: REPORT_SCHEMA,
    version: VERSION,
    ok: errors.length === 0 && grouped.conflicts.length === 0,
    valid: errors.length === 0,
    conflictFree: errors.length === 0 && grouped.conflicts.length === 0,
    tolerance,
    counts: {
      normalizedConstraints: Object.values(normalized).reduce((sum, items) => sum + items.length, 0),
      analyzedProjectionEntries: entries.length,
      projectionGroups: grouped.groups.length,
      conflicts: grouped.conflicts.length,
      disabledConstraints: countDisabled(normalized),
      unsupportedConstraints: unsupportedFamilies.reduce((sum, item) => sum + item.count, 0)
    },
    groups: grouped.groups,
    conflicts: grouped.conflicts,
    unsupportedFamilies,
    errors,
    evidence: [
      entries.length + ' enabled projected translation interval(s) canonicalized in deterministic pair/direction order',
      grouped.groups.length + ' exact normalized projection group(s) intersected with tolerance ' + tolerance,
      grouped.conflicts.length + ' provable local projected-translation conflict(s) found',
      unsupportedFamilies.length ? 'Nonlinear distance families were reported but not analyzed in v0.1' : 'No unsupported nonlinear distance families were supplied'
    ],
    limitations: [
      'This preflight is a conservative local check for translation mounts plus axis/fixed-direction locks and limits that share exactly the same normalized projection.',
      'It does not prove global constraint satisfiability, convergence, stability or physical correctness.',
      'Distance joints and distance limits are reported but not analyzed because their radial constraints are nonlinear in this v0.1 check.',
      'Near-parallel but non-identical directions are intentionally kept in separate groups to avoid inventing equivalence.',
      'Disabled analyzed constraints are validated for source/body integrity but excluded from conflict intersections.',
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
