/* ClearGlass Visual Engine · provenance pipeline (DEMO).
 * Visualises the governed evidence path:
 *   SOURCE -> IDENTIFIER -> HASH -> VALIDATION -> POLICY -> HUMAN_REVIEW -> DECISION
 * terminating in VERIFIED or QUARANTINED.
 *
 * The "hash" here is a SYMBOLIC, non-cryptographic demo digest (djb2) purely for
 * on-screen texture. It is NOT a security control and is always labelled DEMO.
 * This mirrors — but never replaces — the real SHA-256 RFED chain in the repo. */

export const PROV_STAGES = Object.freeze([
  'SOURCE', 'IDENTIFIER', 'HASH', 'VALIDATION', 'POLICY', 'HUMAN_REVIEW', 'DECISION',
]);

/** Symbolic demo digest — deterministic, short, explicitly not cryptographic. */
export function demoHash(input) {
  let h = 5381;
  const s = String(input);
  for (let i = 0; i < s.length; i++) h = (Math.imul(h, 33) ^ s.charCodeAt(i)) >>> 0;
  return 'demo:' + (h >>> 0).toString(16).padStart(8, '0');
}

export class ProvenancePipeline {
  constructor(opts = {}) {
    this.max = opts.max || 32;
    this.items = [];
    this.verified = 0;
    this.quarantined = 0;
  }

  /** Admit an artifact; it begins at SOURCE. */
  admit(spec) {
    if (this.items.length >= this.max) this.items.shift();
    const item = {
      label: (spec && spec.label) ? String(spec.label).slice(0, 120) : 'artifact',
      stageIndex: 0,
      stage: PROV_STAGES[0],
      hash: null,
      progress: 0,
      // Deterministic pass/quarantine derived from content, not randomness.
      willVerify: spec && spec.suspicious ? false : true,
      state: 'IN_PIPELINE',
      demo: true,
    };
    this.items.push(item);
    return item;
  }

  step(dt) {
    for (const it of this.items) {
      if (it.state !== 'IN_PIPELINE') continue;
      it.progress += dt * 0.6;
      if (it.progress >= 1) {
        it.progress = 0;
        it.stageIndex++;
        if (it.stageIndex === 2) it.hash = demoHash(it.label); // HASH stage stamps the demo digest
        if (it.stageIndex >= PROV_STAGES.length) {
          it.state = it.willVerify ? 'VERIFIED' : 'QUARANTINED';
          it.stage = it.state;
          if (it.willVerify) this.verified++; else this.quarantined++;
        } else {
          it.stage = PROV_STAGES[it.stageIndex];
        }
      }
    }
  }
}
