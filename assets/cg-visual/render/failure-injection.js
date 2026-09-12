/* ClearGlass Visual Engine · dev-only failure injection.
 * Lets a developer force degraded conditions to prove the resilience paths.
 * Gated identically to the HUD (never active in production by default). It is
 * exposed on window.__cgVisual.faults only when debug is enabled.
 *
 * Faults: disableWebGPU, disableWebGL, forceCanvas, forceLowFps, floodEvents,
 * contextLoss, throwInScene, reducedMotion, hiddenTab. */

export function faultsEnabled() {
  try {
    const q = typeof location !== 'undefined' && /[?&]cgfault=/.test(location.search);
    const ls = typeof localStorage !== 'undefined' && localStorage.getItem('cg-visual-debug') === '1';
    return !!(q || ls);
  } catch (e) { return false; }
}

/** Parse ?cgfault=forceCanvas,floodEvents into a set of active fault names. */
export function parseFaults() {
  const set = new Set();
  try {
    const m = typeof location !== 'undefined' && location.search.match(/[?&]cgfault=([^&]+)/);
    if (m) decodeURIComponent(m[1]).split(',').forEach((f) => set.add(f.trim()));
  } catch (e) {}
  return set;
}

/** Build a controller bound to a live engine instance. */
export function createFaultController(engine) {
  const state = { forceLowFps: false, floodEvents: false, throwInScene: false };
  return {
    state,
    disableWebGPU() { engine.opts.allowWebGPU = false; return engine.reinitBackend(); },
    disableWebGL() { engine.opts.forced = 'canvas2d'; return engine.reinitBackend(); },
    forceCanvas() { engine.opts.forced = 'canvas2d'; return engine.reinitBackend(); },
    forceLowFps(on = true) { state.forceLowFps = on; },
    floodEvents(on = true) { state.floodEvents = on; },
    throwInScene(on = true) { state.throwInScene = on; },
    contextLoss() { return engine.simulateContextLoss(); },
    reducedMotion(on = true) { engine.setReducedMotion(on); },
    hiddenTab(on = true) { engine.setVisible(!on); },
  };
}
