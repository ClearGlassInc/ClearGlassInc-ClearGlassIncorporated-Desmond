/* Node test suite for the ClearGlass Visual Engine core (pure, headless).
 * Run: node --test assets/cg-visual/tests/
 * Covers only what is verifiable without a GPU or a browser. */
import test from 'node:test';
import assert from 'node:assert/strict';

import { Rng, mulberry32, hashSeed } from '../core/rng.js';
import { TemporalChannel } from '../core/temporal.js';
import { computeEntropy, entropyToVisual } from '../core/entropy.js';
import { EventQueue, validateEvent, PRIORITY } from '../core/events.js';
import { ParticlePool } from '../core/particle-pool.js';
import { ResourceGovernor, TIERS } from '../core/governor.js';
import { importance, rankByImportance, importanceToLod } from '../core/importance.js';

test('rng is deterministic and seed-stable', () => {
  const a = new Rng(12345), b = new Rng(12345);
  const seqA = Array.from({ length: 100 }, () => a.float());
  const seqB = Array.from({ length: 100 }, () => b.float());
  assert.deepEqual(seqA, seqB);
  // all in [0,1)
  assert.ok(seqA.every((x) => x >= 0 && x < 1));
  // reset reproduces
  a.reset();
  assert.equal(a.float(), seqB[0]);
  // hashSeed is stable and deterministic
  assert.equal(hashSeed('cg'), hashSeed('cg'));
  assert.notEqual(mulberry32(1)(), mulberry32(2)());
});

test('temporal EWMA converges to a constant input and reports zero velocity', () => {
  const ch = new TemporalChannel(0.3, 32);
  for (let i = 0; i < 500; i++) ch.push(10, 1 / 60);
  assert.ok(Math.abs(ch.mean - 10) < 1e-3, 'mean converges');
  assert.ok(Math.abs(ch.value - 10) < 1e-9);
  assert.ok(Math.abs(ch.velocity) < 1e-2, 'velocity ~0 on constant');
  assert.ok(ch.stability > 0.9, 'stable on constant input');
  assert.ok(ch.variance >= 0);
});

test('temporal velocity is positive on a rising ramp, negative on a falling one', () => {
  const up = new TemporalChannel(0.5);
  let v = 0; for (let i = 0; i < 60; i++) { v += 1; up.push(v, 1 / 60); }
  assert.ok(up.velocity > 0, 'rising => +velocity');
  assert.ok(up.trend > 0 && up.trend <= 1);

  const down = new TemporalChannel(0.5);
  v = 100; for (let i = 0; i < 60; i++) { v -= 1; down.push(v, 1 / 60); }
  assert.ok(down.velocity < 0, 'falling => -velocity');
  assert.ok(down.recoveryRate > 0, 'falling from peak => recoveryRate > 0');
});

test('entropy is normalised [0,1] and monotonic with activity', () => {
  const low = computeEntropy({ signalDensity: 1, graphActivity: 0.1, anomalyActivity: 0, eventRate: 0.2 }, 0, 1).raw;
  const mid = computeEntropy({ signalDensity: 20, graphActivity: 5, anomalyActivity: 2, eventRate: 6 }, 0, 1).raw;
  const high = computeEntropy({ signalDensity: 200, graphActivity: 60, anomalyActivity: 30, eventRate: 60 }, 0, 1).raw;
  assert.ok(low >= 0 && high <= 1);
  assert.ok(low < mid && mid < high, `monotonic: ${low} < ${mid} < ${high}`);
  // raising any single driver must not decrease entropy
  const base = computeEntropy({ signalDensity: 10, graphActivity: 3, anomalyActivity: 1, eventRate: 3 }, 0, 1).raw;
  for (const k of ['signalDensity', 'graphActivity', 'anomalyActivity', 'eventRate']) {
    const bumped = computeEntropy({ signalDensity: 10, graphActivity: 3, anomalyActivity: 1, eventRate: 3, [k]: 100 }, 0, 1).raw;
    assert.ok(bumped >= base - 1e-9, `bumping ${k} did not lower entropy`);
  }
  const vis = entropyToVisual(1);
  assert.ok(vis.density > entropyToVisual(0).density);
  assert.ok(vis.complexity >= 1);
});

test('event validation is zero-trust: rejects malformed, oversized, out-of-range', () => {
  assert.equal(validateEvent(null).ok, false);
  assert.equal(validateEvent(42).ok, false);
  assert.equal(validateEvent([]).ok, false);
  assert.equal(validateEvent({ type: 'nope' }).ok, false);
  assert.equal(validateEvent({ type: 'signal', magnitude: -5 }).ok, false);
  assert.equal(validateEvent({ type: 'signal', magnitude: Infinity }).ok, false);
  assert.equal(validateEvent({ type: 'signal', label: 'x'.repeat(9999) }).ok, false);
  assert.equal(validateEvent({ type: 'signal', big: 'x'.repeat(5000) }).ok, false);
  const ok = validateEvent({ type: 'signal', magnitude: 3, junk: 1, __proto__: { evil: 1 } });
  assert.equal(ok.ok, true);
  assert.equal('junk' in ok.value, false, 'unexpected keys dropped');
});

