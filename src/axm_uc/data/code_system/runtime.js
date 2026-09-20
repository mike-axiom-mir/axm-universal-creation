'use strict';

// Portable generated-system host. Only load()/CLI read files or write stdout.
const clone = value => JSON.parse(JSON.stringify(value));
const compare = (a, b) => {
  const x = [...a].map(c => c.codePointAt(0)), y = [...b].map(c => c.codePointAt(0));
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i] - y[i];
  return x.length - y.length;
};
const key = value => value === null || typeof value !== 'object' ? JSON.stringify(value) : Array.isArray(value) ?
  '[' + value.map(key).join(',') + ']' : '{' + Object.keys(value).sort(compare).map(k => JSON.stringify(k) + ':' + key(value[k])).join(',') + '}';
const same = (a, b) => key(a) === key(b);
const exact = (value, fields) => value && typeof value === 'object' && !Array.isArray(value) && same(Object.keys(value).sort(), [...fields].sort());

class System {
  constructor(config, functions) {
    this.config = clone(config); this.spec = this.config.system; this.functions = {...functions};
    this.bindings = new Map(this.spec.bindings.map(row => [row.event, row]));
    this.transitions = new Map(this.spec.machine.transitions.map(row => [key([row.from, row.event]), row]));
  }
  _violations(model) { return this.spec.invariants.filter(row => this.functions[row.function](clone(model)) !== true).map(row => row.id); }
  _state(value) {
    if (!exact(value, ['phase', 'model']) || !this.spec.machine.states.includes(value.phase)) throw Error('STATE_INVALID');
    this.functions.ucSystemIdentity(value.model);
    if (this._violations(value.model).length) throw Error('STATE_INVARIANT');
    return clone(value);
  }
  initial() { return this._state({phase: this.spec.machine.initial_state, model: this.functions.ucSystemInitial()}); }
  step(state, event) {
    const current = this._state(state);
    const held = (status, extra = {}) => ({status, state: clone(current), effects: [], ...extra});
    if (!exact(event, ['type', 'args']) || typeof event.type !== 'string' || !Array.isArray(event.args)) return held('HOLD_ARGUMENTS');
    const binding = this.bindings.get(event.type);
    if (!binding) return held('HOLD_NO_TRANSITION');
    const routes = binding.routes ? binding.routes.events : [event.type];
    if (!routes.some(signal => this.transitions.has(key([current.phase, signal])))) return held('HOLD_NO_TRANSITION');
    try {
      // Check arguments before JSON cloning so invalid numbers cannot become null.
      const args = [clone(current.model), ...event.args];
      if (binding.guard && this.functions[binding.guard](...args) !== true) return held('HOLD_GUARD');
      const proposed = this.functions[binding.reducer](...args);
      this.functions.ucSystemIdentity(proposed);
      const signal = binding.routes ? this.functions[binding.routes.function](clone(proposed)) : event.type;
      if (!routes.includes(signal) || !this.transitions.has(key([current.phase, signal]))) return held('HOLD_EXECUTION', {error: 'ROUTE_UNDECLARED'});
      const violations = this._violations(proposed);
      if (violations.length) return held('HOLD_INVARIANT', {violations});
      const transition = this.transitions.get(key([current.phase, signal]));
      return {status: 'APPLIED', state: {phase: transition.to, model: clone(proposed)}, effects: clone(transition.effects),
        transition: {from: transition.from, event: transition.event, to: transition.to}};
    } catch (error) {
      const code = String(error.message);
      return code === 'ARGUMENT_COUNT' || code === 'VALUE_TYPE' || error instanceof TypeError ? held('HOLD_ARGUMENTS') : held('HOLD_EXECUTION', {error: code.slice(0, 160)});
    }
  }
  replay(events, state = null) {
    if (!Array.isArray(events) || events.length > 10000) throw Error('EVENT_LIMIT');
    let current = state === null ? this.initial() : this._state(state);
    const results = [];
    for (const event of events) { const result = this.step(current, event); results.push(result); current = result.state; }
    return {state: current, results};
  }
  checkpoint(events) {
    const replay = this.replay(events);
    return {schema: 'axm.code-system-checkpoint/v0.1', system_sha256: this.config.system_sha256, events: clone(events), state: replay.state};
  }
  restore(checkpoint) {
    if (!exact(checkpoint, ['schema', 'system_sha256', 'events', 'state'])) throw Error('CHECKPOINT_INVALID');
    if (checkpoint.schema !== 'axm.code-system-checkpoint/v0.1' || checkpoint.system_sha256 !== this.config.system_sha256) throw Error('CHECKPOINT_SYSTEM_MISMATCH');
    this._state(checkpoint.state);
    const replay = this.replay(checkpoint.events);
    if (!same(replay.state, checkpoint.state)) throw Error('CHECKPOINT_REPLAY_MISMATCH');
    return clone(replay.state);
  }
  explore() {
    const contract = this.spec.exploration, initial = this.initial(), queue = [[initial, []]], seen = new Set([key(initial)]);
    const covered = new Set(), phases = new Set([initial.phase]), acceptedEvents = new Set();
    let edges = 0, applied = 0, holds = 0, frontier = 0;
    const report = (status, counterexample = null) => ({status, states: seen.size, edges, applied, holds, depth_frontier: frontier,
      max_depth: contract.max_depth, phases: [...phases].sort(compare), transitions: [...covered].sort(compare).map(row => JSON.parse(row)), accepted_events: [...acceptedEvents].sort(compare), counterexample});
    for (let index = 0; index < queue.length; index++) {
      const [state, trace] = queue[index];
      if (trace.length === contract.max_depth) { frontier++; continue; }
      for (const event of contract.events) {
        if (edges >= contract.max_edges) return report('BUDGET_EXHAUSTED');
        const result = this.step(state, event); edges++;
        if (!['APPLIED', 'HOLD_NO_TRANSITION', 'HOLD_GUARD'].includes(result.status)) return report('COUNTEREXAMPLE', {events: [...trace, clone(event)], before: state, result});
        if (result.status !== 'APPLIED') { holds++; continue; }
        applied++; acceptedEvents.add(event.type); covered.add(key(result.transition)); phases.add(result.state.phase);
        const stateKey = key(result.state);
        if (!seen.has(stateKey)) {
          if (seen.size >= contract.max_states) return report('BUDGET_EXHAUSTED');
          seen.add(stateKey); queue.push([result.state, [...trace, clone(event)]]);
        }
      }
    }
    return report('BOUNDED_COMPLETE');
  }
  observe() {
    const scenarios = []; let inputUnchanged = true;
    for (const scenario of this.spec.scenarios) {
      let current = this.initial(); const actual = [], events = [];
      for (const step of scenario.steps) {
        const beforeState = clone(current), beforeEvent = clone(step.event), result = this.step(current, step.event);
        inputUnchanged = inputUnchanged && same(current, beforeState) && same(step.event, beforeEvent);
        actual.push(result); events.push(step.event); current = result.state;
      }
      const replay = this.replay(events), cut = Math.floor(events.length / 2), restored = this.restore(this.checkpoint(events.slice(0, cut))), resumed = this.replay(events.slice(cut), restored);
      scenarios.push({id: scenario.id, steps: actual, replay_equal: same(replay.results, actual),
        recovery_equal: same(resumed.results, actual.slice(cut)) && same(this.restore(this.checkpoint(events)), current)});
    }
    return {system_sha256: this.config.system_sha256, scenarios, input_unchanged: inputUnchanged, exploration: this.explore()};
  }
  verify() {
    const observed = this.observe(), issues = [], coverage = new Set(), events = new Set();
    this.spec.scenarios.forEach((expected, index) => {
      const actual = observed.scenarios[index];
      if (!actual.replay_equal || !actual.recovery_equal) issues.push({code: 'REPLAY_OR_RECOVERY', scenario: expected.id});
      expected.steps.forEach((step, i) => {
        const output = actual.steps[i];
        if (!Object.entries(step.expect).every(([field, value]) => same(output[field], value))) issues.push({code: 'SCENARIO_EXPECTATION', scenario: expected.id, step: i});
        if (output.status === 'APPLIED') { coverage.add(key(output.transition)); events.add(step.event.type); }
      });
    });
    const exploration = observed.exploration;
    if (exploration.status !== 'BOUNDED_COMPLETE') issues.push({code: 'EXPLORATION_' + exploration.status});
    exploration.transitions.forEach(row => coverage.add(key(row))); exploration.accepted_events.forEach(name => events.add(name));
    const missing = this.spec.machine.transitions.some(row => !coverage.has(key({from: row.from, event: row.event, to: row.to})));
    if (missing || this.spec.bindings.some(row => !events.has(row.event))) issues.push({code: 'TRANSITION_COVERAGE_INCOMPLETE'});
    if (!observed.input_unchanged) issues.push({code: 'INPUT_MUTATED'});
    return {status: issues.length ? 'HOLD' : 'PASS', issues, observations: observed};
  }
}

