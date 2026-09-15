import { createHash } from 'node:crypto';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function deepClone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

export function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (isPlainObject(value)) {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = canonicalize(value[key]);
    return out;
  }
  return value;
}

export function canonicalStringify(value) {
  return JSON.stringify(canonicalize(value));
}

export function hashValue(value) {
  return createHash('sha256').update(canonicalStringify(value)).digest('hex');
}

export function createHandRegistry(hands) {
  const registry = new Map();
  for (const hand of hands) {
    if (!hand || hand.schema !== 'axm.hand/v0.1') throw new Error('Invalid Hand schema');
    if (!hand.id || !hand.version || typeof hand.execute !== 'function') throw new Error('Incomplete Hand descriptor');
    if (registry.has(hand.id)) throw new Error(`Duplicate Hand id: ${hand.id}`);
    registry.set(hand.id, hand);
  }
  return Object.freeze({
    get(id) {
      const hand = registry.get(id);
      if (!hand) throw new Error(`Unknown Hand: ${id}`);
      return hand;
    },
    list() {
      return [...registry.values()].map(({ execute, ...descriptor }) => deepClone(descriptor));
    },
  });
}

function getContainer(root, path, createMissing) {
  if (!Array.isArray(path) || path.length === 0) throw new Error('Edit path must be a non-empty array');
  let cursor = root;
  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    if (cursor[key] === undefined) {
      if (!createMissing) throw new Error(`Missing edit path: ${path.slice(0, i + 1).join('.')}`);
      cursor[key] = typeof path[i + 1] === 'number' ? [] : {};
    }
    if (cursor[key] === null || typeof cursor[key] !== 'object') {
      throw new Error(`Edit path is not traversable: ${path.slice(0, i + 1).join('.')}`);
    }
    cursor = cursor[key];
  }
  return { cursor, key: path[path.length - 1] };
}

export function applyStateEdits(inputState, edits = []) {
  const state = deepClone(inputState);
  for (const edit of edits) {
    if (!edit || !['set', 'delete'].includes(edit.op)) throw new Error(`Unsupported edit op: ${edit?.op}`);
    const { cursor, key } = getContainer(state, edit.path, edit.op === 'set');
    if (edit.op === 'set') {
      cursor[key] = deepClone(edit.value);
    } else if (Array.isArray(cursor) && typeof key === 'number') {
      if (key < 0 || key >= cursor.length) throw new Error(`Delete index out of range: ${key}`);
      cursor.splice(key, 1);
    } else {
      if (!(key in cursor)) throw new Error(`Missing delete target: ${edit.path.join('.')}`);
      delete cursor[key];
    }
  }
  return state;
}

function executeStages({ registry, graph, state, startIndex, context }) {
  let current = deepClone(state);
  const checkpoints = [];
  const executedStageIds = [];

  for (let stageIndex = startIndex; stageIndex < graph.stages.length; stageIndex += 1) {
    const stage = graph.stages[stageIndex];
    const hand = registry.get(stage.hand);
    const inputHash = hashValue(current);
    const result = hand.execute(deepClone(current), deepClone(stage.params ?? {}), {
      graphId: graph.id,
      graphVersion: graph.version,
      stageIndex,
      stageId: stage.id,
      callerKind: context.callerKind ?? 'unspecified',
    });
    if (!result || !isPlainObject(result.state)) throw new Error(`Hand ${hand.id} did not return { state }`);
    current = deepClone(result.state);
    const checkpoint = {
      schema: 'axm.hand-checkpoint/v0.1',
      graphId: graph.id,
      graphVersion: graph.version,
      stageIndex,
      stageId: stage.id,
      hand: { id: hand.id, version: hand.version },
      inputHash,
      stateHash: hashValue(current),
      state: deepClone(current),
      evidence: deepClone(result.evidence ?? {}),
    };
    checkpoints.push(checkpoint);
    executedStageIds.push(stage.id);
  }

  return { state: current, checkpoints, executedStageIds };
}

export function executeHandGraph({ registry, graph, initialState, context = {} }) {
  if (!graph || graph.schema !== 'axm.hand-graph/v0.1' || !graph.id || !graph.version || !Array.isArray(graph.stages)) {
    throw new Error('Invalid Hand graph');
  }
  const initial = deepClone(initialState);
  const run = executeStages({ registry, graph, state: initial, startIndex: 0, context });
  return {
    schema: 'axm.hand-run/v0.1',
    graph: { id: graph.id, version: graph.version },
    caller: { kind: context.callerKind ?? 'unspecified' },
    initialStateHash: hashValue(initial),
    finalStateHash: hashValue(run.state),
    finalState: run.state,
    checkpoints: run.checkpoints,
    executedStageIds: run.executedStageIds,
  };
}

export function resumeHandGraph({ registry, graph, checkpoint, edits = [], context = {} }) {
  if (!checkpoint || checkpoint.schema !== 'axm.hand-checkpoint/v0.1') throw new Error('Invalid checkpoint');
  if (checkpoint.graphId !== graph.id || checkpoint.graphVersion !== graph.version) throw new Error('Checkpoint graph mismatch');
  if (hashValue(checkpoint.state) !== checkpoint.stateHash) throw new Error('Checkpoint state hash mismatch');

  const editedState = applyStateEdits(checkpoint.state, edits);
  const run = executeStages({
    registry,
    graph,
    state: editedState,
    startIndex: checkpoint.stageIndex + 1,
    context,
  });

  return {
    schema: 'axm.hand-resume/v0.1',
    graph: { id: graph.id, version: graph.version },
    caller: { kind: context.callerKind ?? 'unspecified' },
    resumedFrom: {
      stageIndex: checkpoint.stageIndex,
      stageId: checkpoint.stageId,
      checkpointStateHash: checkpoint.stateHash,
    },
    editReceipt: {
      edits: deepClone(edits),
      editHash: hashValue(edits),
      editedStateHash: hashValue(editedState),
    },
    finalStateHash: hashValue(run.state),
    finalState: run.state,
    checkpoints: run.checkpoints,
    executedStageIds: run.executedStageIds,
  };
}