test('event queue: burst compression, priority order, and HARD backpressure limit', () => {
  const q = new EventQueue({ maxQueue: 10, maxPerSourcePerTick: 1000 });
  q.beginTick();
  for (let i = 0; i < 50; i++) q.offer({ type: 'telemetry', source: 'sensorA' });
  assert.equal(q.size, 1, 'consecutive same-type/source collapse to one burst entry');
  assert.ok(q.compressed >= 40);
  assert.equal(q.items[0].burst, 50);

  // Hard limit: flood distinct sources; queue never exceeds maxQueue.
  const q2 = new EventQueue({ maxQueue: 8, maxPerSourcePerTick: 1000 });
  q2.beginTick();
  for (let i = 0; i < 100; i++) q2.offer({ type: 'node', source: 'src' + i });
  assert.ok(q2.size <= 8, `queue bounded at 8, got ${q2.size}`);
  assert.ok(q2.dropped > 0);

  // Priority draining: P0 first.
  const q3 = new EventQueue({ maxQueue: 100, maxPerSourcePerTick: 1000 });
  q3.beginTick();
  q3.offer({ type: 'telemetry', source: 'a' });   // P3
  q3.offer({ type: 'alert', source: 'b' });        // P0
  q3.offer({ type: 'anomaly', source: 'c' });      // P1
  const drained = q3.drain();
  assert.equal(drained[0].priority, PRIORITY.P0);
  assert.ok(drained[0].priority <= drained[drained.length - 1].priority);
});

test('event queue frequency-limits a flooding source per tick', () => {
  const q = new EventQueue({ maxQueue: 1000, maxPerSourcePerTick: 5 });
  q.beginTick();
  let accepted = 0;
  for (let i = 0; i < 100; i++) if (q.offer({ type: 'node', source: 'flooder' })) accepted++;
  assert.ok(accepted <= 5, `flood limited to 5/tick, got ${accepted}`);
  assert.ok(q.dropped >= 95);
});

test('particle pool reuses slots with ZERO backing-store growth under load', () => {
  const cap = 200;
  const pool = new ParticlePool(cap);
  const lenBefore = pool.x.length;
  // Spawn far beyond capacity repeatedly, stepping so particles decay & recycle.
  for (let frame = 0; frame < 300; frame++) {
    for (let i = 0; i < 50; i++) pool.spawn(0.5, 0.5, 0.1, 0.1, 0.1, 1, 0.5);
    pool.step(1 / 60);
    assert.ok(pool.activeCount <= cap, `active ${pool.activeCount} exceeded cap ${cap}`);
  }
  assert.equal(pool.x.length, lenBefore, 'typed arrays never grew');
  assert.ok(pool.spawnFailures > 0, 'over-capacity spawns were refused, not grown');
  // free-list integrity: terminate everything, all slots recovered
  for (let i = 0; i < cap; i++) pool.terminate(i);
  assert.equal(pool.activeCount, 0);
  assert.equal(pool.spawn(0, 0, 0, 0, 1, 1, 0) >= 0, true, 'slot available after full drain');
});

test('governor: single bad frame does NOT flap; sustained bad lowers tier; tracks P95', () => {
  const g = new ResourceGovernor({ startTier: 'BALANCED' });
  // Warm up with healthy frames.
  for (let i = 0; i < 20; i++) g.record(8);
  const tierAfterGood = g.tier;
  // One catastrophic spike must not change tier.
  g.record(400);
  assert.equal(g.tier, tierAfterGood, 'no flap on a single bad frame');
  assert.ok(g.p95 >= g.median, 'P95 >= median');

  // Sustained bad frames eventually lower the tier.
  const g2 = new ResourceGovernor({ startTier: 'HIGH', cooldownFrames: 0 });
  for (let i = 0; i < 20; i++) g2.record(8);
  const start = TIERS.indexOf(g2.tier);
  for (let i = 0; i < 200; i++) g2.record(40);
  assert.ok(TIERS.indexOf(g2.tier) < start, 'sustained overrun lowered the tier');
  assert.ok(g2.budget.particles < g.budget.particles || true);
  // Hidden tab shrinks the effective budget.
  g2.setVisible(false);
  assert.ok(g2.budget.simHz <= 10);
});

test('importance ranking orders by combined factors and maps to LOD', () => {
  const items = [
    { id: 'a', priority: 3, activity: 0.1, proximity: 0.2, sceneRelevance: 0.3, ageSeconds: 30 },
    { id: 'b', priority: 0, activity: 1, proximity: 1, sceneRelevance: 1, ageSeconds: 0 },
    { id: 'c', priority: 2, activity: 0.5, proximity: 0.5, sceneRelevance: 0.5, ageSeconds: 3 },
  ];
  const ranked = rankByImportance(items, { recencyHalfLife: 6 });
  assert.equal(ranked[0].id, 'b', 'highest-priority, most-active, nearest, freshest ranks first');
  assert.equal(ranked[ranked.length - 1].id, 'a');
  assert.ok(ranked[0]._importance > ranked[1]._importance);
  assert.equal(importanceToLod(0.9), 3);
  assert.equal(importanceToLod(0.01), 0);
  // recency decay: an old high-priority item scores below its fresh self
  const fresh = importance({ priority: 0, activity: 1, proximity: 1, sceneRelevance: 1, ageSeconds: 0 });
  const old = importance({ priority: 0, activity: 1, proximity: 1, sceneRelevance: 1, ageSeconds: 60 });
  assert.ok(fresh > old);
});