function load() {
  const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
  const lock = JSON.parse(fs.readFileSync(path.join(__dirname, 'source-lock.json'), 'utf8'));
  for (const name of ['runtime.js', 'module.js', 'system.json']) {
    if (crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, name))).digest('hex') !== lock[name]) throw Error('RUNTIME_SOURCE_CHANGED:' + name);
  }
  delete require.cache[require.resolve('./module.js')];
  return new System(JSON.parse(fs.readFileSync(path.join(__dirname, 'system.json'), 'utf8')), require('./module.js'));
}
module.exports = {System, load, same};
if (require.main === module) {
  try {
    const args = process.argv.slice(2), system = load(); let result;
    if (!args.length || same(args, ['verify'])) result = system.verify();
    else if (same(args, ['observe'])) result = system.observe();
    else if (args.length === 2 && ['replay', 'checkpoint', 'restore'].includes(args[0])) {
      const raw = require('node:fs').readFileSync(args[1]);
      if (raw.length > 1048576) throw Error('REQUEST_BYTES_LIMIT');
      result = system[args[0]](JSON.parse(raw));
    } else throw Error('usage: runtime.js [verify | replay events.json | checkpoint events.json | restore checkpoint.json]');
    const output = JSON.stringify(result);
    if (Buffer.byteLength(output) > 8 * 1048576) throw Error('RESULT_BYTES_LIMIT');
    process.stdout.write(output + '\n');
    if (result.status === 'HOLD') process.exitCode = 1;
  } catch (error) { process.stderr.write(JSON.stringify({status: 'HOLD', error: String(error.message).slice(0, 300)}) + '\n'); process.exitCode = 2; }
}
