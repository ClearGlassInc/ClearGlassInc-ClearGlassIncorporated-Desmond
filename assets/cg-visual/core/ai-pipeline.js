/* ClearGlass Visual Engine · AI pipeline visualization (observable stages only).
 * Shows the OBSERVABLE governance stages of a model-assisted action:
 *   INPUT -> CLASSIFY -> RETRIEVE -> ANALYZE -> POLICY -> CONFIDENCE -> OVERSIGHT -> OUTPUT
 * It renders only stage transitions and a confidence scalar. It NEVER exposes
 * private chain-of-thought or model internals — those are not modelled here. */

export const AI_STAGES = Object.freeze([
  'INPUT', 'CLASSIFY', 'RETRIEVE', 'ANALYZE', 'POLICY', 'CONFIDENCE', 'OVERSIGHT', 'OUTPUT',
]);

export class AiPipeline {
  constructor(opts = {}) {
    this.max = opts.max || 12;
    this.jobs = [];
  }

  submit(spec = {}) {
    if (this.jobs.length >= this.max) this.jobs.shift();
    const job = {
      label: (spec.label ? String(spec.label).slice(0, 80) : 'task'),
      stageIndex: 0,
      stage: AI_STAGES[0],
      progress: 0,
      confidence: 0,                 // populated at the CONFIDENCE stage
      requiresOversight: false,      // set at POLICY based on confidence
      state: 'RUNNING',
    };
    this.jobs.push(job);
    return job;
  }

  step(dt, rng) {
    for (const j of this.jobs) {
      if (j.state !== 'RUNNING') continue;
      j.progress += dt * 0.8;
      if (j.progress < 1) continue;
      j.progress = 0;
      j.stageIndex++;
      if (j.stageIndex >= AI_STAGES.length) { j.state = 'DONE'; j.stage = 'OUTPUT'; continue; }
      j.stage = AI_STAGES[j.stageIndex];
      if (j.stage === 'CONFIDENCE') j.confidence = rng ? rng.range(0.4, 0.99) : 0.7;
      if (j.stage === 'POLICY') {
        // Governance rule (mirrors the repo's model): low confidence escalates.
        j.requiresOversight = j.confidence > 0 ? j.confidence < 0.6 : true;
      }
    }
  }
}
