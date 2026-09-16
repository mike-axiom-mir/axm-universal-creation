'use strict';

const Core = require('./source/axm-physics-core.js');
const Composer = require('./uc-constraint-composer.js');

const VERSION = '0.5.0';
const STEP_SCHEMA = 'axm.uc-constraint-collision-isolation-step/v0.1';
const SIMULATION_SCHEMA = 'axm.uc-constraint-collision-isolation-simulation/v0.1';
const MAX_TEMP_GROUPS = 32768;

function clone(value) { return JSON.parse(JSON.stringify(value)); }
function body(world, id) { return (world.bodies || []).find(item => item.id === id) || null; }
function collisionGroup(item) {
  return item && item.collision && Number.isFinite(Number(item.collision.group)) ? Math.round(Number(item.collision.group)) : 0;
}

function constraintEdges(normalized) {
  const edges = [];
  (normalized.mounts || []).forEach(item => edges.push({ family: 'translation-mounts', id: item.id, a: item.a, b: item.b }));
  (normalized.distanceJoints || []).forEach(item => edges.push({ family: 'distance-joints', id: item.id, a: item.a, b: item.b }));
  (normalized.distanceLimits || []).forEach(item => edges.push({ family: 'distance-limits', id: item.id, a: item.a, b: item.b }));
  (normalized.axisLocks || []).forEach(item => edges.push({ family: 'axis-locks', id: item.id, a: item.a, b: item.b }));
  (normalized.axisLimits || []).forEach(item => edges.push({ family: 'axis-limits', id: item.id, a: item.a, b: item.b }));
  (normalized.directionLocks || []).forEach(item => edges.push({ family: 'direction-locks', id: item.id, a: item.a, b: item.b }));
  return edges.sort((left, right) => {
    const pairLeft = [left.a, left.b].sort().join('\u0000') + '\u0000' + left.family + '\u0000' + left.id;
    const pairRight = [right.a, right.b].sort().join('\u0000') + '\u0000' + right.family + '\u0000' + right.id;
    return pairLeft.localeCompare(pairRight);
  });
}

function connectedComponents(normalized) {
  const adjacency = new Map();
  constraintEdges(normalized).forEach(edge => {
    if (!adjacency.has(edge.a)) adjacency.set(edge.a, new Set());
    if (!adjacency.has(edge.b)) adjacency.set(edge.b, new Set());
    adjacency.get(edge.a).add(edge.b); adjacency.get(edge.b).add(edge.a);
  });
  const visited = new Set(); const components = [];
  Array.from(adjacency.keys()).sort().forEach(start => {
    if (visited.has(start)) return;
    const pending = [start]; const members = [];
    while (pending.length) {
      const current = pending.shift();
      if (visited.has(current)) continue;
      visited.add(current); members.push(current);
      Array.from(adjacency.get(current) || []).sort().forEach(next => { if (!visited.has(next)) pending.push(next); });
    }
    members.sort(); if (members.length > 1) components.push(members);
  });
  return components.sort((a, b) => a[0].localeCompare(b[0]));
}

function nextUnusedNegativeGroup(used, cursor) {
  let value = cursor;
  while (value >= -MAX_TEMP_GROUPS && used.has(value)) value--;
  return value >= -MAX_TEMP_GROUPS ? value : null;
}

