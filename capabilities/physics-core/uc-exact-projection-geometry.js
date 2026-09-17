'use strict';

const BasePreflight = require('./uc-constraint-preflight.js');
const TranslationMounts = require('./uc-translation-mounts.js');
const DistanceJoints = require('./uc-distance-joints.js');
const DistanceLimits = require('./uc-distance-limits.js');
const AxisLocks = require('./uc-axis-locks.js');
const AxisLimits = require('./uc-axis-limits.js');
const DirectionLocks = require('./uc-direction-locks.js');
const DirectionLimits = require('./uc-direction-limits.js');

const VERSION = '0.1.0';
const SCHEMA = 'axm.uc-exact-projection-geometry/v0.1';

function cleanZero(value) {
  return Math.abs(value) <= Number.EPSILON ? 0 : value;
}

function directionKey(direction) {
  return cleanZero(direction.x).toString() + ',' + cleanZero(direction.y).toString();
}

function pairKey(a, b) {
  return a + '\u0000' + b;
}

function negateInterval(min, max) {
  return { min: -max, max: -min };
}

function canonicalProjectionEntry(input) {
  const pair = BasePreflight.canonicalPair(input.a, input.b);
  const projected = BasePreflight.canonicalDirection(input.direction);
  let min = input.min;
  let max = input.max;
  if (pair.flipped !== projected.flipped) {
    const negated = negateInterval(min, max);
    min = negated.min;
    max = negated.max;
  }
  const direction = projected.direction;
  return {
    key: pairKey(pair.a, pair.b) + '\u0000' + directionKey(direction),
    pairKey: pairKey(pair.a, pair.b),
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
  const pair = BasePreflight.canonicalPair(item.a, item.b);
  return {
    key: pairKey(pair.a, pair.b),
    a: pair.a,
    b: pair.b,
    min,
    max,
    family,
    id: item.id,
    source
  };
}

function normalize(world, constraints) {
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

function groupProjectionEntries(entries, tolerance) {
  const grouped = new Map();
  entries.forEach(entry => {
    if (!grouped.has(entry.key)) grouped.set(entry.key, []);
    grouped.get(entry.key).push(entry);
  });
  return Array.from(grouped.keys()).sort().map(key => {
    const constraints = grouped.get(key);
    let min = -Infinity;
    let max = Infinity;
    constraints.forEach(item => {
      min = Math.max(min, item.min);
      max = Math.min(max, item.max);
    });
    const first = constraints[0];
    return {
      key,
      pairKey: first.pairKey,
      a: first.a,
      b: first.b,
      direction: { x: first.direction.x, y: first.direction.y },
      intersection: { min, max },
      conflict: min > max + tolerance,
      constraints: constraints.map(item => ({
        family: item.family,
        id: item.id,
        source: item.source,
        min: item.min,
        max: item.max
      }))
    };
  });
}

function groupRadialEntries(entries, tolerance) {
  const grouped = new Map();
  entries.forEach(entry => {
    if (!grouped.has(entry.key)) grouped.set(entry.key, []);
    grouped.get(entry.key).push(entry);
  });
  return Array.from(grouped.keys()).sort().map(key => {
    const constraints = grouped.get(key);
    let min = -Infinity;
    let max = Infinity;
    constraints.forEach(item => {
      min = Math.max(min, item.min);
      max = Math.min(max, item.max);
    });
    const first = constraints[0];
    return {
      key,
      a: first.a,
      b: first.b,
      intersection: { min, max },
      conflict: min > max + tolerance,
      constraints: constraints.map(item => ({
        family: item.family,
        id: item.id,
        source: item.source,
        min: item.min,
        max: item.max
      }))
    };
  });
}

function analyze(world, constraints, options) {
  options = options || {};
  const tolerance = Number.isFinite(Number(options.tolerance)) ? Number(options.tolerance) : BasePreflight.DEFAULT_TOLERANCE;
  const normalized = normalize(world, constraints);
  const projectionEntries = buildProjectionEntries(normalized);
  const radialEntries = buildRadialEntries(normalized);
  return {
    schema: SCHEMA,
    version: VERSION,
    tolerance,
    groups: groupProjectionEntries(projectionEntries, tolerance),
    radialGroups: groupRadialEntries(radialEntries, tolerance),
    counts: {
      projectionEntries: projectionEntries.length,
      projectionGroups: groupProjectionEntries(projectionEntries, tolerance).length,
      radialEntries: radialEntries.length,
      radialGroups: groupRadialEntries(radialEntries, tolerance).length
    },
    limitations: [
      'This view exists only to preserve full-precision normalized geometry for downstream proof decisions.',
      'It does not mutate world state, execute the donor core, or independently claim satisfiability.'
    ]
  };
}

module.exports = {
  VERSION,
  SCHEMA,
  analyze
};
