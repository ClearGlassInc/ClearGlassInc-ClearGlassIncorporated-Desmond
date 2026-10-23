/* ClearGlass Visual Engine · interface-telemetry instrument (browser).
 *
 * Fills <dd data-cg-tel="…"> cells inside figure[data-cg-instrument="telemetry"]
 * with the page's OWN state. Every value is true of this page, right now:
 *
 *   motion   — what the site's motion control / OS setting resolves to
 *   tier     — the background engine's ResourceGovernor tier, or "Static"
 *   renderer — the engine's actual backend (WebGPU / WebGL2 / Canvas 2D), or "None"
 *   signals  — how many example signals this page has animated since it loaded
 *
 * Nothing is fetched and nothing describes the outside world. Cells without a
 * data-cg-tel key (Mode, Data source) are static markup and are left alone.
 * There is deliberately no aria-live: a ticking counter announced to a screen
 * reader is noise, and the values are readable on demand. */

const TIER_LABEL = { MINIMAL: 'Minimal', LOW: 'Low', BALANCED: 'Balanced', HIGH: 'High', ULTRA: 'Ultra' };
const BACKEND_LABEL = { webgpu: 'WebGPU', webgl2: 'WebGL2', canvas2d: 'Canvas 2D', canvas: 'Canvas 2D', static: 'Static' };

function backendName(engine) {
  if (!engine) return 'None';
  const b = engine.backend;
  const raw = (b && b.kind) || (engine.sim && engine.sim.world && engine.sim.world.renderBackend) || '';
  const key = String(raw).toLowerCase();
  return BACKEND_LABEL[key] || (raw ? String(raw) : 'Unknown');
}

export function mount(host, scheduler) {
  const cells = {};
  for (const dd of host.querySelectorAll('[data-cg-tel]')) cells[dd.getAttribute('data-cg-tel')] = dd;
  if (!Object.keys(cells).length) return null;

  const write = (key, value) => {
    const dd = cells[key];
    if (dd && dd.textContent !== value) dd.textContent = value;
  };

  function render() {
    const engine = scheduler.engine();
    const mode = scheduler.policy.mode;
    write('motion', scheduler.reduced() ? 'Reduced' : 'Full');
    // The governor's own tier, verbatim. (The instruments' resulting mode is
    // exposed as data-cg-mode, not mixed into this row.)
    write('tier', TIER_LABEL[scheduler.tier()] || (engine ? 'Starting' : 'Not running'));
    write('renderer', backendName(engine));
    write('signals', String(scheduler.signalsTraced));
    host.setAttribute('data-cg-mode', mode);
  }

  render();
  const unsubscribe = scheduler.subscribe(render);
  let next = 0;

  return scheduler.add({
    host,
    setMode() { render(); },
    // The engine boots on idle and its tier moves slowly; a 2s refresh while
    // on screen is enough and costs a few text comparisons.
    frame(now) { if (now >= next) { next = now + 2000; render(); } },
    dispose() { unsubscribe(); },
  });
}
