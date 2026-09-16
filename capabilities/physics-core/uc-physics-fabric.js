'use strict';

function buildPhysicsFabric(Core) {
  if (!Core || typeof Core.createWorld !== 'function' || typeof Core.step !== 'function') {
    throw new Error('AXM Physics Core is required');
  }

  const VERSION = '0.1.0';
  const FABRIC_SCHEMA = 'axm.uc-physics-fabric/v0.1';
  const STEP_SCHEMA = 'axm.uc-physics-step/v0.1';
  const TRACE_SCHEMA = 'axm.uc-physics-trace/v0.1';
  const ADAPTER_ID = 'axm-uc-physics-fabric';
  const MAX_TRACE_FRAMES = 2000;
  const MAX_COLLECTION = 4096;

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function finite(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function bounded(value, min, max, fallback) {
    return Math.max(min, Math.min(max, finite(value, fallback)));
  }

  function text(value, fallback) {
    const s = value == null ? '' : String(value).trim();
    return s || fallback;
  }

  function vector(value, fallback) {
    const v = value || {};
    const f = fallback || { x: 0, y: 0 };
    return { x: finite(v.x, f.x), y: finite(v.y, f.y) };
  }

  function magnitude(v) {
    return Math.hypot(v.x, v.y);
  }

  function normalize(v, fallback) {
    const m = magnitude(v);
    if (m > 1e-12) return { x: v.x / m, y: v.y / m };
    return fallback || { x: 1, y: 0 };
  }

  function dot(a, b) {
    return a.x * b.x + a.y * b.y;
  }

  function sortById(values) {
    return values.slice().sort((a, b) => String(a.id).localeCompare(String(b.id)));
  }

  function ensureLimit(values, label) {
    if (!Array.isArray(values)) return [];
    if (values.length > MAX_COLLECTION) throw new Error(label + ' limit exceeded');
    return values;
  }

  function normalizeMaterial(input, fallbackId) {
    input = input || {};
    const out = {
      id: text(input.id, fallbackId || 'material-default'),
      friction: bounded(input.friction, 0, 2, 0.45),
      restitution: bounded(input.restitution, 0, 1, 0.25),
      linearDamping: bounded(input.linearDamping, 0, 0.999, 0.01),
      gravityScale: bounded(input.gravityScale, -20, 20, 1)
    };
    if (input.density != null) out.density = bounded(input.density, 0.000001, 1e9, 1);
    if (input.mass != null) out.mass = bounded(input.mass, 0.000001, 1e9, 1);
    if (input.userData != null) out.userData = clone(input.userData);
    return out;
  }

  function materialMap(materials) {
    const out = {};
    const list = Array.isArray(materials)
      ? materials
      : Object.keys(materials || {}).map(id => Object.assign({ id }, materials[id]));
    ensureLimit(list, 'material');
    list.forEach((material, index) => {
      const normalized = normalizeMaterial(material, 'material-' + String(index + 1).padStart(3, '0'));
      if (out[normalized.id]) throw new Error('duplicate material id ' + normalized.id);
      out[normalized.id] = normalized;
    });
    return out;
  }

  function shapeArea(shape) {
    if (!shape) return 1;
    if (shape.kind === 'circle') {
      const r = bounded(shape.radius, 0.001, 1e6, 0.5);
      return Math.PI * r * r;
    }
    if (shape.kind === 'box') {
      const hw = bounded(shape.halfWidth, 0.001, 1e6, 0.5);
      const hh = bounded(shape.halfHeight, 0.001, 1e6, 0.5);
      return 4 * hw * hh;
    }
    return 1;
  }

  function materializeBody(input, materials) {
    const body = clone(input || {});
    const materialId = text(body.materialId || body.material, '');
    const material = materialId ? materials[materialId] : null;
    if (materialId && !material) throw new Error('unknown material ' + materialId);
    if (material) {
      ['friction', 'restitution', 'linearDamping', 'gravityScale'].forEach(key => {
        if (body[key] == null && material[key] != null) body[key] = material[key];
      });
      if ((body.type || 'dynamic') === 'dynamic' && body.mass == null) {
        if (material.mass != null) body.mass = material.mass;
        else if (material.density != null) body.mass = material.density * shapeArea(body.shape);
      }
      body.userData = Object.assign({}, material.userData || {}, body.userData || {}, { materialId });
    }
    delete body.material;
    delete body.materialId;
    return body;
  }

  function normalizeRegion(region) {
    if (!region) return null;
    if (region.kind === 'circle') {
      return {
        kind: 'circle',
        center: vector(region.center),
        radius: bounded(region.radius, 0.000001, 1e9, 1)
      };
    }
    if (region.kind === 'box') {
      return {
        kind: 'box',
        center: vector(region.center),
        halfWidth: bounded(region.halfWidth, 0.000001, 1e9, 1),
        halfHeight: bounded(region.halfHeight, 0.000001, 1e9, 1)
      };
    }
    throw new Error('unsupported field region kind ' + region.kind);
  }

  function normalizeField(input, index) {
    input = input || {};
    const kind = ['uniform', 'radial', 'vortex', 'drag'].includes(input.kind) ? input.kind : 'uniform';
    const out = {
      id: text(input.id, 'field-' + String(index + 1).padStart(3, '0')),
      kind,
      enabled: input.enabled !== false,
      region: normalizeRegion(input.region)
    };
    if (kind === 'uniform') out.acceleration = vector(input.acceleration, { x: 0, y: 0 });
    if (kind === 'drag') out.coefficient = bounded(input.coefficient, 0, 1e6, 0.1);
    if (kind === 'radial' || kind === 'vortex') {
      out.center = vector(input.center);
      out.strength = finite(input.strength, 1);
      out.falloff = ['none', 'linear', 'inverse-square'].includes(input.falloff) ? input.falloff : 'none';
      out.radius = input.radius == null ? null : bounded(input.radius, 0.000001, 1e9, 1);
      out.minDistance = bounded(input.minDistance, 0.000001, 1e9, 0.1);
    }
    return out;
  }

  function normalizeDriver(input, index) {
    input = input || {};
    const kind = input.kind === 'seek' ? 'seek' : 'velocity';
    const out = {
      id: text(input.id, 'driver-' + String(index + 1).padStart(3, '0')),
      kind,
      bodyId: text(input.bodyId, ''),
      enabled: input.enabled !== false
    };
    if (!out.bodyId) throw new Error('driver bodyId required');
    if (kind === 'velocity') out.velocity = vector(input.velocity);
    else {
      out.target = vector(input.target);
      out.speed = bounded(input.speed, 0, 1e9, 1);
      out.arriveRadius = bounded(input.arriveRadius, 0, 1e9, 0.05);
    }
    return out;
  }

  function getBody(world, id) {
    return (world.bodies || []).find(body => body.id === id) || null;
  }

  function normalizeSpring(input, index, world) {
    input = input || {};
    const a = text(input.a, '');
    const b = text(input.b, '');
    if (!a || !b || a === b) throw new Error('spring requires distinct a and b body ids');
    const bodyA = getBody(world, a);
    const bodyB = getBody(world, b);
    if (!bodyA || !bodyB) throw new Error('spring body not found: ' + (!bodyA ? a : b));
    const currentDistance = Math.hypot(bodyB.position.x - bodyA.position.x, bodyB.position.y - bodyA.position.y);
    return {
      id: text(input.id, 'spring-' + String(index + 1).padStart(3, '0')),
      kind: 'spring-distance',
      a,
      b,
      restLength: bounded(input.restLength, 0, 1e9, currentDistance),
      stiffness: bounded(input.stiffness, 0, 1e9, 20),
      damping: bounded(input.damping, 0, 1e9, 2),
      maxForce: bounded(input.maxForce, 0, 1e12, 1e6),
      enabled: input.enabled !== false
    };
  }

  function normalizeAction(input, index) {
    input = input || {};
    const supported = ['apply-force', 'apply-impulse', 'set-velocity', 'set-gravity', 'set-enabled', 'teleport'];
    if (!supported.includes(input.kind)) throw new Error('unsupported physics action ' + input.kind);
    const out = {
      id: text(input.id, 'action-' + String(index + 1).padStart(3, '0')),
      kind: input.kind,
      atStep: Math.max(1, Math.round(finite(input.atStep, 1))),
      executed: !!input.executed
    };
    if (input.bodyId != null) out.bodyId = text(input.bodyId, '');
    if (input.force != null) out.force = vector(input.force);
    if (input.impulse != null) out.impulse = vector(input.impulse);
    if (input.velocity != null) out.velocity = vector(input.velocity);
    if (input.gravity != null) out.gravity = vector(input.gravity);
    if (input.position != null) out.position = vector(input.position);
    if (input.enabled != null) out.enabled = !!input.enabled;
    if (input.zeroVelocity != null) out.zeroVelocity = !!input.zeroVelocity;
    return out;
  }

  function ensureUniqueIds(values, label) {
    const seen = new Set();
    values.forEach(value => {
      if (seen.has(value.id)) throw new Error('duplicate ' + label + ' id ' + value.id);
      seen.add(value.id);
    });
  }

  function refreshFabricDiagnostics(fabric) {
    const coreValidation = Core.validate(fabric.world);
    fabric.diagnostics = {
      status: coreValidation.ok ? 'READY' : 'INVALID',
      coreVersion: Core.VERSION,
      bodyCount: fabric.world.bodies.length,
      materialCount: Object.keys(fabric.materials).length,
      fieldCount: fabric.fields.length,
      springCount: fabric.springs.length,
      driverCount: fabric.drivers.length,
      pendingActionCount: fabric.actions.filter(action => !action.executed).length,
      executedActionCount: fabric.actions.filter(action => action.executed).length,
      checksum: Core.checksum(fabric.world),
      coreValidation
    };
    return fabric;
  }

  function createFabric(input) {
    input = input || {};
    const materials = materialMap(input.materials || []);
    let world = Core.createWorld(input.world || input.worldConfig || {});
    const bodies = ensureLimit(input.bodies || [], 'body');
    bodies.forEach(body => {
      world = Core.addBody(world, materializeBody(body, materials)).world;
    });
    const fields = ensureLimit(input.fields || [], 'field').map(normalizeField);
    const drivers = ensureLimit(input.drivers || [], 'driver').map(normalizeDriver);
    const springs = ensureLimit(input.springs || [], 'spring').map((spring, index) => normalizeSpring(spring, index, world));
    const actions = ensureLimit(input.actions || [], 'action').map(normalizeAction);
    ensureUniqueIds(fields, 'field');
    ensureUniqueIds(drivers, 'driver');
    ensureUniqueIds(springs, 'spring');
    ensureUniqueIds(actions, 'action');
    const fabric = {
      schema: FABRIC_SCHEMA,
      version: VERSION,
      core: { id: 'axm-physics-2d', version: Core.VERSION },
      world,
      materials,
      fields: sortById(fields),
      springs: sortById(springs),
      drivers: sortById(drivers),
      actions: actions.slice().sort((a, b) => a.atStep - b.atStep || a.id.localeCompare(b.id)),
      metadata: clone(input.metadata || {}),
      diagnostics: null
    };
    return refreshFabricDiagnostics(fabric);
  }

  function validateFabric(fabric) {
    const errors = [];
    if (!fabric || fabric.schema !== FABRIC_SCHEMA) errors.push('fabric schema must be ' + FABRIC_SCHEMA);
    if (!fabric || !fabric.world) errors.push('fabric world required');
    if (fabric && fabric.world) {
      const core = Core.validate(fabric.world);
      errors.push.apply(errors, core.errors || []);
    }
    return {
      ok: errors.length === 0,
      errors,
      warnings: [
        'UC Physics Fabric extends the imported deterministic 2D prototype core; it does not claim scientific validation, rigid-body rotation, rigid joints, deformables, fluids or 3D physics.',
        'Spring-distance constraints are force-based springs, not hard rigid joints.'
      ]
    };
  }

  function addBody(fabric, body) {
    const out = clone(fabric);
    const validation = validateFabric(out);
    if (!validation.ok) throw new Error(validation.errors.join('; '));
    out.world = Core.addBody(out.world, materializeBody(body, out.materials || {})).world;
    return refreshFabricDiagnostics(out);
  }

  function addBodies(fabric, bodies) {
    let out = clone(fabric);
    ensureLimit(bodies || [], 'body').forEach(body => {
      out = addBody(out, body);
    });
    return out;
  }

  function regionContains(region, position) {
    if (!region) return true;
    if (region.kind === 'circle') {
      const dx = position.x - region.center.x;
      const dy = position.y - region.center.y;
      return dx * dx + dy * dy <= region.radius * region.radius;
    }
    return Math.abs(position.x - region.center.x) <= region.halfWidth &&
      Math.abs(position.y - region.center.y) <= region.halfHeight;
  }

  function fieldFalloff(field, distance) {
    if (field.radius != null && distance > field.radius) return 0;
    if (field.falloff === 'linear' && field.radius != null) return Math.max(0, 1 - distance / field.radius);
    if (field.falloff === 'inverse-square') {
      const d = Math.max(field.minDistance || 0.1, distance);
      return 1 / (d * d);
    }
    return 1;
  }

  function fieldAcceleration(field, body) {
    if (!field.enabled || !regionContains(field.region, body.position)) return { x: 0, y: 0 };
    if (field.kind === 'uniform') return clone(field.acceleration);
    if (field.kind === 'drag') {
      return { x: -body.velocity.x * field.coefficient, y: -body.velocity.y * field.coefficient };
    }
    const offset = { x: body.position.x - field.center.x, y: body.position.y - field.center.y };
    const distance = magnitude(offset);
    const scale = fieldFalloff(field, distance) * field.strength;
    if (Math.abs(scale) <= 1e-15) return { x: 0, y: 0 };
    const radial = normalize(offset, { x: 1, y: 0 });
    if (field.kind === 'radial') return { x: radial.x * scale, y: radial.y * scale };
    return { x: -radial.y * scale, y: radial.x * scale };
  }

  function accumulateForce(map, bodyId, force) {
    const current = map[bodyId] || (map[bodyId] = { x: 0, y: 0 });
    current.x += force.x;
    current.y += force.y;
  }

  function collectFieldForces(fabric, map) {
    const applied = [];
    sortById(fabric.fields || []).forEach(field => {
      let affected = 0;
      fabric.world.bodies.forEach(body => {
        if (body.type !== 'dynamic' || !body.enabled || body.sleeping) return;
        const acceleration = fieldAcceleration(field, body);
        if (Math.abs(acceleration.x) <= 1e-15 && Math.abs(acceleration.y) <= 1e-15) return;
        const mass = finite(body.mass, 0);
        if (!(mass > 0)) return;
        accumulateForce(map, body.id, { x: acceleration.x * mass, y: acceleration.y * mass });
        affected++;
      });
      applied.push({ id: field.id, kind: field.kind, affectedBodies: affected });
    });
    return applied;
  }

  function collectSpringForces(fabric, map) {
    const applied = [];
    sortById(fabric.springs || []).forEach(spring => {
      if (!spring.enabled) return;
      const a = getBody(fabric.world, spring.a);
      const b = getBody(fabric.world, spring.b);
      if (!a || !b) throw new Error('spring body missing for ' + spring.id);
      const delta = { x: b.position.x - a.position.x, y: b.position.y - a.position.y };
      const distance = magnitude(delta);
      const axis = normalize(delta, { x: 1, y: 0 });
      const relativeVelocity = { x: b.velocity.x - a.velocity.x, y: b.velocity.y - a.velocity.y };
      const relativeAlong = dot(relativeVelocity, axis);
      const extension = distance - spring.restLength;
      let forceMagnitude = spring.stiffness * extension + spring.damping * relativeAlong;
      forceMagnitude = Math.max(-spring.maxForce, Math.min(spring.maxForce, forceMagnitude));
      const force = { x: axis.x * forceMagnitude, y: axis.y * forceMagnitude };
      if (a.type === 'dynamic' && a.enabled) accumulateForce(map, a.id, force);
      if (b.type === 'dynamic' && b.enabled) accumulateForce(map, b.id, { x: -force.x, y: -force.y });
      applied.push({
        id: spring.id,
        a: spring.a,
        b: spring.b,
        distance,
        extension,
        forceMagnitude
      });
    });
    return applied;
  }

  function applyCombinedForces(fabric) {
    const map = {};
    const fields = collectFieldForces(fabric, map);
    const springs = collectSpringForces(fabric, map);
    let world = fabric.world;
    Object.keys(map).sort().forEach(bodyId => {
      world = Core.applyForce(world, bodyId, map[bodyId]);
    });
    fabric.world = world;
    return { fields, springs, bodyForces: clone(map) };
  }

  function applyDrivers(fabric) {
    let world = fabric.world;
    const receipts = [];
    sortById(fabric.drivers || []).forEach(driver => {
      if (!driver.enabled) return;
      const body = getBody(world, driver.bodyId);
      if (!body) throw new Error('driver body not found: ' + driver.bodyId);
      let velocity;
      if (driver.kind === 'velocity') velocity = driver.velocity;
      else {
        const delta = { x: driver.target.x - body.position.x, y: driver.target.y - body.position.y };
        const distance = magnitude(delta);
        velocity = distance <= driver.arriveRadius
          ? { x: 0, y: 0 }
          : { x: normalize(delta).x * driver.speed, y: normalize(delta).y * driver.speed };
      }
      world = Core.setVelocity(world, driver.bodyId, velocity);
      receipts.push({ id: driver.id, bodyId: driver.bodyId, kind: driver.kind, velocity: clone(velocity) });
    });
    fabric.world = world;
    return receipts;
  }

  function executeAction(fabric, action, upcomingStep) {
    let world = fabric.world;
    if (action.kind === 'apply-force') world = Core.applyForce(world, action.bodyId, action.force || { x: 0, y: 0 });
    else if (action.kind === 'apply-impulse') world = Core.applyImpulse(world, action.bodyId, action.impulse || { x: 0, y: 0 });
    else if (action.kind === 'set-velocity') world = Core.setVelocity(world, action.bodyId, action.velocity || { x: 0, y: 0 });
    else if (action.kind === 'set-gravity') world.gravity = vector(action.gravity, world.gravity);
    else if (action.kind === 'set-enabled') {
      const body = getBody(world, action.bodyId);
      if (!body) throw new Error('action body not found: ' + action.bodyId);
      body.enabled = !!action.enabled;
      if (body.enabled) { body.sleeping = false; body.sleepFrames = 0; }
    } else if (action.kind === 'teleport') {
      const body = getBody(world, action.bodyId);
      if (!body) throw new Error('action body not found: ' + action.bodyId);
      body.position = vector(action.position, body.position);
      if (action.zeroVelocity) body.velocity = { x: 0, y: 0 };
      body.sleeping = false;
      body.sleepFrames = 0;
    }
    fabric.world = world;
    action.executed = true;
    action.executedAtStep = upcomingStep;
    return { id: action.id, kind: action.kind, executedAtStep: upcomingStep };
  }

  function executeScheduledActions(fabric) {
    const upcomingStep = (fabric.world.stepIndex || 0) + 1;
    const receipts = [];
    fabric.actions.forEach(action => {
      if (!action.executed && action.atStep <= upcomingStep) receipts.push(executeAction(fabric, action, upcomingStep));
    });
    return receipts;
  }

  function stepFabric(fabric, dt) {
    const out = clone(fabric);
    const validation = validateFabric(out);
    if (!validation.ok) throw new Error(validation.errors.join('; '));
    const actions = executeScheduledActions(out);
    const drivers = applyDrivers(out);
    const forces = applyCombinedForces(out);
    const coreStep = Core.step(out.world, dt);
    out.world = coreStep.world;
    refreshFabricDiagnostics(out);
    return {
      schema: STEP_SCHEMA,
      ok: true,
      fabric: out,
      world: clone(out.world),
      diagnostics: clone(out.diagnostics),
      receipts: { actions, drivers, fields: forces.fields, springs: forces.springs, bodyForces: forces.bodyForces },
      core: { diagnostics: clone(coreStep.diagnostics), events: clone(coreStep.events) },
      evidence: [
        actions.length + ' scheduled action(s) executed before core step ' + out.world.stepIndex,
        drivers.length + ' deterministic driver(s) applied',
        forces.fields.length + ' force field(s) evaluated',
        forces.springs.length + ' spring-distance constraint(s) evaluated',
        'Imported AXM Physics Core v' + Core.VERSION + ' executed the collision/integration step',
        'State checksum ' + Core.checksum(out.world)
      ]
    };
  }

  function simulateFabric(fabric, steps, dt, sampleEvery) {
    let out = clone(fabric);
    const count = Math.max(1, Math.min(100000, Math.round(finite(steps, 1))));
    const every = Math.max(1, Math.min(count, Math.round(finite(sampleEvery, 1))));
    const frames = [];
    let last = null;
    function capture() {
      if (frames.length >= MAX_TRACE_FRAMES) throw new Error('UC physics trace frame limit exceeded');
      frames.push({
        stepIndex: out.world.stepIndex,
        time: out.world.time,
        checksum: Core.checksum(out.world),
        bodies: out.world.bodies.map(body => ({
          id: body.id,
          position: clone(body.position),
          velocity: clone(body.velocity),
          sleeping: !!body.sleeping
        }))
      });
    }
    capture();
    for (let index = 0; index < count; index++) {
      last = stepFabric(out, dt);
      out = last.fabric;
      if ((index + 1) % every === 0 || index === count - 1) capture();
    }
    return {
      schema: TRACE_SCHEMA,
      ok: true,
      steps: count,
      sampleEvery: every,
      frames,
      fabric: out,
      diagnostics: clone(out.diagnostics),
      finalChecksum: Core.checksum(out.world),
      evidence: (last ? last.evidence : []).concat([count + ' UC physics fabric step(s) completed'])
    };
  }

  function inspectFabric(fabric) {
    const validation = validateFabric(fabric);
    return {
      schema: 'axm.uc-physics-inspection/v0.1',
      ok: validation.ok,
      validation,
      coreVersion: Core.VERSION,
      counts: {
        bodies: fabric && fabric.world && fabric.world.bodies ? fabric.world.bodies.length : 0,
        materials: fabric && fabric.materials ? Object.keys(fabric.materials).length : 0,
        fields: fabric && fabric.fields ? fabric.fields.length : 0,
        springs: fabric && fabric.springs ? fabric.springs.length : 0,
        drivers: fabric && fabric.drivers ? fabric.drivers.length : 0,
        actions: fabric && fabric.actions ? fabric.actions.length : 0
      },
      checksum: validation.ok ? Core.checksum(fabric.world) : null
    };
  }

  function run(request) {
    request = request || {};
    const capability = request.capability || request.operation || 'inspect-fabric';
    const input = request.input || request;
    if (capability === 'create-fabric') return { ok: true, output: createFabric(input) };
    if (capability === 'add-body') return { ok: true, output: addBody(input.fabric, input.body) };
    if (capability === 'add-bodies') return { ok: true, output: addBodies(input.fabric, input.bodies) };
    if (capability === 'step-fabric') return { ok: true, output: stepFabric(input.fabric, input.dt) };
    if (capability === 'simulate-fabric') return { ok: true, output: simulateFabric(input.fabric, input.steps, input.dt, input.sampleEvery) };
    if (capability === 'inspect-fabric') return { ok: true, output: inspectFabric(input.fabric || input) };
    if (capability === 'query-point') return { ok: true, output: Core.queryPoint(input.fabric.world, input.point) };
    if (capability === 'raycast') return { ok: true, output: Core.raycast(input.fabric.world, input.ray) };
    return { ok: false, error: 'unsupported UC physics capability: ' + capability };
  }

  function adapter() {
    return {
      id: ADAPTER_ID,
      version: VERSION,
      coreVersion: Core.VERSION,
      capabilities: [
        'create-fabric', 'add-body', 'add-bodies', 'step-fabric', 'simulate-fabric',
        'inspect-fabric', 'query-point', 'raycast'
      ],
      run
    };
  }

  return {
    VERSION,
    FABRIC_SCHEMA,
    STEP_SCHEMA,
    TRACE_SCHEMA,
    ADAPTER_ID,
    createFabric,
    validateFabric,
    addBody,
    addBodies,
    stepFabric,
    simulateFabric,
    inspectFabric,
    run,
    adapter
  };
}

const defaultCore = require('./source/axm-physics-core.js');
const api = buildPhysicsFabric(defaultCore);
api.withCore = buildPhysicsFabric;
module.exports = api;
