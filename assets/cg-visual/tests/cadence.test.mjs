/* Node tests for core/cadence.js — the timing and policy behind the in-content
 * instruments. Run: node --test assets/cg-visual/tests/ */
import test from 'node:test';
import assert from 'node:assert/strict';

import { Rng } from '../core/rng.js';
import { TIERS } from '../core/governor.js';
import {
  boundedDelay, instrumentPolicy, chainDuration, chainState,
  seedTargets, angularGap, sweepHits,
} from '../core/cadence.js';

test('boundedDelay stays inside its window and is seed-deterministic', () => {
  const a = new Rng(7), b = new Rng(7);
  for (let i = 0; i < 500; i++) {
    const d = boundedDelay(a, 2200, 4600);
    assert.ok(d >= 2200 && d <= 4600, `out of window: ${d}`);
    assert.equal(d, boundedDelay(b, 2200, 4600));
  }
  // A reversed window is normalised rather than producing negatives.
  const r = new Rng(3);
  for (let i = 0; i < 50; i++) {
    const d = boundedDelay(r, 900, 300);
    assert.ok(d >= 300 && d <= 900);
  }
});

test('instrumentPolicy: reduced motion always wins, and every governor tier maps', () => {
  for (const tier of [null, ...TIERS]) {
    assert.equal(instrumentPolicy({ reduced: true, tier }).mode, 'static');
  }
  assert.equal(instrumentPolicy({ tier: 'MINIMAL' }).mode, 'static');
  assert.equal(instrumentPolicy({ tier: 'LOW' }).mode, 'lite');
  assert.equal(instrumentPolicy({ tier: 'HIGH', saveData: true }).mode, 'lite');
  assert.equal(instrumentPolicy({ tier: 'ULTRA', narrow: true }).mode, 'lite');
  assert.equal(instrumentPolicy({ tier: 'BALANCED' }).mode, 'full');
  // No engine on the page (tier null) still animates on a capable screen.
  assert.equal(instrumentPolicy({}).mode, 'full');
  // Static never asks for frames or signals.
  const s = instrumentPolicy({ reduced: true });
  assert.equal(s.fps, 0);
  assert.equal(s.signals, 0);
});

test('chainState walks every stage in order and ends sealed, then done', () => {
  const plan = { stages: 4, travelMs: 100, defaultDwellMs: 50, dwellMs: [50, 50, 400, 50], sealMs: 200 };
  assert.equal(chainDuration(plan), 50 + 50 + 400 + 50 + 3 * 100 + 200);

  const seen = [];
  for (let t = 0; t <= chainDuration(plan) + 10; t += 5) {
    const s = chainState(t, plan);
    const key = s.phase === 'travel' ? `travel:${s.stage}->${s.to}` : `${s.phase}:${s.stage}`;
    if (seen[seen.length - 1] !== key) seen.push(key);
    assert.ok(s.progress >= 0 && s.progress <= 1, `progress out of range at ${t}`);
  }
  assert.deepEqual(seen, [
    'dwell:0', 'travel:0->1', 'dwell:1', 'travel:1->2',
    'dwell:2', 'travel:2->3', 'dwell:3', 'sealed:3', 'done:3',
  ]);
});

test('chainState gives a gate stage its longer dwell', () => {
  const plan = { stages: 3, travelMs: 100, defaultDwellMs: 50, dwellMs: [50, 900, 50], sealMs: 100 };
  // Gate stage 1 starts after dwell 0 + travel 0->1 = 150ms and lasts 900ms.
  assert.equal(chainState(160, plan).phase, 'dwell');
  assert.equal(chainState(160, plan).stage, 1);
  assert.equal(chainState(1040, plan).stage, 1);
  assert.equal(chainState(1060, plan).phase, 'travel');
  // Negative time clamps to the start rather than throwing.
  assert.deepEqual(chainState(-5, plan), { phase: 'dwell', stage: 0, progress: 0 });
});

test('seedTargets: separated bearings, bounded ranges, labelled as examples', () => {
  const targets = seedTargets(new Rng(20260912), 5);
  assert.equal(targets.length, 5);
  for (let i = 0; i < targets.length; i++) {
    const t = targets[i];
    assert.match(t.id, /^EX-\d{2}$/);
    assert.ok(t.bearing >= 0 && t.bearing < 360);
    assert.ok(t.range >= 0.28 && t.range <= 0.86);
    for (let j = i + 1; j < targets.length; j++) {
      assert.ok(angularGap(t.bearing, targets[j].bearing) >= 40);
    }
  }
  assert.deepEqual(seedTargets(new Rng(1), 5), seedTargets(new Rng(1), 5));
});

test('sweepHits handles the wrap through north and never fires a full turn', () => {
  const targets = [{ id: 'A', bearing: 10 }, { id: 'B', bearing: 350 }, { id: 'C', bearing: 180 }];
  assert.deepEqual(sweepHits(0, 20, targets).map((t) => t.id), ['A']);
  // 340 -> 380 (unwrapped) crosses north: B at 350, then A at 10 (= 370).
  assert.deepEqual(sweepHits(340, 380, targets).map((t) => t.id), ['A', 'B']);
  assert.deepEqual(sweepHits(170, 181, targets).map((t) => t.id), ['C']);
  // Exactly on the previous angle is not re-fired; exactly on the next one is.
  assert.deepEqual(sweepHits(10, 15, targets), []);
  assert.deepEqual(sweepHits(5, 10, targets).map((t) => t.id), ['A']);
  // No movement, backwards movement, or a full turn report nothing.
  assert.deepEqual(sweepHits(50, 50, targets), []);
  assert.deepEqual(sweepHits(60, 50, targets), []);
  assert.deepEqual(sweepHits(0, 360, targets), []);
  assert.deepEqual(sweepHits(0, 900, targets), []);
});
