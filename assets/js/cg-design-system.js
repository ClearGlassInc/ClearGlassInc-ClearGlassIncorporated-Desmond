/* ClearGlass design-system loader.
   Preserves the existing behavior layer in cg-design-system-core.js and
   adds the Business Productivity Suite to product navigation/catalog.
   Also harmonizes BLUEDESK with the ClearGlass global command bar so the
   product console reads as one premium system instead of stacked brands. */
(function () {
  'use strict';

  var PRODUCT_PAGE = '/business-productivity-suite.html';
  var PRODUCT_URL = 'https://turbo-fishstick-jg11zep.pages.github.io/';
  var BLUEDESK_PATHS = ['/bluedesk', '/bluedesk.html'];

  function normalizedPath() {
    return location.pathname.replace(/\/+$/, '').toLowerCase() || '/';
  }

  function isProductPage() {
    return normalizedPath() === PRODUCT_PAGE;
  }

  function isBlueDeskPage() {
    return BLUEDESK_PATHS.indexOf(normalizedPath()) !== -1;
  }

  function installBlueDeskShellStyles() {
    if (!isBlueDeskPage() || document.getElementById('cg-bluedesk-global-shell-css')) return;

    var style = document.createElement('style');
    style.id = 'cg-bluedesk-global-shell-css';
    style.textContent =
      'body.cg-bluedesk-global-shell{--cg-bd-global-h:72px}' +
      'body.cg-bluedesk-global-shell>.app>aside>.brand{display:none!important}' +
      'body.cg-bluedesk-global-shell>.app>aside{padding-top:12px!important}' +
      'body.cg-bluedesk-global-shell .cg-topbar{' +
        'z-index:5000!important;' +
        'background:linear-gradient(180deg,rgba(3,16,31,.96),rgba(3,12,25,.91))!important;' +
        'border-bottom:1px solid rgba(56,189,248,.28)!important;' +
        'box-shadow:0 18px 50px rgba(0,0,0,.28),0 0 44px rgba(56,189,248,.10)!important;' +
        'backdrop-filter:blur(24px) saturate(1.32)!important;' +
        '-webkit-backdrop-filter:blur(24px) saturate(1.32)!important' +
      '}' +
      'body.cg-bluedesk-global-shell .cg-topbar:after{' +
        'content:"";position:absolute;left:18px;right:18px;bottom:-1px;height:1px;pointer-events:none;' +
        'background:linear-gradient(90deg,transparent,rgba(56,189,248,.92),rgba(96,165,250,.72),rgba(168,85,247,.58),transparent);' +
        'box-shadow:0 0 18px rgba(56,189,248,.42)' +
      '}' +
      'body.cg-bluedesk-global-shell .cg-bd-context{' +
        'display:inline-flex;align-items:center;gap:8px;min-width:0;margin-left:2px;padding:7px 11px;border-radius:999px;' +
        'border:1px solid rgba(56,189,248,.24);background:linear-gradient(135deg,rgba(56,189,248,.10),rgba(59,130,246,.07),rgba(168,85,247,.07));' +
        'box-shadow:inset 0 1px 0 rgba(255,255,255,.07),0 0 22px rgba(56,189,248,.07);color:#eaf8ff;' +
        'font:600 10px/1.1 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap' +
      '}' +
      'body.cg-bluedesk-global-shell .cg-bd-context-dot{' +
        'width:7px;height:7px;border-radius:50%;background:#34d399;box-shadow:0 0 10px rgba(52,211,153,.9);flex:0 0 auto' +
      '}' +
      'body.cg-bluedesk-global-shell .cg-bd-context strong{font-weight:700;color:#fff}' +
      'body.cg-bluedesk-global-shell .cg-bd-context span:last-child{color:#8fb8d5;font-weight:500}' +
      'body.cg-bluedesk-global-shell>.app>main>.topbar{' +
        'top:var(--cg-bd-global-h)!important;z-index:1100!important;' +
        'background:linear-gradient(180deg,rgba(4,20,38,.91),rgba(2,10,24,.80))!important' +
      '}' +
      '@media(min-width:781px){' +
        'body.cg-bluedesk-global-shell>.app>aside{' +
          'top:var(--cg-bd-global-h)!important;height:calc(100vh - var(--cg-bd-global-h))!important;' +
          'border-top:1px solid rgba(56,189,248,.12)' +
        '}' +
      '}' +
      '@media(max-width:900px){' +
        'body.cg-bluedesk-global-shell .cg-bd-context{padding:6px 9px;max-width:180px;overflow:hidden}' +
        'body.cg-bluedesk-global-shell .cg-bd-context span:last-child{display:none}' +
      '}' +
      '@media(max-width:780px){' +
        'body.cg-bluedesk-global-shell>.app>aside{padding:10px 10px 12px!important;border-top:0!important}' +
        'body.cg-bluedesk-global-shell>.app>aside>.navgrp:first-of-type{padding-top:6px!important}' +
        'body.cg-bluedesk-global-shell>.app>main>.topbar{top:var(--cg-bd-global-h)!important}' +
      '}' +
      '@media(max-width:560px){' +
        'body.cg-bluedesk-global-shell .cg-bd-context{max-width:128px;font-size:9px;letter-spacing:.05em;padding:6px 8px}' +
        'body.cg-bluedesk-global-shell .cg-bd-context strong{overflow:hidden;text-overflow:ellipsis}' +
      '}';
    document.head.appendChild(style);
  }

  function harmonizeBlueDesk() {
    if (!isBlueDeskPage() || !document.body) return true;

    document.body.classList.add('cg-bluedesk-global-shell');
    installBlueDeskShellStyles();

    // The circled BLUEDESK/CISO masthead duplicates the global identity.
    // Remove only the rail-local brand block; all navigation and console
    // controls remain intact.
    var localBrand = document.querySelector('body > .app > aside > .brand, .app > aside > .brand');
    if (localBrand && localBrand.parentNode) localBrand.parentNode.removeChild(localBrand);

    var bar = document.querySelector('.cg-topbar');
    if (!bar) return false;

    var barInner = bar.querySelector('.cg-topbar-in');
    var globalBrand = bar.querySelector('.cg-tb-brand');
    if (barInner && globalBrand && !bar.querySelector('.cg-bd-context')) {
      var context = document.createElement('div');
      context.className = 'cg-bd-context';
      context.setAttribute('aria-label', 'Current product: BLUEDESK CISO Command Console');
      context.innerHTML = '<span class="cg-bd-context-dot" aria-hidden="true"></span><strong>BLUEDESK</strong><span>CISO COMMAND</span>';
      globalBrand.insertAdjacentElement('afterend', context);
    }

    function syncBarHeight() {
      var h = Math.max(56, Math.ceil(bar.getBoundingClientRect().height || 0));
      document.body.style.setProperty('--cg-bd-global-h', h + 'px');
    }
    syncBarHeight();
    window.addEventListener('resize', syncBarHeight, { passive: true });
    if ('ResizeObserver' in window && !bar.__cgBlueDeskObserved) {
      bar.__cgBlueDeskObserved = true;
      new ResizeObserver(syncBarHeight).observe(bar);
    }

    return true;
  }

  function addCatalogCard() {
    var pagePath = normalizedPath();
    if (pagePath !== '/products' && pagePath !== '/products.html') return true;
    if (document.getElementById('cg-business-productivity-suite-card')) return true;

    var container = document.querySelector('.cg-page .cg-container');
    var hero = container && container.querySelector('.cg-hero');
    if (!container || !hero) return false;

    var section = document.createElement('section');
    section.className = 'cg-product-section';
    section.id = 'business-productivity-suite';
    section.innerHTML =
      '<div class="cg-section-head">' +
        '<p class="cg-eyebrow">Business productivity systems</p>' +
        '<h2>Business productivity systems</h2>' +
        '<p>Canadian-first plan comparison and subscription-readiness experiences connected to the ClearGlass product ecosystem.</p>' +
      '</div>' +
      '<div class="cg-product-grid">' +
        '<article class="cg-product-card" id="cg-business-productivity-suite-card">' +
          '<span class="cg-card-icon" aria-hidden="true">▦</span>' +
          '<p class="cg-card-meta">Business productivity systems</p>' +
          '<h3>Business Productivity Suite</h3>' +
          '<p>CAD-oriented productivity plan comparison, seat configuration, and subscription lifecycle architecture.</p>' +
          '<div class="cg-card-actions">' +
            '<a class="btn btn-dark" href="' + PRODUCT_PAGE + '">View Product</a>' +
            '<a class="btn btn-glass" href="' + PRODUCT_URL + '" target="_blank" rel="noopener noreferrer">Launch Live App ↗</a>' +
          '</div>' +
        '</article>' +
      '</div>';

    hero.insertAdjacentElement('afterend', section);
    return true;
  }

  function addDesktopProductLink() {
    var menu = document.querySelector('.cg-tb-dropdown');
    if (!menu) return false;
    if (menu.querySelector('a[href="' + PRODUCT_PAGE + '"]')) return true;

    var link = document.createElement('a');
    link.href = PRODUCT_PAGE;
    link.setAttribute('role', 'menuitem');
    if (isProductPage()) {
      link.className = 'is-active';
      link.setAttribute('aria-current', 'page');
    }
    link.innerHTML =
      '<div class="cg-tb-dd-icon">▦</div>' +
      '<div class="cg-tb-dd-meta">' +
        '<span class="cg-tb-dd-label">Business Productivity Suite</span>' +
        '<span class="cg-tb-dd-sub">CAD PRODUCTIVITY PLANS</span>' +
      '</div>';
    menu.appendChild(link);
    return true;
  }

  function addMobileProductLink() {
    var menu = document.querySelector('.cg-tb-mobile');
    if (!menu) return false;
    if (menu.querySelector('a[href="' + PRODUCT_PAGE + '"]')) return true;

    var link = document.createElement('a');
    link.href = PRODUCT_PAGE;
    link.innerHTML = 'Business Productivity Suite <span class="arr">→</span>';
    var government = menu.querySelector('a[href="/government.html"]');
    if (government) menu.insertBefore(link, government.previousElementSibling || government);
    else menu.appendChild(link);
    return true;
  }

  function integrate() {
    var catalogDone = addCatalogCard();
    var desktopDone = addDesktopProductLink();
    var mobileDone = addMobileProductLink();
    var blueDeskDone = harmonizeBlueDesk();
    return catalogDone && desktopDone && mobileDone && blueDeskDone;
  }

  function retryIntegration() {
    var attempts = 0;
    function run() {
      attempts += 1;
      if (integrate() || attempts >= 40) return;
      setTimeout(run, 100);
    }
    run();
  }

  if (document.body && isBlueDeskPage()) {
    document.body.classList.add('cg-bluedesk-global-shell');
    installBlueDeskShellStyles();
    // Remove the duplicate local product masthead before the global core
    // measures and mounts its navigation shell.
    var earlyBrand = document.querySelector('body > .app > aside > .brand, .app > aside > .brand');
    if (earlyBrand && earlyBrand.parentNode) earlyBrand.parentNode.removeChild(earlyBrand);
  }

  var core = document.createElement('script');
  core.src = '/assets/js/cg-design-system-core.js';
  core.async = false;
  core.onload = retryIntegration;
  core.onerror = retryIntegration;
  document.head.appendChild(core);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', retryIntegration, { once: true });
  } else {
    retryIntegration();
  }
})();