function prepare(world, constraints, options) {
  options = options || {};
  const normalized = Composer.normalizeConstraints(world, constraints || {});
  const components = connectedComponents(normalized);
  const out = clone(world); const enabled = options.enabled !== false;
  const usedGroups = new Set((out.bodies || []).map(collisionGroup));
  const receipts = []; let cursor = -1;
  components.forEach((memberIds, index) => {
    const members = memberIds.map(id => body(out, id));
    const originalGroups = members.map(item => collisionGroup(item));
    const receipt = {
      component: index + 1, members: memberIds.slice(), applied: false, temporaryGroup: null,
      originalGroups: memberIds.map((id, memberIndex) => ({ id, group: originalGroups[memberIndex] }))
    };
    if (!enabled) { receipt.reason = 'DISABLED'; receipts.push(receipt); return; }
    if (originalGroups.some(group => group !== 0)) { receipt.reason = 'EXISTING_GROUP_SEMANTICS'; receipts.push(receipt); return; }
    const group = nextUnusedNegativeGroup(usedGroups, cursor);
    if (group == null) { receipt.reason = 'TEMP_GROUP_CAPACITY_EXHAUSTED'; receipts.push(receipt); return; }
    cursor = group - 1; usedGroups.add(group);
    members.forEach(item => {
      if (!item.collision) item.collision = { category: 1, mask: 2147483647, group: 0 };
      item.collision.group = group;
    });
    receipt.applied = true; receipt.temporaryGroup = group; receipt.reason = 'APPLIED_COMPONENT_NEGATIVE_GROUP'; receipts.push(receipt);
  });
  return {
    world: out, normalized, components, receipts, enabled,
    appliedComponents: receipts.filter(item => item.applied).length,
    skippedComponents: receipts.filter(item => !item.applied).length,
    isolatedBodies: receipts.filter(item => item.applied).reduce((total, item) => total + item.members.length, 0)
  };
}

function restoreGroups(world, receipts) {
  const out = clone(world);
  receipts.forEach(receipt => {
    if (!receipt.applied) return;
    receipt.originalGroups.forEach(entry => { const item = body(out, entry.id); if (item && item.collision) item.collision.group = entry.group; });
  });
  return out;
}

function refreshDiagnostics(world, prior) {
  prior = prior || {};
  const refreshed = Core.measure(world, prior.substeps || 0, prior.maxPenetration || 0, prior.broadphasePairs || 0, {
    overflowBodies: prior.broadphaseOverflowBodies || 0,
    cellEntries: prior.broadphaseCellEntries || 0,
    occupiedCells: prior.broadphaseOccupiedCells || 0,
    warmStartedContacts: prior.warmStartedContacts || 0,
    warmStartAppliedImpulse: prior.warmStartAppliedImpulse || 0,
    warmStartCorrectionImpulse: prior.warmStartCorrectionImpulse || 0,
    detectedUniqueContacts: prior.detectedUniqueContacts || 0
  });
  refreshed.energyDelta = Number.isFinite(prior.energyDelta) ? prior.energyDelta : refreshed.energyDelta;
  refreshed.constraintComposerPostStabilized = !!prior.constraintComposerPostStabilized;
  refreshed.contactEvidenceBasis = 'CORE_STAGE_WITH_TEMP_COMPONENT_COLLISION_GROUPS_BEFORE_POST_CONSTRAINT_STABILIZATION';
  refreshed.constraintCollisionIsolation = true;
  refreshed.collisionGroupsRestored = true;
  world.diagnostics = refreshed;
  return refreshed;
}

function validate(world, constraints, options) {
  const composer = Composer.validate(world, constraints || {});
  const errors = (composer.errors || []).slice();
  let prepared = null;
  if (composer.ok) {
    try { prepared = prepare(world, constraints || {}, options || {}); } catch (error) { errors.push(error.message); }
  }
  return {
    ok: errors.length === 0,
    errors,
    componentCount: prepared ? prepared.components.length : 0,
    warnings: (composer.warnings || []).concat([
      'Collision isolation is component-wide across translation mounts, distance joints, distance limits, axis locks, axis limits and fixed-direction locks: every body in one connected constraint component temporarily shares one negative collision group during the donor-core collision stage.',
      'This is not edge-only pair suppression; bodies connected indirectly through the same constraint component also do not collide with each other during that stage.',
      'A component containing any nonzero caller collision.group is skipped rather than silently overriding existing group semantics.',
      'Temporary groups are chosen deterministically from unused negative group ids and restored on the returned world.',
      'The imported donor source remains untouched.'
    ])
  };
}

