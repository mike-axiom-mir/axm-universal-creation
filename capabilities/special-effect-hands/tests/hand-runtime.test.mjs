import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandRegistry, executeHandGraph, hashValue, resumeHandGraph } from '../src/hand-runtime.mjs';
import { ELECTRIC_HANDS, ELECTRIC_STORM_GRAPH, makeElectricInitialState } from '../src/electric-hands.mjs';

const registry = createHandRegistry(ELECTRIC_HANDS);

test('same graph + seed is deterministic and caller-neutral', () => {
  const initialState = makeElectricInitialState(424242);
  const human = executeHandGraph({ registry, graph: ELECTRIC_STORM_GRAPH, initialState, context: { callerKind: 'human-ui' } });
  const ai = executeHandGraph({ registry, graph: ELECTRIC_STORM_GRAPH, initialState, context: { callerKind: 'ai-agent' } });
  const mirror = executeHandGraph({ registry, graph: ELECTRIC_STORM_GRAPH, initialState, context: { callerKind: 'mirror-deterministic' } });

  assert.equal(human.finalStateHash, ai.finalStateHash);
  assert.equal(ai.finalStateHash, mirror.finalStateHash);
  assert.deepEqual(human.finalState, mirror.finalState);
  assert.equal(human.checkpoints.length, ELECTRIC_STORM_GRAPH.stages.length);
});

test('checkpoint edit changes only downstream replay', () => {
  const original = executeHandGraph({
    registry,
    graph: ELECTRIC_STORM_GRAPH,
    initialState: makeElectricInitialState(20260915),
    context: { callerKind: 'mirror-deterministic' },
  });

  const branchCheckpoint = original.checkpoints.find((checkpoint) => checkpoint.stageId === 'grow-branches');
  assert.ok(branchCheckpoint);
  const checkpointHashBefore = hashValue(branchCheckpoint.state);

  const resumed = resumeHandGraph({
    registry,
    graph: ELECTRIC_STORM_GRAPH,
    checkpoint: branchCheckpoint,
    edits: [
      { op: 'set', path: ['effect', 'controls', 'branchEnergyScale'], value: 0.31 },
      { op: 'set', path: ['effect', 'controls', 'glowScale'], value: 0.62 },
      { op: 'set', path: ['paths', 1, 'points', 2, 'y'], value: 0.18 },
    ],
    context: { callerKind: 'ai-agent' },
  });

  assert.equal(hashValue(branchCheckpoint.state), checkpointHashBefore, 'stored checkpoint must stay unchanged');
  assert.deepEqual(resumed.executedStageIds, ['profile-energy', 'core-light', 'soft-bloom', 'ambient-field', 'pulse', 'preview']);
  assert.notEqual(resumed.finalStateHash, original.finalStateHash);
  assert.equal(resumed.finalState.effect.controls.branchEnergyScale, 0.31);
  assert.equal(resumed.finalState.effect.controls.glowScale, 0.62);
  assert.equal(resumed.finalState.paths[1].points[2].y, 0.18);
  assert.equal(resumed.finalState.paths[0].points.length, branchCheckpoint.state.paths[0].points.length);
});

test('special-effect graph stays editable and realization remains derived', () => {
  const run = executeHandGraph({
    registry,
    graph: ELECTRIC_STORM_GRAPH,
    initialState: makeElectricInitialState(77),
    context: { callerKind: 'deterministic-program' },
  });

  assert.ok(run.finalState.paths.length > 1);
  assert.deepEqual(
    run.finalState.layers.map((layer) => layer.module),
    ['light.neon-edge-glow', 'light.soft-bloom-halo', 'atmosphere.ambient-field', 'motion.idle-pulse'],
  );
  assert.equal(run.finalState.realizations.svgPreview.derivedFromTopologyHash, hashValue(run.finalState.paths));
  assert.match(run.finalState.realizations.svgPreview.content, /^<svg /);
});
