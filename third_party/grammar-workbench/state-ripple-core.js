(function (root, factory) {
  const api = factory(
    typeof require === 'function' ? require('./construction-program-core.js') : root.AXMGrammarGlassConstructionProgramCore
  );
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.AXMGrammarGlassStateRippleCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Program) {
  'use strict';

  const MAX_NODES = 4096;
  const MAX_OPERATIONS = 32768;
  const OPS = Object.freeze([...(Program.OPS || []), 'COPY', 'SUM']);
  const BAD_SEGMENTS = new Set(['__proto__', 'prototype', 'constructor']);
  const TRUSTED_BASELINES = new WeakSet();

  function canon(value) { return Program.canon(value); }
  function sha256(value) { return Program.sha256(value); }
  function clone(value) { return value == null ? value : JSON.parse(JSON.stringify(value)); }
  function freeze(value) { if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.freeze(value); for (const child of Object.values(value)) freeze(child); } return value; }
  function uniqSorted(values) { return [...new Set((values || []).map(String))].sort(); }
  function pathParts(path) {
    const parts = String(path || '').split('.').filter(Boolean);
    if (!parts.length || parts.some(part => BAD_SEGMENTS.has(part) || !/^[A-Za-z0-9_-]+$/.test(part))) throw Error('STATE_RIPPLE_PATH_INVALID');
    return parts;
  }
  function pathsOverlap(a, b) {
    const aa = pathParts(a), bb = pathParts(b), n = Math.min(aa.length, bb.length);
    for (let i = 0; i < n; i += 1) if (aa[i] !== bb[i]) return false;
    return true;
  }
  function getPath(state, path) {
    let cur = state;
    for (const part of pathParts(path)) {
      if (cur == null || typeof cur !== 'object' || !(part in cur)) return { present: false, value: null };
      cur = cur[part];
    }
    return { present: true, value: clone(cur) };
  }
  function setPath(state, path, value) {
    const parts = pathParts(path); let cur = state;
    for (let i = 0; i < parts.length - 1; i += 1) {
      const part = parts[i];
      if (cur[part] == null) cur[part] = {};
      if (typeof cur[part] !== 'object' || Array.isArray(cur[part])) throw Error('STATE_RIPPLE_PATH_NOT_OBJECT');
      cur = cur[part];
    }
    cur[parts[parts.length - 1]] = clone(value);
  }
  function valueDigest(state, path) { return sha256(getPath(state, path)); }
  function opAccess(operation) {
    const op = operation?.op;
    if (!OPS.includes(op)) throw Error('STATE_RIPPLE_OPERATION_INVALID');
    if (op === 'EMIT_SIGNAL') {
      if (!operation.signal || !/^[A-Za-z0-9_.:-]+$/.test(String(operation.signal))) throw Error('STATE_RIPPLE_SIGNAL_INVALID');
      return { reads: [], writes: [], signals: [String(operation.signal)] };
    }
    if (op === 'COPY') {
      const from = String(operation.from || ''), path = String(operation.path || ''); pathParts(from); pathParts(path);
      return { reads: [from], writes: [path], signals: [] };
    }
    if (op === 'SUM') {
      const reads = uniqSorted(operation.paths || []); if (!reads.length) throw Error('STATE_RIPPLE_SUM_PATHS_REQUIRED');
      reads.forEach(pathParts); const path = String(operation.path || ''); pathParts(path);
      return { reads, writes: [path], signals: [] };
    }
    const path = String(operation.path || ''); pathParts(path);
    if (op === 'SET') return { reads: [], writes: [path], signals: [] };
    if (op === 'ASSERT_EQ') return { reads: [path], writes: [], signals: [] };
    return { reads: [path], writes: [path], signals: [] };
  }
  function normalizeNode(node) {
    if (!node?.id || !/^[A-Za-z0-9_.:-]+$/.test(String(node.id))) throw Error('STATE_RIPPLE_NODE_ID_INVALID');
    const operations = (node.operations || []).map(clone); if (!operations.length) throw Error('STATE_RIPPLE_NODE_OPERATIONS_REQUIRED');
    const reads = uniqSorted(node.reads), writes = uniqSorted(node.writes), dependsOn = uniqSorted(node.dependsOn), effects = uniqSorted(node.effects);
    reads.forEach(pathParts); writes.forEach(pathParts);
    for (const operation of operations) {
      const access = opAccess(operation);
      for (const path of access.reads) if (!reads.includes(path)) throw Error(`STATE_RIPPLE_UNDECLARED_READ:${node.id}:${path}`);
      for (const path of access.writes) if (!writes.includes(path)) throw Error(`STATE_RIPPLE_UNDECLARED_WRITE:${node.id}:${path}`);
      for (const signal of access.signals) if (!effects.includes(signal)) throw Error(`STATE_RIPPLE_UNDECLARED_EFFECT:${node.id}:${signal}`);
    }
    const core = { id: String(node.id), reads, writes, dependsOn, effects, operations };
    return freeze({ ...core, nodeSha256: sha256(core) });
  }
  function topo(nodes) {
    const byId = new Map(nodes.map(node => [node.id, node])), indegree = new Map(nodes.map(node => [node.id, 0])), children = new Map(nodes.map(node => [node.id, []]));
    for (const node of nodes) for (const dep of node.dependsOn) {
      if (!byId.has(dep)) throw Error(`STATE_RIPPLE_UNKNOWN_DEPENDENCY:${node.id}:${dep}`);
      if (dep === node.id) throw Error('STATE_RIPPLE_SELF_DEPENDENCY');
      indegree.set(node.id, indegree.get(node.id) + 1); children.get(dep).push(node.id);
    }
    const ready = [...indegree.entries()].filter(([, n]) => n === 0).map(([id]) => id).sort(), order = [];
    while (ready.length) {
      const id = ready.shift(); order.push(id);
      for (const child of children.get(id).sort()) { indegree.set(child, indegree.get(child) - 1); if (indegree.get(child) === 0) { ready.push(child); ready.sort(); } }
    }
    if (order.length !== nodes.length) throw Error('STATE_RIPPLE_DEPENDENCY_CYCLE');
    return order;
  }
  function explicitAncestors(nodes) {
    const byId = new Map(nodes.map(node => [node.id, node])), memo = new Map();
    function collect(id) { if (memo.has(id)) return memo.get(id); const out = new Set(); for (const dep of byId.get(id).dependsOn) { out.add(dep); for (const item of collect(dep)) out.add(item); } memo.set(id, out); return out; }
    for (const node of nodes) collect(node.id); return memo;
  }
  function prefixKeys(path) {
    const parts = pathParts(path), out = [];
    for (let i = 1; i <= parts.length; i += 1) out.push(parts.slice(0, i).join('.'));
    return out;
  }
  function addToIndex(map, key, value) { if (!map.has(key)) map.set(key, new Set()); map.get(key).add(value); }
  function overlappingIndexedIds(path, exactIndex, descendantIndex) {
    const out = new Set();
    for (const prefix of prefixKeys(path)) for (const id of exactIndex.get(prefix) || []) out.add(id);
    for (const id of descendantIndex.get(path) || []) out.add(id);
    return out;
  }
  function checkWriteOrdering(nodes) {
    const ancestry = explicitAncestors(nodes), exactIndex = new Map(), descendantIndex = new Map();
    for (const node of nodes) {
      for (const path of node.writes) {
        for (const otherId of overlappingIndexedIds(path, exactIndex, descendantIndex)) {
          if (otherId === node.id) continue;
          if (!ancestry.get(node.id).has(otherId) && !ancestry.get(otherId).has(node.id)) throw Error(`STATE_RIPPLE_AMBIGUOUS_WRITE_ORDER:${otherId}:${node.id}:${path}`);
        }
        addToIndex(exactIndex, path, node.id);
        const parts = pathParts(path);
        for (let i = 1; i < parts.length; i += 1) addToIndex(descendantIndex, parts.slice(0, i).join('.'), node.id);
      }
    }
  }
  function buildGraph(nodes, order) {
    const byId = new Map(nodes.map(node => [node.id, node])), index = new Map(order.map((id, i) => [id, i]));
    const incoming = new Map(order.map(id => [id, new Set(byId.get(id).dependsOn)])), outgoing = new Map(order.map(id => [id, new Set()]));
    for (const id of order) for (const dep of incoming.get(id)) outgoing.get(dep).add(id);
    const exactWrites = new Map(), descendantWrites = new Map();
    for (const id of order) {
      for (const path of byId.get(id).writes) {
        addToIndex(exactWrites, path, id);
        const parts = pathParts(path);
        for (let i = 1; i < parts.length; i += 1) addToIndex(descendantWrites, parts.slice(0, i).join('.'), id);
      }
    }
    for (const readerId of order) {
      const readerIndex = index.get(readerId), reader = byId.get(readerId);
      for (const read of reader.reads) for (const writerId of overlappingIndexedIds(read, exactWrites, descendantWrites)) {
        if (writerId === readerId || index.get(writerId) >= readerIndex) continue;
        outgoing.get(writerId).add(readerId); incoming.get(readerId).add(writerId);
      }
    }
    const core = { order: [...order], incoming: Object.fromEntries(order.map(id => [id, [...incoming.get(id)].sort((a,b) => index.get(a)-index.get(b)||a.localeCompare(b))])), outgoing: Object.fromEntries(order.map(id => [id, [...outgoing.get(id)].sort((a,b) => index.get(a)-index.get(b)||a.localeCompare(b))])) };
    return freeze({ ...core, graphSha256: sha256(core) });
  }
  function createFabric({ fabricId = 'grammar-glass-state-ripple', nodes = [], requiredEffects = [], binding = null, opaqueNodeIds = [] } = {}) {
    if (!fabricId || !/^[A-Za-z0-9_.:-]+$/.test(String(fabricId))) throw Error('STATE_RIPPLE_FABRIC_ID_INVALID');
    if (!Array.isArray(nodes) || !nodes.length || nodes.length > MAX_NODES) throw Error('STATE_RIPPLE_NODE_COUNT_INVALID');
    const normalized = nodes.map(normalizeNode); if (new Set(normalized.map(node => node.id)).size !== normalized.length) throw Error('STATE_RIPPLE_DUPLICATE_NODE_ID');
    const operationCount = normalized.reduce((sum, node) => sum + node.operations.length, 0); if (operationCount > MAX_OPERATIONS) throw Error('STATE_RIPPLE_OPERATION_CEILING_EXCEEDED');
    const order = topo(normalized); checkWriteOrdering(normalized); const graph = buildGraph(normalized, order);
    const effects = uniqSorted(requiredEffects), allEffects = new Set(normalized.flatMap(node => node.effects)); for (const effect of effects) if (!allEffects.has(effect)) throw Error(`STATE_RIPPLE_REQUIRED_EFFECT_UNDECLARED:${effect}`);
    const opaque = uniqSorted(opaqueNodeIds); const ids = new Set(normalized.map(node => node.id)); for (const id of opaque) if (!ids.has(id)) throw Error(`STATE_RIPPLE_UNKNOWN_OPAQUE_NODE:${id}`);
    const core = {
      schema: 'axm.code.grammar-glass-state-ripple-fabric.v1', version: '1.0.0', result: 'STATE_RIPPLE_FABRIC_READY_NOT_EXECUTED',
      fabricId: String(fabricId), binding: binding == null ? null : clone(binding), nodeCount: normalized.length, operationCount,
      nodes: normalized, topologicalOrder: order, graph, requiredEffects: effects, opaqueNodeIds: opaque,
      limits: { maximumNodes: MAX_NODES, maximumOperations: MAX_OPERATIONS },
      truth: { declaredReadsRequired: true, declaredWritesRequired: true, opaqueDependenciesNeverSilentlyReused: true, sparseWakeIsNotFullProofWithoutReferenceGate: true, retainedCacheIsNotTrainingOrLearnedWeights: true, localWakeValidityIsNotGlobalBudgetViability: true, arbitrarySourceExecution: false, automaticPromotion: false },
      authority: 'TRANSIENT_STATE_RIPPLE_ONLY'
    };
    return freeze({ ...core, fabricSha256: sha256(core) });
  }
  function fromConstructionProgram(program, options = {}) {
    if (!Program.validProgram(program)) throw Error('STATE_RIPPLE_VALID_CONSTRUCTION_PROGRAM_REQUIRED');
    return createFabric({
      fabricId: options.fabricId || `state-ripple:${program.programId || 'construction-program'}`,
      nodes: program.modules.map(module => ({ id: module.id, reads: module.reads, writes: module.writes, dependsOn: module.dependsOn, effects: module.effects, operations: module.operations })),
      requiredEffects: program.requiredEffects || [], opaqueNodeIds: options.opaqueNodeIds || [],
      binding: { constructionProgramSha256: program.programSha256, constructionProgramBinding: clone(program.binding || null) }
    });
  }
  function validFabric(fabric) {
    if (!fabric || fabric.schema !== 'axm.code.grammar-glass-state-ripple-fabric.v1' || !fabric.fabricSha256 || !Array.isArray(fabric.nodes) || !Array.isArray(fabric.topologicalOrder) || fabric.nodeCount !== fabric.nodes.length || fabric.topologicalOrder.length !== fabric.nodes.length) return false;
    try {
      const rebuilt = createFabric({ fabricId: fabric.fabricId, nodes: fabric.nodes, requiredEffects: fabric.requiredEffects, binding: fabric.binding, opaqueNodeIds: fabric.opaqueNodeIds });
      return rebuilt.fabricSha256 === fabric.fabricSha256 && canon(rebuilt) === canon(fabric);
    } catch { return false; }
  }
  function readSnapshot(fabric, state) {
    const paths = uniqSorted(fabric.nodes.flatMap(node => node.reads));
    return freeze(Object.fromEntries(paths.map(path => [path, valueDigest(state, path)])));
  }
  function executeNode(node, state) {
    const staged = clone(state), signals = []; let failure = null;
    for (const operation of node.operations) {
      try {
        if (operation.op === 'SET') setPath(staged, operation.path, operation.value);
        else if (operation.op === 'INCREMENT') { const current = getPath(staged, operation.path); const by = Number(operation.by); if (!current.present || !Number.isFinite(current.value) || !Number.isFinite(by)) throw Error('INCREMENT_REQUIRES_FINITE_NUMBER'); setPath(staged, operation.path, current.value + by); }
        else if (operation.op === 'TRANSITION') { const current = getPath(staged, operation.path); if (!current.present || canon(current.value) !== canon(operation.from)) throw Error('TRANSITION_FROM_MISMATCH'); setPath(staged, operation.path, operation.to); }
        else if (operation.op === 'ASSERT_EQ') { const current = getPath(staged, operation.path); if (!current.present || canon(current.value) !== canon(operation.value)) throw Error('ASSERT_EQ_FAILED'); }
        else if (operation.op === 'EMIT_SIGNAL') signals.push(String(operation.signal));
        else if (operation.op === 'COPY') { const current = getPath(staged, operation.from); if (!current.present) throw Error('COPY_SOURCE_MISSING'); setPath(staged, operation.path, current.value); }
        else if (operation.op === 'SUM') { let total = Number(operation.constant || 0); if (!Number.isFinite(total)) throw Error('SUM_CONSTANT_INVALID'); for (const path of operation.paths || []) { const current = getPath(staged, path); if (!current.present || !Number.isFinite(current.value)) throw Error('SUM_REQUIRES_FINITE_NUMBERS'); total += current.value; } setPath(staged, operation.path, total); }
        else throw Error('STATE_RIPPLE_OPERATION_INVALID');
      } catch (error) { failure = error.message || String(error); break; }
    }
    return { failure, staged, signals };
  }
  function captureWrites(node, state) { return freeze(node.writes.map(path => ({ path, value: getPath(state, path) })).sort((a,b) => pathParts(a.path).length-pathParts(b.path).length||a.path.localeCompare(b.path))); }
  function applyWrites(state, writes) { for (const item of writes) { if (!item.value?.present) continue; setPath(state, item.path, item.value.value); } }
  function inputFingerprint(node, state, cache, incomingIds) {
    const reads = Object.fromEntries(node.reads.map(path => [path, valueDigest(state, path)]));
    const dependencies = Object.fromEntries(incomingIds.map(id => [id, cache[id]?.outputSha256 || null]));
    return sha256({ reads, dependencies });
  }
  const CACHE_ENTRY_KEYS = Object.freeze(['cacheEntrySha256', 'emittedSignals', 'inputFingerprint', 'nodeId', 'nodeSha256', 'outputSha256', 'writeValues']);
  const BASELINE_KEYS = Object.freeze(['authority', 'baselineSha256', 'cache', 'cacheCount', 'fabricSha256', 'finalStateSha256', 'graphSha256', 'result', 'schema', 'truth', 'version', 'watchDigests', 'watchedInputSha256']);
  const BASELINE_TRUTH = Object.freeze({ watchedInputsStoredAsDigestsOnly: true, unchangedCacheEntriesMayBeRetainedByIdentity: true, baselineIsNotAuthority: true });
  function portableJson(value, seen = new Set()) {
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return true;
    if (typeof value === 'number') return Number.isFinite(value);
    if (!value || typeof value !== 'object' || seen.has(value)) return false;
    if (!Array.isArray(value)) { const prototype = Object.getPrototypeOf(value); if (prototype !== Object.prototype && prototype !== null) return false; }
    seen.add(value);
    const valid = (Array.isArray(value) ? value : Object.values(value)).every(item => portableJson(item, seen));
    seen.delete(value);
    return valid;
  }
  function exactKeys(value, expected) { return !!value && typeof value === 'object' && !Array.isArray(value) && canon(Object.keys(value).sort()) === canon([...expected].sort()); }
  function digest(value) { return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value); }
  function orderedWritePaths(node) { return [...node.writes].sort((a,b) => pathParts(a).length-pathParts(b).length||a.localeCompare(b)); }
  function expectedSignals(node) { return node.operations.filter(operation => operation.op === 'EMIT_SIGNAL').map(operation => String(operation.signal)); }
  function makeCacheEntry(node, fingerprint, state, signals) {
    const writeValues = captureWrites(node, state), core = { nodeId: node.id, nodeSha256: node.nodeSha256, inputFingerprint: fingerprint, writeValues, emittedSignals: [...signals], outputSha256: sha256({ writeValues, emittedSignals: [...signals] }) };
    return freeze({ ...core, cacheEntrySha256: sha256(core) });
  }
  function validCacheEntry(node, entry) {
    if (!node || !exactKeys(entry, CACHE_ENTRY_KEYS) || entry.nodeId !== node.id || entry.nodeSha256 !== node.nodeSha256 || !digest(entry.inputFingerprint) || !digest(entry.outputSha256) || !digest(entry.cacheEntrySha256)) return false;
    if (!Array.isArray(entry.writeValues) || !Array.isArray(entry.emittedSignals)) return false;
    const paths = orderedWritePaths(node);
    if (entry.writeValues.length !== paths.length || entry.emittedSignals.length !== expectedSignals(node).length) return false;
    for (let index = 0; index < paths.length; index += 1) {
      const write = entry.writeValues[index];
      if (!exactKeys(write, ['path', 'value']) || write.path !== paths[index] || !exactKeys(write.value, ['present', 'value']) || typeof write.value.present !== 'boolean' || (!write.value.present && write.value.value !== null)) return false;
    }
    if (canon(entry.emittedSignals) !== canon(expectedSignals(node)) || entry.outputSha256 !== sha256({ writeValues: entry.writeValues, emittedSignals: entry.emittedSignals })) return false;
    const core = { ...entry }; delete core.cacheEntrySha256;
    return sha256(core) === entry.cacheEntrySha256;
  }
  function makeBaseline(fabric, inputState, finalState, cache) {
    const watchDigests = readSnapshot(fabric, inputState), cacheCore = Object.fromEntries(fabric.topologicalOrder.map(id => [id, cache[id]]));
    const core = { schema: 'axm.code.grammar-glass-state-ripple-baseline.v1', version: '1.0.0', result: 'STATE_RIPPLE_BASELINE_READY', fabricSha256: fabric.fabricSha256, graphSha256: fabric.graph.graphSha256, watchDigests, watchedInputSha256: sha256(watchDigests), finalStateSha256: sha256(finalState), cache: cacheCore, cacheCount: Object.keys(cacheCore).length, truth: BASELINE_TRUTH, authority: 'NONE' };
    const baseline = freeze({ ...core, baselineSha256: sha256(core) });
    TRUSTED_BASELINES.add(baseline);
    return baseline;
  }
  function validBaseline(fabric, baseline) {
    if (!validFabric(fabric) || !portableJson(baseline) || !exactKeys(baseline, BASELINE_KEYS) || baseline.schema !== 'axm.code.grammar-glass-state-ripple-baseline.v1' || baseline.version !== '1.0.0' || baseline.result !== 'STATE_RIPPLE_BASELINE_READY' || baseline.authority !== 'NONE' || baseline.fabricSha256 !== fabric.fabricSha256 || baseline.graphSha256 !== fabric.graph.graphSha256 || !digest(baseline.baselineSha256) || !digest(baseline.watchedInputSha256) || !digest(baseline.finalStateSha256) || canon(baseline.truth) !== canon(BASELINE_TRUTH)) return false;
    const expectedWatchPaths = uniqSorted(fabric.nodes.flatMap(node => node.reads)), expectedCacheIds = [...fabric.topologicalOrder];
    if (!exactKeys(baseline.watchDigests, expectedWatchPaths) || !expectedWatchPaths.every(path => digest(baseline.watchDigests[path])) || baseline.watchedInputSha256 !== sha256(baseline.watchDigests) || !exactKeys(baseline.cache, expectedCacheIds) || baseline.cacheCount !== expectedCacheIds.length) return false;
    const core = { ...baseline }; delete core.baselineSha256; if (sha256(core) !== baseline.baselineSha256) return false;
    const byId = new Map(fabric.nodes.map(node => [node.id, node]));
    return expectedCacheIds.every(id => validCacheEntry(byId.get(id), baseline.cache[id]));
  }
  function runAll(fabric, inputState = {}) {
    if (!validFabric(fabric)) throw Error('STATE_RIPPLE_VALID_FABRIC_REQUIRED');
    const state = clone(inputState), byId = new Map(fabric.nodes.map(node => [node.id, node])), cache = {}, receipts = [], realized = new Set();
    for (const id of fabric.topologicalOrder) {
      const node = byId.get(id), fingerprint = inputFingerprint(node, state, cache, fabric.graph.incoming[id]), before = sha256(captureWrites(node, state)), result = executeNode(node, state);
      if (result.failure) {
        const core = { schema: 'axm.code.grammar-glass-state-ripple-full-run.v1', version: '1.0.0', result: 'STATE_RIPPLE_FULL_RUN_HELD_NODE_FAILURE', fabricSha256: fabric.fabricSha256, failedNodeId: id, failure: result.failure, executedNodeCount: receipts.length + 1, finalState: null, finalStateSha256: null, receipts, baseline: null, truth: { failedUpdateNotPublished: true, fullReferenceRun: true }, authority: 'NONE' };
        return freeze({ ...core, runSha256: sha256(core) });
      }
      const after = sha256(captureWrites(node, result.staged)), changed = after !== before; for (const key of Object.keys(state)) delete state[key]; Object.assign(state, result.staged); if (changed) for (const signal of result.signals) realized.add(signal);
      const entry = makeCacheEntry(node, fingerprint, state, result.signals); cache[id] = entry;
      const receiptCore = { nodeId: id, result: 'NODE_EXECUTED_FULL', beforeWriteSha256: before, afterWriteSha256: after, committedStateChange: changed, outputSha256: entry.outputSha256 }; receipts.push(freeze({ ...receiptCore, receiptSha256: sha256(receiptCore) }));
    }
    const missing = fabric.requiredEffects.filter(effect => !realized.has(effect)), baseline = makeBaseline(fabric, inputState, state, cache);
    const core = { schema: 'axm.code.grammar-glass-state-ripple-full-run.v1', version: '1.0.0', result: missing.length ? 'STATE_RIPPLE_FULL_RUN_HELD_REQUIRED_EFFECTS' : 'STATE_RIPPLE_FULL_RUN_COMPLETE', fabricSha256: fabric.fabricSha256, failedNodeId: null, failure: null, executedNodeCount: fabric.nodeCount, reusedNodeCount: 0, finalState: state, finalStateSha256: sha256(state), realizedEffects: [...realized].sort(), missingRequiredEffects: missing, receipts, baseline, truth: { fullReferenceRun: true, sparseReusePerformed: false, externalSideEffects: false }, authority: 'TRANSIENT_STATE_RIPPLE_ONLY' };
    return freeze({ ...core, runSha256: sha256(core) });
  }
  function changedWatchedPaths(baseline, current) { return Object.keys(current).filter(path => current[path] !== baseline.watchDigests[path]).sort(); }
  function wakeClosure(fabric, changedPaths, baseline) {
    const wake = new Set(fabric.opaqueNodeIds), byId = new Map(fabric.nodes.map(node => [node.id, node]));
    for (const id of fabric.topologicalOrder) { const node = byId.get(id); if (!baseline.cache[id] || node.reads.some(read => changedPaths.some(path => pathsOverlap(read, path)))) wake.add(id); }
    const queue = [...wake]; while (queue.length) { const id = queue.shift(); for (const child of fabric.graph.outgoing[id]) if (!wake.has(child)) { wake.add(child); queue.push(child); } }
    return wake;
  }
  function sparseUpdate(fabric, inputState, baseline, { wakeBudget = Infinity, expectedBaselineSha256 = null } = {}) {
    if (!validFabric(fabric)) throw Error('STATE_RIPPLE_VALID_FABRIC_REQUIRED');
    if (!validBaseline(fabric, baseline)) throw Error('STATE_RIPPLE_CURRENT_BASELINE_REQUIRED');
    if (!TRUSTED_BASELINES.has(baseline)) {
      if (!digest(expectedBaselineSha256)) throw Error('STATE_RIPPLE_BASELINE_PIN_REQUIRED');
      if (expectedBaselineSha256 !== baseline.baselineSha256) throw Error('STATE_RIPPLE_BASELINE_PIN_MISMATCH');
    }
    const currentWatch = readSnapshot(fabric, inputState), changedPaths = changedWatchedPaths(baseline, currentWatch), conservativeWake = wakeClosure(fabric, changedPaths, baseline), budget = Number(wakeBudget);
    if (!(budget >= 0)) throw Error('STATE_RIPPLE_WAKE_BUDGET_INVALID');
    if (conservativeWake.size > budget) {
      const core = { schema: 'axm.code.grammar-glass-state-ripple-update.v1', version: '1.0.0', result: 'STATE_RIPPLE_HELD_GLOBAL_WAKE_BUDGET', fabricSha256: fabric.fabricSha256, baselineSha256: baseline.baselineSha256, changedReadPaths: changedPaths, conservativeWakeNodeCount: conservativeWake.size, wakeBudget: budget, executedNodeCount: 0, reusedNodeCount: 0, finalState: null, nextBaseline: null, truth: { locallyValidWakeSetCanStillFailGlobalBudget: true, noPartialUpdatePublished: true, heldIsNotFailureProof: true }, authority: 'NONE' };
      return freeze({ ...core, updateSha256: sha256(core) });
    }
    const state = clone(inputState), byId = new Map(fabric.nodes.map(node => [node.id, node])), cache = {}, receipts = [], realized = new Set(); let executed = 0, reused = 0;
    for (const id of fabric.topologicalOrder) {
      const node = byId.get(id), old = baseline.cache[id], fingerprint = inputFingerprint(node, state, cache, fabric.graph.incoming[id]), canReuse = !!old && !fabric.opaqueNodeIds.includes(id) && old.inputFingerprint === fingerprint;
      const before = sha256(captureWrites(node, state));
      if (canReuse) {
        applyWrites(state, old.writeValues); const after = sha256(captureWrites(node, state)), changed = after !== before; if (changed) for (const signal of old.emittedSignals) realized.add(signal); cache[id] = old; reused += 1;
        const receiptCore = { nodeId: id, result: 'NODE_REUSED_EXACT_CACHE', conservativeWakeCandidate: conservativeWake.has(id), beforeWriteSha256: before, afterWriteSha256: after, committedStateChange: changed, outputSha256: old.outputSha256, retainedCacheIdentity: true }; receipts.push(freeze({ ...receiptCore, receiptSha256: sha256(receiptCore) }));
        continue;
      }
      const result = executeNode(node, state); executed += 1;
      if (result.failure) {
        const core = { schema: 'axm.code.grammar-glass-state-ripple-update.v1', version: '1.0.0', result: 'STATE_RIPPLE_HELD_NODE_FAILURE', fabricSha256: fabric.fabricSha256, baselineSha256: baseline.baselineSha256, changedReadPaths: changedPaths, conservativeWakeNodeCount: conservativeWake.size, wakeBudget: budget, failedNodeId: id, failure: result.failure, executedNodeCount: executed, reusedNodeCount: reused, finalState: null, nextBaseline: null, receipts, truth: { stagedSparseUpdateDiscarded: true, priorBaselinePreserved: true, noPartialUpdatePublished: true }, authority: 'NONE' };
        return freeze({ ...core, updateSha256: sha256(core) });
      }
      const after = sha256(captureWrites(node, result.staged)), changed = after !== before; for (const key of Object.keys(state)) delete state[key]; Object.assign(state, result.staged); if (changed) for (const signal of result.signals) realized.add(signal);
      const entry = makeCacheEntry(node, fingerprint, state, result.signals); cache[id] = entry;
      const receiptCore = { nodeId: id, result: 'NODE_EXECUTED_SPARSE', conservativeWakeCandidate: conservativeWake.has(id), beforeWriteSha256: before, afterWriteSha256: after, committedStateChange: changed, outputSha256: entry.outputSha256, retainedCacheIdentity: false }; receipts.push(freeze({ ...receiptCore, receiptSha256: sha256(receiptCore) }));
    }
    const missing = fabric.requiredEffects.filter(effect => !realized.has(effect)), nextBaseline = makeBaseline(fabric, inputState, state, cache);
    const core = { schema: 'axm.code.grammar-glass-state-ripple-update.v1', version: '1.0.0', result: missing.length ? 'STATE_RIPPLE_HELD_REQUIRED_EFFECTS' : 'STATE_RIPPLE_SPARSE_UPDATE_COMPLETE', fabricSha256: fabric.fabricSha256, baselineSha256: baseline.baselineSha256, changedReadPaths: changedPaths, conservativeWakeNodeCount: conservativeWake.size, wakeBudget: budget, executedNodeCount: executed, reusedNodeCount: reused, reuseFraction: fabric.nodeCount ? reused / fabric.nodeCount : 0, finalState: state, finalStateSha256: sha256(state), realizedEffects: [...realized].sort(), missingRequiredEffects: missing, receipts, nextBaseline, truth: { exactDigestReuseOnly: true, opaqueNodesNeverReused: true, retainedCacheObjectIdentityPreservedWhenReused: true, noFullStateDiffRequiredForRouting: true, sparseResultStillNeedsReferenceEvidenceForNewClaimScope: true, externalSideEffects: false, automaticPromotion: false }, authority: 'TRANSIENT_STATE_RIPPLE_ONLY' };
    return freeze({ ...core, updateSha256: sha256(core) });
  }
  function shadowVerify(fabric, inputState, baseline, options = {}) {
    const sparse = sparseUpdate(fabric, inputState, baseline, options);
    if (!sparse.finalState || !sparse.nextBaseline) {
      const core = { schema: 'axm.code.grammar-glass-state-ripple-shadow.v1', version: '1.0.0', result: 'STATE_RIPPLE_SHADOW_HELD_SPARSE_UPDATE', fabricSha256: fabric.fabricSha256, sparseUpdateSha256: sparse.updateSha256, fullRunSha256: null, finalStateEquivalent: null, nodeOutputsEquivalent: null, sparse, full: null, truth: { holdPreservedWithoutFakeEquivalence: true }, authority: 'NONE' };
      return freeze({ ...core, shadowSha256: sha256(core) });
    }
    const full = runAll(fabric, inputState), ids = fabric.topologicalOrder;
    const finalEq = full.finalStateSha256 === sparse.finalStateSha256 && full.result === sparse.result.replace('SPARSE_UPDATE_COMPLETE','FULL_RUN_COMPLETE');
    const outputsEq = !!full.baseline && ids.every(id => full.baseline.cache[id].outputSha256 === sparse.nextBaseline.cache[id].outputSha256);
    const effectsEq = canon(full.realizedEffects || []) === canon(sparse.realizedEffects || []) && canon(full.missingRequiredEffects || []) === canon(sparse.missingRequiredEffects || []);
    const pass = finalEq && outputsEq && effectsEq;
    const core = { schema: 'axm.code.grammar-glass-state-ripple-shadow.v1', version: '1.0.0', result: pass ? 'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_PASS' : 'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_FAIL', fabricSha256: fabric.fabricSha256, sparseUpdateSha256: sparse.updateSha256, fullRunSha256: full.runSha256, finalStateEquivalent: finalEq, nodeOutputsEquivalent: outputsEq, effectsEquivalent: effectsEq, sparseExecutedNodeCount: sparse.executedNodeCount, sparseReusedNodeCount: sparse.reusedNodeCount, fullExecutedNodeCount: full.executedNodeCount, sparse, full, truth: { referencePathExecutesAllNodes: true, passIsBoundedToExactFabricAndInput: true, passDoesNotProveArbitraryFutureFabrics: true, wallClockSpeedupNotClaimed: true }, authority: 'NONE' };
    return freeze({ ...core, shadowSha256: sha256(core) });
  }

  return Object.freeze({ MAX_NODES, MAX_OPERATIONS, OPS, canon, sha256, pathsOverlap, createFabric, fromConstructionProgram, validFabric, readSnapshot, runAll, validBaseline, sparseUpdate, shadowVerify });
});