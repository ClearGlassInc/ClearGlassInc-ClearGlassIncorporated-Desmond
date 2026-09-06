/** Progressive future-glass control discovery and pointer physics. */
(() => {
  "use strict";

  const SELECTOR = [
    "button", ".btn", ".cg-btn", ".cta", "[role='button']",
    "input[type='submit']", "input[type='button']", "input[type='reset']",
    "a.button", "a.btn", "a.cta"
  ].join(",");
  const PRIMARY_HINT = /(^|[-_])(primary|purchase|checkout|buy|order|subscribe|deploy|submit|cta)([-_]|$)/i;
  const DANGER_HINT = /(^|[-_])(danger|delete|remove|revoke|destructive)([-_]|$)/i;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = matchMedia("(hover: hover) and (pointer: fine)");
  const observed = new WeakSet();
  const states = new WeakMap();

  function hasOwnedPseudo(control, pseudo) {
    const content = getComputedStyle(control, pseudo).content;
    return content && content !== "none" && content !== "normal" && content !== '""';
  }

  function isPrimary(control) {
    const identity = `${control.className || ""} ${control.id || ""} ${control.getAttribute("name") || ""}`;
    return PRIMARY_HINT.test(identity);
  }

  function render(control) {
    const state = states.get(control);
    if (!state || !control.classList.contains("is-future-active")) return;
    const ease = .16;
    state.x += (state.targetX - state.x) * ease;
    state.y += (state.targetY - state.y) * ease;
    control.style.setProperty("--glass-btn-magnet-x", `${state.x.toFixed(2)}px`);
    control.style.setProperty("--glass-btn-magnet-y", `${state.y.toFixed(2)}px`);
    if (Math.abs(state.targetX - state.x) + Math.abs(state.targetY - state.y) > .08) {
      state.frame = requestAnimationFrame(() => render(control));
    } else {
      state.frame = 0;
    }
  }

  function onPointerMove(event) {
    if (reduceMotion.matches || !finePointer.matches) return;
    const control = event.currentTarget;
    const rect = control.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
    const nx = x / rect.width;
    const ny = y / rect.height;
    const distance = Math.min(1, Math.hypot(nx - .5, ny - .5) * 1.42);
    control.style.setProperty("--pointer-x", `${(nx * 100).toFixed(1)}%`);
    control.style.setProperty("--pointer-y", `${(ny * 100).toFixed(1)}%`);
    control.style.setProperty("--pointer-distance", (1 - distance).toFixed(3));
    if (control.classList.contains("future-glass-primary")) {
      const state = states.get(control);
      const limit = Math.min(5, Math.max(2, rect.width / 70));
      state.targetX = (nx - .5) * limit * 2;
      state.targetY = (ny - .5) * limit * 1.35;
      if (!state.frame) state.frame = requestAnimationFrame(() => render(control));
    }
  }

  function resetPointer(event) {
    const control = event.currentTarget;
    const state = states.get(control);
    if (state) state.targetX = state.targetY = 0;
    control.style.setProperty("--pointer-x", "50%");
    control.style.setProperty("--pointer-y", "50%");
    control.style.setProperty("--pointer-distance", "0");
    if (!reduceMotion.matches && state && !state.frame) state.frame = requestAnimationFrame(() => render(control));
  }

  function activate(control) {
    if (control.classList.contains("is-future-active")) return;
    control.classList.add("is-future-active");
    if (!reduceMotion.matches && finePointer.matches) {
      control.addEventListener("pointermove", onPointerMove, { passive: true });
      control.addEventListener("pointerleave", resetPointer, { passive: true });
    }
  }

  const viewportObserver = "IntersectionObserver" in window
    ? new IntersectionObserver(entries => {
        for (const entry of entries) if (entry.isIntersecting) {
          activate(entry.target);
          viewportObserver.unobserve(entry.target);
        }
      }, { rootMargin: "180px" })
    : null;

  function enhance(control) {
    if (!(control instanceof HTMLElement) || observed.has(control) || control.closest("[data-no-future-glass]")) return;
    observed.add(control);
    const baseBackground = getComputedStyle(control).backgroundImage;
    if (baseBackground && baseBackground !== "none") control.style.setProperty("--future-base-background-image", baseBackground);
    control.classList.add("future-glass-control");
    if (!(control instanceof HTMLInputElement) && !hasOwnedPseudo(control, "::before") && !hasOwnedPseudo(control, "::after")) {
      control.classList.add("future-glass-layers");
    }
    if (isPrimary(control)) control.classList.add("future-glass-primary");
    if (DANGER_HINT.test(`${control.className} ${control.id}`)) control.classList.add("future-glass-danger");
    states.set(control, { x: 0, y: 0, targetX: 0, targetY: 0, frame: 0 });
    if (viewportObserver) viewportObserver.observe(control); else activate(control);
  }

  function discover(root = document) {
    if (root instanceof Element && root.matches(SELECTOR)) enhance(root);
    root.querySelectorAll?.(SELECTOR).forEach(enhance);
  }

  function init() {
    document.documentElement.classList.add("future-glass-ready");
    discover();
    new MutationObserver(records => {
      for (const record of records) for (const node of record.addedNodes) if (node.nodeType === Node.ELEMENT_NODE) discover(node);
    }).observe(document.body, { childList: true, subtree: true });
    document.addEventListener("click", event => {
      const busyControl = event.target.closest?.("[aria-busy='true']");
      if (busyControl?.matches(SELECTOR)) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