function step(world, constraints, dt, options) {
  options = options || {};
  const validation = validate(world, constraints, options);
  if (!validation.ok) throw new Error(validation.errors.join('; '));
  const prepared = prepare(world, constraints || {}, options);
  const composed = Composer.step(prepared.world, constraints || {}, dt, options.composer || {});
  const collisionStageWorld = clone(composed.core.worldBeforePostCompositeStabilization);
  const restoredWorld = restoreGroups(composed.world, prepared.receipts);
  const finalDiagnostics = refreshDiagnostics(restoredWorld, composed.world.diagnostics);
  return {
    schema: STEP_SCHEMA,
    ok: true,
    world: restoredWorld,
    constraints: clone(composed.constraints),
    isolationDiagnostics: {
      enabled: prepared.enabled, componentCount: prepared.components.length, appliedComponents: prepared.appliedComponents,
      skippedComponents: prepared.skippedComponents, isolatedBodies: prepared.isolatedBodies, receipts: clone(prepared.receipts),
      groupsRestored: true, contactEvidenceBasis: finalDiagnostics.contactEvidenceBasis
    },
    composerDiagnostics: clone(composed.composerDiagnostics),
    core: { diagnostics: clone(composed.core.diagnostics), events: clone(composed.core.events), worldAsIntegratedWithTemporaryGroups: collisionStageWorld },
    evidence: [
      prepared.components.length + ' connected constraint component(s) discovered across six supported translation-only constraint families in deterministic body-id order',
      prepared.appliedComponents + ' component(s) received unused temporary negative collision groups for the donor-core collision stage',
      prepared.skippedComponents + ' component(s) skipped isolation rather than overriding existing collision-group semantics',
      'Composer executed one preserved AXM Physics Core v' + Core.VERSION + ' collision/integration step',
      'Caller collision groups restored on the returned world after constraint stabilization',
      'Final restored-world checksum ' + Core.checksum(restoredWorld)
    ],
    limitations: [
      'Isolation suppresses collisions for whole connected constraint components, not only directly constrained edges.',
      'Components containing any nonzero caller collision.group are intentionally skipped.',
      'Category and mask filters are preserved; this layer only uses temporary negative group ids that were unused in the caller world.',
      'Core contact evidence describes the collision stage while temporary groups were active; the returned world has caller groups restored afterward.',
      'Translation mounts, center-to-center distance joints, center-distance limits, world-axis translation locks, world-axis translation limits and fixed world-space direction locks are understood; no additional joint families are implied.',
      'Distance-limit slack semantics remain unchanged: a limit edge participates in component discovery even while its range interior is physically unconstrained.',
      'Axis-lock edges participate in component topology even though their orthogonal translation remains physically free.',
      'Axis-limit edges participate in component topology even while their allowed interval is physically slack.',
      'Direction-lock edges participate in component topology even though perpendicular translation remains physically free and the direction stays fixed in world space.',
      'No angular inertia, rotating local anchors, hinge, full slider/prismatic, rotational weld, motor or gear semantics are implemented.',
      'This is game/prototype physics evidence, not scientific validation.'
    ]
  };
}

function simulate(world, constraints, steps, dt, options) {
  let out = clone(world);
  const count = Math.max(1, Math.min(100000, Math.round(Number.isFinite(Number(steps)) ? Number(steps) : 1)));
  let last = null;
  for (let index = 0; index < count; index++) { last = step(out, constraints, dt, options || {}); out = last.world; }
  return {
    schema: SIMULATION_SCHEMA, ok: true, steps: count, world: out,
    constraints: last ? last.constraints : Composer.normalizeConstraints(out, constraints || {}),
    isolationDiagnostics: last ? last.isolationDiagnostics : null,
    checksum: Core.checksum(out), evidence: (last ? last.evidence : []).concat([count + ' collision-isolated composed step(s) completed'])
  };
}

module.exports = { VERSION, STEP_SCHEMA, SIMULATION_SCHEMA, MAX_TEMP_GROUPS, connectedComponents, prepare, restoreGroups, validate, step, simulate };
