/* ClearGlass Visual Engine · sensor-scope instrument (browser).
 *
 * Upgrades <div class="cg-radar__scope" role="img" aria-label="…"> inside a
 * figure[data-cg-instrument="radar"]. Rings and crosshair are CSS (visible with
 * no JS); bearing ticks and example targets are a static SVG drawn once; the
 * sweep is a separate layer rotated with a CSS transform, so per-frame work is
 * one transform write plus class toggles when a target pings.
 *
 * Every target is an EXAMPLE signal (EX-nn) from a seeded generator. Nothing
 * here observes, monitors or detects anything real, and the figure caption
 * says so. When the sweep passes a target it pings; some pings are marked
 * "correlated" and handed to the background engine as a signal event, which
 * is how one example signal shows up across both visual layers. */

import { Rng, hashSeed } from '../core/rng.js';
import { seedTargets, sweepHits } from '../core/cadence.js';

const SVG = 'http://www.w3.org/2000/svg';
const PERIOD_MS = { full: 7200, lite: 10800 };
const PING_MS = 1400;
const LINK_MS = 1800;
const CORRELATE_EVERY = 3; // every third ping is correlated: steady, not random bursts

function el(name, attrs) {
  const n = document.createElementNS(SVG, name);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  return n;
}

function polar(bearingDeg, r) {
  // Bearing 0 = north (up), clockwise, in a 200x200 viewBox centred on 100,100.
  const a = (bearingDeg - 90) * Math.PI / 180;
  return { x: 100 + Math.cos(a) * r, y: 100 + Math.sin(a) * r };
}

export function mount(host, scheduler) {
  const scope = host.querySelector('.cg-radar__scope');
  if (!scope) return null;

  const rng = new Rng(hashSeed(host.id || 'cg-radar'));
  const targets = seedTargets(rng, 5);

  // Rings and crosshair are CSS backgrounds on the scope (so the scope reads as
  // a scope with no JS at all); the SVG adds what needs coordinates.
  const svg = el('svg', { viewBox: '0 0 200 200', class: 'cg-radar__svg', 'aria-hidden': 'true', focusable: 'false' });
  const grid = el('g', { class: 'cg-radar__grid' });
  for (let b = 0; b < 360; b += 15) {
    const major = b % 90 === 0;
    const p1 = polar(b, major ? 86 : 90), p2 = polar(b, 94);
    grid.appendChild(el('line', { x1: p1.x.toFixed(2), y1: p1.y.toFixed(2), x2: p2.x.toFixed(2), y2: p2.y.toFixed(2), class: major ? 'is-major' : '' }));
  }
  svg.appendChild(grid);

  const labels = el('g', { class: 'cg-radar__bearings' });
  for (const [b, txt] of [[0, '000'], [90, '090'], [180, '180'], [270, '270']]) {
    const p = polar(b, 80);
    const t = el('text', { x: p.x.toFixed(2), y: (p.y + 2.5).toFixed(2), 'text-anchor': 'middle' });
    t.textContent = txt;
    labels.appendChild(t);
  }
  svg.appendChild(labels);

  const link = el('line', { class: 'cg-radar__link', x1: 100, y1: 100, x2: 100, y2: 100 });
  svg.appendChild(link);

  const marks = targets.map((t) => {
    const p = polar(t.bearing, t.range * 94);
    const g = el('g', { class: 'cg-radar__target', transform: `translate(${p.x.toFixed(2)} ${p.y.toFixed(2)})` });
    g.appendChild(el('circle', { class: 'cg-radar__ring', r: 6 }));
    g.appendChild(el('circle', { class: 'cg-radar__dot', r: 1.8 }));
    const label = el('text', { class: 'cg-radar__label', x: 5, y: -5 });
    label.textContent = t.id;
    g.appendChild(label);
    svg.appendChild(g);
    return { t, g, p, pingUntil: 0 };
  });

  const sweep = document.createElement('div');
  sweep.className = 'cg-radar__sweep';
  sweep.setAttribute('aria-hidden', 'true');

  scope.appendChild(svg);
  scope.appendChild(sweep);

  let mode = 'static';
  let start = 0;
  let prevAngle = 0;
  let pings = 0;
  let linkUntil = 0;

  return scheduler.add({
    host,
    setMode(next) {
      mode = next;
      host.classList.toggle('cg-instrument--static', next === 'static');
      host.classList.toggle('cg-instrument--live', next !== 'static');
      start = 0;
      if (next === 'static') {
        sweep.style.transform = '';
        for (const m of marks) { m.g.classList.remove('is-ping'); m.pingUntil = 0; }
        link.classList.remove('is-on');
      }
    },
    frame(now) {
      if (mode === 'static') return;
      const period = PERIOD_MS[mode] || PERIOD_MS.full;
      if (!start) { start = now; prevAngle = 0; }
      const angle = ((now - start) / period) * 360; // unwrapped
      sweep.style.transform = `rotate(${(angle % 360).toFixed(2)}deg)`;

      for (const t of sweepHits(prevAngle, angle, targets)) {
        const m = marks.find((x) => x.t === t);
        m.pingUntil = now + PING_MS;
        m.g.classList.add('is-ping');
        pings += 1;
        if (pings % CORRELATE_EVERY === 0) {
          link.setAttribute('x2', m.p.x.toFixed(2));
          link.setAttribute('y2', m.p.y.toFixed(2));
          link.classList.add('is-on');
          linkUntil = now + LINK_MS;
          scheduler.emit({ type: 'signal', label: `${t.id} example signal correlated` });
        }
      }
      prevAngle = angle;

      for (const m of marks) {
        if (m.pingUntil && now >= m.pingUntil) { m.pingUntil = 0; m.g.classList.remove('is-ping'); }
      }
      if (linkUntil && now >= linkUntil) { linkUntil = 0; link.classList.remove('is-on'); }
    },
  });
}
