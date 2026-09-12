(function (root, factory) {
  const api = factory(
    typeof require === 'function' ? require('./playground-core.js') : root.AXMGrammarGlassPlaygroundCore
  );
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMGrammarGlassConstructionProgramCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Playground) {
  'use strict';

  const MAX_MODULES = 12;
  const MAX_OPERATIONS = 128;
  const OPS = Object.freeze(['SET', 'INCREMENT', 'TRANSITION', 'ASSERT_EQ', 'EMIT_SIGNAL']);
  const BAD_SEGMENTS = new Set(['__proto__', 'prototype', 'constructor']);

  function canon(value) { return Playground.canon(value); }
  function sha256(value) { return Playground.sha256(value); }
  function freeze(value) { if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.freeze(value); for (const child of Object.values(value)) freeze(child); } return value; }
  function clone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }
  function uniqSorted(values) { return [...new Set((values || []).map(String))].sort(); }
  function pathParts(path) {
    const parts = String(path || '').split('.').filter(Boolean);
    if (!parts.length || parts.some(part => BAD_SEGMENTS.has(part) || !/^[A-Za-z0-9_-]+$/.test(part))) throw Error('CONSTRUCTION_PROGRAM_PATH_INVALID');
    return parts;
  }
  function getPath(state, path) { let cur = state; for (const part of pathParts(path)) { if (cur == null || typeof cur !== 'object' || !(part in cur)) return undefined; cur = cur[part]; } return cur; }
  function setPath(state, path, value) {
    const parts = pathParts(path); let cur = state;
    for (let i = 0; i < parts.length - 1; i += 1) {
      const part = parts[i];
      if (cur[part] == null) cur[part] = {};
      if (typeof cur[part] !== 'object' || Array.isArray(cur[part])) throw Error('CONSTRUCTION_PROGRAM_PATH_NOT_OBJECT');
      cur = cur[part];
    }
    cur[parts[parts.length - 1]] = clone(value);
  }
  function opAccess(operation) {
    const op = operation?.op;
    if (!OPS.includes(op)) throw Error('CONSTRUCTION_PROGRAM_OPERATION_INVALID');
    if (op === 'EMIT_SIGNAL') {
      if (!operation.signal || !/^[A-Za-z0-9_.:-]+$/.test(String(operation.signal))) throw Error('CONSTRUCTION_PROGRAM_SIGNAL_INVALID');
      return { reads: [], writes: [], signals: [String(operation.signal)] };
    }
    const path = String(operation.path || ''); pathParts(path);
    if (op === 'SET') return { reads: [], writes: [path], signals: [] };
    if (op === 'ASSERT_EQ') return { reads: [path], writes: [], signals: [] };
    return { reads: [path], writes: [path], signals: [] };
  }
  function normalizeModule(module) {
    if (!module?.id || !/^[A-Za-z0-9_.:-]+$/.test(String(module.id))) throw Error('CONSTRUCTION_PROGRAM_MODULE_ID_INVALID');
    const operations = (module.operations || []).map(operation => clone(operation));
    if (!operations.length) throw Error('CONSTRUCTION_PROGRAM_MODULE_OPERATIONS_REQUIRED');
    const reads = uniqSorted(module.reads), writes = uniqSorted(module.writes), dependencies = uniqSorted(module.dependsOn), effects = uniqSorted(module.effects);
    reads.forEach(pathParts); writes.forEach(pathParts);
    for (const operation of operations) {
      const access = opAccess(operation);
      for (const path of access.reads) if (!reads.includes(path)) throw Error(`CONSTRUCTION_PROGRAM_UNDECLARED_READ:${module.id}:${path}`);
      for (const path of access.writes) if (!writes.includes(path)) throw Error(`CONSTRUCTION_PROGRAM_UNDECLARED_WRITE:${module.id}:${path}`);
      for (const signal of access.signals) if (!effects.includes(signal)) throw Error(`CONSTRUCTION_PROGRAM_UNDECLARED_EFFECT:${module.id}:${signal}`);
    }
    const core = { id: String(module.id), reads, writes, dependsOn: dependencies, effects, operations };
    return { ...core, moduleSha256: sha256(core) };
  }
  function topo(modules) {
    const byId = new Map(modules.map(module => [module.id, module]));
    const indegree = new Map(modules.map(module => [module.id, 0]));
    const children = new Map(modules.map(module => [module.id, []]));
    for (const module of modules) {
      for (const dep of module.dependsOn) {
        if (!byId.has(dep)) throw Error(`CONSTRUCTION_PROGRAM_UNKNOWN_DEPENDENCY:${module.id}:${dep}`);
        if (dep === module.id) throw Error('CONSTRUCTION_PROGRAM_SELF_DEPENDENCY');
        indegree.set(module.id, indegree.get(module.id) + 1);
        children.get(dep).push(module.id);
      }
    }
    const ready = [...indegree.entries()].filter(([, degree]) => degree === 0).map(([id]) => id).sort();
    const order = [];
    while (ready.length) {
      const id = ready.shift(); order.push(id);
      for (const child of children.get(id).sort()) {
        indegree.set(child, indegree.get(child) - 1);
        if (indegree.get(child) === 0) { ready.push(child); ready.sort(); }
      }
    }
    if (order.length !== modules.length) throw Error('CONSTRUCTION_PROGRAM_DEPENDENCY_CYCLE');
    return order;
  }
  function ancestors(modules) {
    const byId = new Map(modules.map(module => [module.id, module]));
    const memo = new Map();
    function collect(id) {
      if (memo.has(id)) return memo.get(id);
      const set = new Set();
      for (const dep of byId.get(id).dependsOn) { set.add(dep); for (const item of collect(dep)) set.add(item); }
      memo.set(id, set); return set;
    }
    for (const module of modules) collect(module.id);
    return memo;
  }
  function pathOverlaps(left, right) {
    const leftParts = pathParts(left), rightParts = pathParts(right);
    const sharedLength = Math.min(leftParts.length, rightParts.length);
    for (let index = 0; index < sharedLength; index += 1) {
      if (leftParts[index] !== rightParts[index]) return false;
    }
    return true;
  }
  function checkWriteOrdering(modules) {
    const ancestry = ancestors(modules);
    for (let i = 0; i < modules.length; i += 1) for (let j = i + 1; j < modules.length; j += 1) {
      const a = modules[i], b = modules[j];
      const overlap = a.writes.flatMap(left => b.writes.filter(right => pathOverlaps(left, right)).map(right => [left, right]))[0];
      if (overlap && !ancestry.get(a.id).has(b.id) && !ancestry.get(b.id).has(a.id)) {
        const paths = overlap[0] === overlap[1] ? overlap[0] : `${overlap[0]}:${overlap[1]}`;
        throw Error(`CONSTRUCTION_PROGRAM_AMBIGUOUS_WRITE_ORDER:${a.id}:${b.id}:${paths}`);
      }
    }
  }
  function createProgram({ programId = 'grammar-glass-construction-program', modules = [], requiredEffects = [], binding = null } = {}) {
    if (!programId || !/^[A-Za-z0-9_.:-]+$/.test(String(programId))) throw Error('CONSTRUCTION_PROGRAM_ID_INVALID');
    if (!Array.isArray(modules) || !modules.length || modules.length > MAX_MODULES) throw Error('CONSTRUCTION_PROGRAM_MODULE_COUNT_INVALID');
    const normalized = modules.map(normalizeModule);
    if (new Set(normalized.map(module => module.id)).size !== normalized.length) throw Error('CONSTRUCTION_PROGRAM_DUPLICATE_MODULE_ID');
    const operationCount = normalized.reduce((sum, module) => sum + module.operations.length, 0);
    if (operationCount > MAX_OPERATIONS) throw Error('CONSTRUCTION_PROGRAM_OPERATION_CEILING_EXCEEDED');
    const topologicalOrder = topo(normalized); checkWriteOrdering(normalized);
    const effects = uniqSorted(requiredEffects);
    const allDeclaredEffects = new Set(normalized.flatMap(module => module.effects));
    for (const effect of effects) if (!allDeclaredEffects.has(effect)) throw Error(`CONSTRUCTION_PROGRAM_REQUIRED_EFFECT_UNDECLARED:${effect}`);
    const core = {
      schema: 'axm.code.grammar-glass-construction-program.v1', version: '1.0.0', result: 'BOUNDED_CONSTRUCTION_PROGRAM_READY_NOT_EXECUTED',
      programId: String(programId), binding: binding == null ? null : clone(binding), moduleCount: normalized.length, operationCount,
      modules: normalized, topologicalOrder, requiredEffects: effects,
      executionContract: { transientJsonStateOnly: true, arbitraryCodeExecution: false, eval: false, dynamicImport: false, filesystem: false, network: false, process: false, dom: false, maximumModules: MAX_MODULES, maximumOperations: MAX_OPERATIONS },
      truth: { declaredReadsEnforced: true, declaredWritesEnforced: true, dependencyOrderEnforced: true, ambiguousConcurrentWritesRejected: true, emittedEffectRequiresCommittedStateChangeForConvergenceCredit: true, programIsNotSourceCode: true, programIsNotOsSandbox: true, automaticExecution: false, automaticPromotion: false },
      authority: 'TRANSIENT_PROGRAM_STATE_ONLY'
    };
    return freeze({ ...core, programSha256: sha256(core) });
  }
  function validProgram(program) {
    if (!program || program.schema !== 'axm.code.grammar-glass-construction-program.v1' || !program.programSha256) return false;
    try {
      const rebuilt = createProgram({ programId: program.programId, modules: program.modules, requiredEffects: program.requiredEffects, binding: program.binding });
      return rebuilt.programSha256 === program.programSha256 && canon(rebuilt) === canon(program);
    } catch { return false; }
  }
  function execute(program, initialState = {}) {
    if (!validProgram(program)) throw Error('VALID_CONSTRUCTION_PROGRAM_REQUIRED');
    const state = clone(initialState); const byId = new Map(program.modules.map(module => [module.id, module]));
    const receipts = []; const realizedEffects = new Set();
    for (const id of program.topologicalOrder) {
      const module = byId.get(id), staged = clone(state), signals = [], before = sha256(state); let failure = null;
      for (const operation of module.operations) {
        try {
          if (operation.op === 'SET') setPath(staged, operation.path, operation.value);
          else if (operation.op === 'INCREMENT') {
            const current = getPath(staged, operation.path), by = Number(operation.by);
            if (!Number.isFinite(current) || !Number.isFinite(by)) throw Error('INCREMENT_REQUIRES_FINITE_NUMBER');
            setPath(staged, operation.path, current + by);
          } else if (operation.op === 'TRANSITION') {
            const current = getPath(staged, operation.path);
            if (canon(current) !== canon(operation.from)) throw Error('TRANSITION_FROM_MISMATCH');
            setPath(staged, operation.path, operation.to);
          } else if (operation.op === 'ASSERT_EQ') {
            if (canon(getPath(staged, operation.path)) !== canon(operation.value)) throw Error('ASSERT_EQ_FAILED');
          } else if (operation.op === 'EMIT_SIGNAL') signals.push(String(operation.signal));
        } catch (error) { failure = error.message || String(error); break; }
      }
      if (failure) {
        const core = { moduleId: id, moduleSha256: module.moduleSha256, result: 'MODULE_HELD_NO_COMMIT', failure, beforeStateSha256: before, afterStateSha256: before, emittedSignals: [], committedStateChange: false };
        receipts.push({ ...core, receiptSha256: sha256(core) });
        const finalCore = { schema: 'axm.code.grammar-glass-construction-program-execution.v1', version: '1.0.0', result: 'PROGRAM_HELD_MODULE_FAILURE', programSha256: program.programSha256, finalState: state, finalStateSha256: sha256(state), realizedEffects: [...realizedEffects].sort(), missingRequiredEffects: program.requiredEffects.filter(effect => !realizedEffects.has(effect)), receipts, truth: { executionWasExplicitFunctionCall: true, priorCommittedPrefixPreserved: true, failedModuleDidNotCommit: true, externalSideEffects: false, sourceExecution: false, automaticPromotion: false }, authority: 'TRANSIENT_PROGRAM_STATE_ONLY' };
        return freeze({ ...finalCore, executionSha256: sha256(finalCore) });
      }
      const after = sha256(staged), changed = after !== before;
      for (const key of Object.keys(state)) delete state[key]; Object.assign(state, staged);
      if (changed) for (const signal of signals) realizedEffects.add(signal);
      const core = { moduleId: id, moduleSha256: module.moduleSha256, result: 'MODULE_COMMITTED', failure: null, beforeStateSha256: before, afterStateSha256: after, emittedSignals: signals, committedStateChange: changed };
      receipts.push({ ...core, receiptSha256: sha256(core) });
    }
    const missing = program.requiredEffects.filter(effect => !realizedEffects.has(effect));
    const finalCore = { schema: 'axm.code.grammar-glass-construction-program-execution.v1', version: '1.0.0', result: missing.length ? 'PROGRAM_HELD_REQUIRED_EFFECTS_MISSING' : 'PROGRAM_TRANSIENT_EXECUTION_COMPLETE', programSha256: program.programSha256, finalState: state, finalStateSha256: sha256(state), realizedEffects: [...realizedEffects].sort(), missingRequiredEffects: missing, receipts, truth: { executionWasExplicitFunctionCall: true, externalSideEffects: false, sourceExecution: false, runtimeNetworkAccess: false, runtimeFilesystemAccess: false, automaticPromotion: false }, authority: 'TRANSIENT_PROGRAM_STATE_ONLY' };
    return freeze({ ...finalCore, executionSha256: sha256(finalCore) });
  }

  return Object.freeze({ MAX_MODULES, MAX_OPERATIONS, OPS, canon, sha256, createProgram, validProgram, execute });
});
