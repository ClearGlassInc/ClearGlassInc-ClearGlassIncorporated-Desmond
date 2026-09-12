/* ClearGlass Visual Engine · dev diagnostics HUD.
 * DISABLED by default in production. Enabled only when ?cgdebug=1 is in the URL
 * or localStorage['cg-visual-debug']==='1'. Shows FPS / frame time / P95 / sim
 * time / particle / node / edge / queue / scenes / LOD / quality / DPR /
 * backend / pool load. Text only — no untrusted HTML is ever injected. */

export function hudEnabled() {
  try {
    const q = typeof location !== 'undefined' && /[?&]cgdebug=1\b/.test(location.search);
    const ls = typeof localStorage !== 'undefined' && localStorage.getItem('cg-visual-debug') === '1';
    return !!(q || ls);
  } catch (e) { return false; }
}

export class Hud {
  constructor() {
    this.el = null;
    if (typeof document === 'undefined') return;
    const el = document.createElement('div');
    el.id = 'cg-visual-hud';
    el.setAttribute('aria-hidden', 'true');
    el.style.cssText = [
      'position:fixed', 'bottom:8px', 'left:8px', 'z-index:2147483000',
      'font:11px/1.35 ui-monospace,Menlo,Consolas,monospace',
      'color:#ffd7db', 'background:rgba(20,4,6,0.82)', 'border:1px solid rgba(234,70,72,0.5)',
      'border-radius:8px', 'padding:8px 10px', 'pointer-events:none', 'white-space:pre',
      'max-width:44vw', 'backdrop-filter:blur(4px)',
    ].join(';');
    document.body.appendChild(el);
    this.el = el;
  }
  /** Update from a plain metrics object. Uses textContent — never innerHTML. */
  update(m) {
    if (!this.el) return;
    this.el.textContent =
      'CG VISUAL · DEMO diagnostics\n' +
      'backend  ' + m.backend + '   quality ' + m.quality + '  DPR ' + m.dpr + '\n' +
      'fps ' + m.fps.toFixed(0) + '  frame ' + m.frameMs.toFixed(1) + 'ms  P95 ' + m.p95.toFixed(1) + 'ms\n' +
      'sim ' + m.simMs.toFixed(2) + 'ms  state ' + m.systemState + '  entropy ' + m.entropy.toFixed(2) + '\n' +
      'particles ' + m.particles + '/' + m.poolCap + ' (' + (m.load * 100).toFixed(0) + '%)  pool-refused ' + m.spawnFailures + '\n' +
      'nodes ' + m.nodes + '  edges ' + m.edges + '  signals ' + m.signals + '  queue ' + m.queue + '\n' +
      'lod ' + m.lod + '  scenes ' + m.scenes;
  }
  dispose() { if (this.el && this.el.remove) this.el.remove(); this.el = null; }
}
