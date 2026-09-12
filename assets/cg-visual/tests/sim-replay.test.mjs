/* Node tests for the Simulation + deterministic replay. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { Simulation } from '../core/simulation.js';
import { Recorder, replay } from '../core/replay.js';

const SEED = 987654;

function scriptedEvents(i, rng) {
  // A deterministic event script keyed off the frame index.
  const out = [];
  if (i % 5 === 0) out.push({ type: 'signal', source: 'core', magnitude: 3 });
  if (i % 11 === 0) out.push({ type: 'anomaly', source: 'sensor', magnitude: 42 });
  if (i % 17 === 0) out.push({ type: 'node', source: 'graph' });
  if (i % 23 === 0) out.push({ type: 'provenance', source: 'ledger', label: 'artifact-' + i });
  if (i % 7 === 0) out.push({ type: 'pipeline', source: 'ai', label: 'job-' + i });
  return out;
}

test('same seed + same event sequence => bit-identical WorldState snapshot', () => {
  const runOnce = () => {
    const sim = new Simulation(SEED, { particleCapacity: 2000 });
    for (let i = 1; i <= 400; i++) {
      for (const e of scriptedEvents(i)) sim.emit(e);
      sim.step(1 / 60);
    }
    return sim.snapshot();
  };
  const a = runOnce();
  const b = runOnce();
  assert.deepEqual(a, b, 'two identical runs produced identical snapshots');
});

test('Recorder + replay() reproduce the recorded run exactly', () => {
  const rec = new Recorder(SEED, { particleCapacity: 2000 });
  for (let i = 1; i <= 250; i++) rec.tick(1 / 60, scriptedEvents(i));
  const liveSnap = rec.sim.snapshot();
  const recording = rec.record();

  const first = replay(recording).snapshot;
  const second = replay(recording).snapshot;
  assert.deepEqual(first, second, 'replay is deterministic across invocations');
  assert.deepEqual(first, liveSnap, 'replay matches the originally recorded live run');
});

test('pause halts advancement; stepOnce advances exactly one frame', () => {
  const rec = new Recorder(SEED);
  for (let i = 0; i < 10; i++) rec.tick(1 / 60, []);
  const f = rec.sim.world.frame;
  rec.pause();
  rec.tick(1 / 60, []);              // ignored while paused
  assert.equal(rec.sim.world.frame, f, 'paused recorder does not advance via tick');
  rec.stepOnce(1 / 60, []);          // explicit single step
  assert.equal(rec.sim.world.frame, f + 1);
});

test('entropy and system state escalate with a heavy event load', () => {
  const calm = new Simulation(SEED);
  for (let i = 1; i <= 300; i++) { if (i % 40 === 0) calm.emit({ type: 'telemetry', source: 's' }); calm.step(1 / 60); }

  const storm = new Simulation(SEED);
  for (let i = 1; i <= 300; i++) {
    for (let k = 0; k < 6; k++) storm.emit({ type: 'anomaly', source: 'sensor' + k, magnitude: 80 });
    for (let k = 0; k < 6; k++) storm.emit({ type: 'signal', source: 'src' + k, magnitude: 5 });
    storm.step(1 / 60);
  }
  assert.ok(storm.world.entropy > calm.world.entropy, `storm entropy ${storm.world.entropy} > calm ${calm.world.entropy}`);
  assert.ok(storm.world.entropy >= 0 && storm.world.entropy <= 1);
  assert.notEqual(storm.world.systemState, 'NOMINAL', 'heavy load escalates system state');
});

test('simulation never exceeds hard population limits under an event flood', () => {
  const sim = new Simulation(SEED, { particleCapacity: 800, maxSignals: 64 });
  for (let i = 1; i <= 500; i++) {
    for (let k = 0; k < 200; k++) sim.emit({ type: 'signal', source: 'flood' + (k % 30), magnitude: 4 });
    sim.step(1 / 60);
    assert.ok(sim.pool.activeCount <= 800, 'particle cap held');
    assert.ok(sim.signals.signals.length <= 64, 'signal cap held');
    assert.ok(sim.queue.size <= 256, 'event queue cap held');
    assert.ok(sim.graph.nodes.length <= 40, 'node cap held');
  }
});
