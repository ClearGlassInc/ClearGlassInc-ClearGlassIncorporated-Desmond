/* ClearGlass Visual Engine · evidence-chain instrument (browser).
 *
 * Upgrades a static, readable ordered list of stages:
 *
 *   <figure data-cg-instrument="chain">
 *     <ol class="cg-chain__stages">
 *       <li class="cg-chain__stage" [data-gate]><i class="cg-chain__node"></i><b>Stage</b><span>note</span></li>
 *     </ol>
 *   </figure>
 *
 * A packet dwells at each stage, travels to the next, and the run ends sealed
 * at the last stage; a stage marked data-gate (human approval) holds the packet
 * longer, so the motion shows the wait instead of implying automation skips it.
 * The list stays the source of truth: screen readers and no-JS visitors read
 * the same stages in the same order. Nothing here claims to be live. */

import { Rng, hashSeed } from '../core/rng.js';
import { boundedDelay, chainDuration, chainState } from '../core/cadence.js';

const GATE_DWELL_MS = 1700;
const DWELL_MS = 560;
const TRAVEL_MS = 680;
const SEAL_MS = 1200;

function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

export function mount(host, scheduler) {
  const list = host.querySelector('.cg-chain__stages');
  const stages = list ? Array.from(list.querySelectorAll('.cg-chain__stage')) : [];
  if (stages.length < 2) return null;
  const nodes = stages.map((li) => li.querySelector('.cg-chain__node') || li);

  const rng = new Rng(hashSeed(host.id || 'cg-chain'));
  const plan = {
    stages: stages.length,
    travelMs: TRAVEL_MS,
    defaultDwellMs: DWELL_MS,
    dwellMs: stages.map((li) => (li.hasAttribute('data-gate') ? GATE_DWELL_MS : DWELL_MS)),
    sealMs: SEAL_MS,
  };
  const runMs = chainDuration(plan);

  const packet = document.createElement('span');
  packet.className = 'cg-chain__packet';
  packet.setAttribute('aria-hidden', 'true');
  host.appendChild(packet);

  // Geometry is read on mount and on resize only, never per frame.
  let points = [];
  function measure() {
    const base = host.getBoundingClientRect();
    points = nodes.map((n) => {
      const r = n.getBoundingClientRect();
      return { x: r.left - base.left + r.width / 2, y: r.top - base.top + r.height / 2 };
    });
  }
  measure();
  const ro = 'ResizeObserver' in window ? new ResizeObserver(measure) : null;
  if (ro) ro.observe(host);

  let mode = 'static';
  let runStart = 0;
  let restUntil = 0;
  let lastKey = '';
  let sealedEmitted = false;

  function setStageClasses(state) {
    const key = state ? `${state.phase}:${state.stage}` : 'idle';
    if (key === lastKey) return; // write the DOM only on transitions
    lastKey = key;
    stages.forEach((li, i) => {
      const active = !!state && i === state.stage && state.phase === 'dwell';
      li.classList.toggle('is-active', active);
      li.classList.toggle('is-passed', !!state && (i < state.stage || (state.phase === 'travel' && i === state.stage)));
      li.classList.toggle('is-holding', active && li.hasAttribute('data-gate'));
    });
    host.classList.toggle('is-sealed', !!state && state.phase === 'sealed');
  }

  function reset() {
    setStageClasses(null);
    packet.classList.remove('is-on');
  }

  return scheduler.add({
    host,
    setMode(next) {
      mode = next;
      host.classList.toggle('cg-instrument--static', next === 'static');
      host.classList.toggle('cg-instrument--live', next !== 'static');
      if (next === 'static') { reset(); runStart = 0; restUntil = 0; }
    },
    frame(now) {
      if (mode === 'static' || !points.length) return;
      if (!runStart) {
        if (now < restUntil) return;
        runStart = now;
        sealedEmitted = false;
        packet.classList.add('is-on');
      }
      const t = now - runStart;
      if (t >= runMs) {
        reset();
        runStart = 0;
        restUntil = now + boundedDelay(rng, 2400, 5200);
        return;
      }
      const st = chainState(t, plan);
      let p;
      if (st.phase === 'travel') {
        const a = points[st.stage], b = points[st.to], k = ease(st.progress);
        p = { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k };
      } else {
        p = points[st.stage];
      }
      packet.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`;
      setStageClasses(st);
      if (st.phase === 'sealed' && !sealedEmitted) {
        sealedEmitted = true;
        scheduler.emit({ type: 'provenance', label: 'governed action sealed (illustrative)' });
      }
    },
    dispose() { if (ro) ro.disconnect(); },
  });
}
