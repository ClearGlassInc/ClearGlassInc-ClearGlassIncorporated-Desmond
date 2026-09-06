/* ═══════════════════════════════════════════════════════════════════
   CLEARGLASS GLOBAL DESIGN SYSTEM — behavior layer
   Mounts the ambient FX defined in assets/css/cg-design-system.css:
   aurora background, floating depth orbs with parallax, scan-line
   sweep, cursor-reactive glow, and scroll-reveal motion.
   Idempotent; respects prefers-reduced-motion; opt out per page with
   <body data-cg-no-fx> or <html data-cg-no-fx>.
═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  if (window.__cgDesignSystem) return;
  window.__cgDesignSystem = true;

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) { /* ignore */ }

  function optedOut() {
    return document.documentElement.hasAttribute('data-cg-no-fx') ||
      (document.body && document.body.hasAttribute('data-cg-no-fx'));
  }

  function ensureFonts() {
    // The design system's typography (Cormorant Garamond / Urbanist /
    // IBM Plex Mono) — only add the stylesheet if the page doesn't
    // already load Urbanist.
    var links = document.querySelectorAll('link[href*="fonts.googleapis.com"]');
    for (var i = 0; i < links.length; i++) {
      if (/Urbanist/.test(links[i].href)) return;
    }
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400&family=Urbanist:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap';
    document.head.appendChild(l);
  }

  function el(tag, className) {
    var n = document.createElement(tag);
    n.className = className;
    n.setAttribute('aria-hidden', 'true');
    return n;
  }

  function mountAmbient() {
    var frag = document.createDocumentFragment();
    frag.appendChild(el('div', 'cg-fx-neon-grid'));
    frag.appendChild(el('div', 'cg-fx-aurora'));
    frag.appendChild(el('div', 'cg-fx-orb o1'));
    frag.appendChild(el('div', 'cg-fx-orb o2'));
    frag.appendChild(el('div', 'cg-fx-orb o3'));
    if (!reduceMotion) {
      frag.appendChild(el('div', 'cg-fx-scan'));
      frag.appendChild(el('div', 'cg-fx-neon-thread'));
    }
    document.body.appendChild(frag);
  }

  function mountCursorGlow() {
    if (reduceMotion) return;
    // Pages that already ship the homepage cursor glow keep their own.
    if (document.querySelector('.cursor-glow')) return;
    var glow = el('div', 'cg-fx-cursor');
    document.body.appendChild(glow);
    var x = -500, y = -500, raf = null;
    document.addEventListener('pointermove', function (e) {
      x = e.clientX; y = e.clientY;
      if (raf) return;
      raf = requestAnimationFrame(function () {
        glow.style.left = x + 'px';
        glow.style.top = y + 'px';
        raf = null;
      });
    }, { passive: true });
  }

  function bindParallax() {
    if (reduceMotion) return;
    var orbs = document.querySelectorAll('.cg-fx-orb');
    if (!orbs.length) return;
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        var s = window.scrollY || 0;
        for (var i = 0; i < orbs.length; i++) {
          orbs[i].style.setProperty('--cg-par', String(-(s * (0.03 + i * 0.025))));
        }
        ticking = false;
      });
    }, { passive: true });
  }

  function bindReveal() {
    if (reduceMotion || !('IntersectionObserver' in window)) return;
    try {
      var targets = document.querySelectorAll(
        'main > section, body > section, article, .card, .product-card, .tech-card, .connect-card, .value-card, .offer-card, .cg-glass-card'
      );
      if (!targets.length) return;
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            en.target.classList.add('cg-vis');
            io.unobserve(en.target);
          }
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -6% 0px' });
      for (var i = 0; i < targets.length && i < 80; i++) {
        var t = targets[i];
        var r = t.getBoundingClientRect();
        // Never hide content already in the first viewport.
        if (r.top < window.innerHeight * 0.9) continue;
        t.classList.add('cg-rv');
        io.observe(t);
      }
    } catch (e) { /* reveal is progressive enhancement only */ }
  }

  /* Side Store owns its primary header. Consolidate the store identity,
     section navigation, search/account controls, and cart into one responsive
     sticky surface. Remove any separately injected global title bar so the two
     systems can never overlap or hide content. */
  function mergeSideStoreHeader() {
    var pagePath = location.pathname.replace(/\/+$/, '').toLowerCase();
    if (pagePath !== '/side-store' && pagePath !== '/side-store.html') return;

    var header = document.querySelector('header#navbar.st-header, header.st-header#navbar');
    if (!header) return;

    document.documentElement.setAttribute('data-cg-no-topbar', '');
    header.classList.add('cg-store-header-merged');

    function removeDuplicateTopbar() {
      var duplicates = document.querySelectorAll('.cg-topbar, .cg-topbar-spacer');
      for (var i = 0; i < duplicates.length; i++) {
        if (duplicates[i] !== header && duplicates[i].parentNode) {
          duplicates[i].parentNode.removeChild(duplicates[i]);
        }
      }
    }

    removeDuplicateTopbar();

    if (!document.getElementById('cg-store-header-merge-css')) {
      var style = document.createElement('style');
      style.id = 'cg-store-header-merge-css';
      style.textContent =
        'body>.cg-topbar,body>.cg-topbar-spacer{display:none!important}' +
        '.cg-store-header-merged{top:0!important;z-index:1200!important}' +
        '.cg-store-header-merged .st-header-in{display:flex;align-items:center;flex-wrap:nowrap;min-height:64px}' +
        '@media(max-width:920px){' +
          'html{scroll-padding-top:112px}' +
          '.cg-store-header-merged .st-header-in{flex-wrap:wrap;gap:6px 10px;padding:8px 12px;min-height:auto}' +
          '.cg-store-header-merged .st-brand{flex:1 1 auto;min-width:0}' +
          '.cg-store-header-merged .st-actions{flex:0 0 auto;margin-left:auto}' +
          '.cg-store-header-merged .st-navlinks{display:grid!important;order:3;grid-template-columns:repeat(5,minmax(0,1fr));width:100%;margin:0;gap:4px}' +
          '.cg-store-header-merged .st-navlinks a{min-width:0;text-align:center;line-height:1.15;white-space:normal;padding:7px 4px;font-size:11px}' +
        '}' +
        '@media(max-width:560px){' +
          'html{scroll-padding-top:104px}' +
          '.cg-store-header-merged .st-header-in{padding:6px 8px;gap:5px 6px}' +
          '.cg-store-header-merged .st-brand{font-size:11.5px;gap:5px;max-width:calc(100% - 120px)}' +
          '.cg-store-header-merged .st-brand-mk{width:28px;height:28px;border-radius:8px}' +
          '.cg-store-header-merged .st-brand-mk svg{width:16px;height:16px}' +
          '.cg-store-header-merged .st-brand>span:last-child{overflow:hidden;text-overflow:ellipsis}' +
          '.cg-store-header-merged .st-actions{gap:3px}' +
          '.cg-store-header-merged .st-iconbtn,.cg-store-header-merged .st-cart{min-height:34px;padding:6px 7px;border-radius:9px}' +
          '.cg-store-header-merged .st-iconbtn svg,.cg-store-header-merged .st-cart svg{width:15px;height:15px}' +
          '.cg-store-header-merged .st-cartn{min-width:18px;height:18px;padding:0 4px;font-size:10px}' +
          '.cg-store-header-merged .st-navlinks{gap:2px}' +
          '.cg-store-header-merged .st-navlinks a{font-size:9.5px;padding:6px 2px}' +
        '}' +
        '@media(max-width:360px){' +
          '.cg-store-header-merged .st-brand{font-size:10.5px;max-width:calc(100% - 110px)}' +
          '.cg-store-header-merged .st-iconbtn,.cg-store-header-merged .st-cart{min-width:30px;padding:5px 6px}' +
          '.cg-store-header-merged .st-navlinks a{font-size:8.8px}' +
        '}';
      document.head.appendChild(style);
    }

    // A second navigation script may execute after this design-system module.
    // Keep the store header authoritative if that late script tries to stack a
    // duplicate title bar above it.
    if ('MutationObserver' in window && document.body) {
      var observer = new MutationObserver(removeDuplicateTopbar);
      observer.observe(document.body, { childList: true });
    }
  }

  /* ── Global top bar — the ClearGlassInc. 2040 identity and menu on pages
     that do not already provide primary navigation. Existing page navigation
     remains the single source of navigation for that page. The homepage keeps
     its original single nav.
     Opt out only with data-cg-no-topbar on <html> or <body>. Pages can dock
     their own controls into the bar with [data-cg-topbar-slot], and rebrand the
     left side with data-cg-topbar-title / data-cg-topbar-sub on <body>. ── */
  function mountTopbar() {
    if (document.querySelector('.cg-topbar')) return;
    // Never stack the global bar above a page's own primary navigation. Keep
    // the selector semantic so table-of-contents and footer navs do not prevent
    // a page without a primary menu from receiving the global bar.
    if (document.querySelector(
      'nav[aria-label*="primary" i], nav[aria-label*="main" i], ' +
      'header nav, body > nav.nav, body > header.site-header'
    )) return;
    // nav.js supplies the single global top bar site-wide. When a page also
    // loads nav.js, defer to it so only one navigation bar renders instead of
    // two stacked bars. Checked via the script tag (present in the DOM
    // regardless of execution order) so this is order- and timing-independent.
    if (Array.prototype.some.call(document.scripts, function (s) {
        return /(^|\/)nav\.js(\?|$)/.test(s.src);
    })) return;
    if (document.documentElement.hasAttribute('data-cg-no-topbar') ||
        (document.body && document.body.hasAttribute('data-cg-no-topbar'))) return;
    var pagePath = location.pathname.replace(/\/+$/, '').toLowerCase();
    if (pagePath === '' || pagePath === '/index.html') return;

    var PRODUCTS = [
      ['Artemis IV Core', '/artemis-iv.html', '◎', 'Tactical Intelligence'],
      ['Artemis OS', '/artemis-os.html', '◈', 'Governed Agent OS'],
      ['Artemis Self-Evolving Platform', '/artemis-self-evolving-platform.html', '✦', 'AI Improvement Loop'],
      ['Artemis AI Cyber Intelligence', '/artemis-ai-cyber-intelligence-platform.html', '⚡', 'Cyber Intelligence'],
      ['Guardian', '/guardian.html', '🌐', 'Financial Intelligence'],
      ['BLUEDESK', '/bluedesk.html', '🛡️', 'CISO Risk & Blue Team'],
      ['ClearGlass NEXUS v12', '/clearglass-nexus.html', '◇', 'Command Platform'],
      ['ClearPulse', '/clearpulse.html', '📡', 'Signal Intelligence'],
      ['Flowsint', '/flowsint.html', '🕸️', 'OSINT Investigation Graph'],
      ['Command Center', '/command-center.html', '⌁', 'Live Operations Console'],
      ['Conduit', '/conduit.html', '⟿', 'Workflow Automation'],
      ['Air Systems Control', '/air-systems-control.html', '◌', 'Glass Control Surface'],
      ['SATS Digital Twin', '/sats-digital-twin.html', '◍', 'Storm-Adaptive Simulation'],
      ['Counter-UAS OS', '/counter-uas-commercialization-os.html', '⦿', 'Commercialization System'],
      ['Procurement Legal Tech', '/procurement-legal-tech.html', '§', 'Public-Sector Legal Ops'],
      ['Traffic Enforcement', '/traffic-enforcement.html', '◆', 'Safety Intelligence'],
      ['SMB Suite', '/smb.html', '▣', 'Small Business Systems'],
      ['SMB Cyber Trust Kit', '/smb-cyber-trust-kit.html', '🔐', 'Plain-Language Security'],
      ['Web Design & Dev', '/web-design.html', '💻', 'Growth Infrastructure'],
      ['Side Store', '/side-store.html', '🔌', 'Electronics Catalog'],
      ['Revenue Engine', '/revenue-engine.html', '$', 'Commercial Automation'],
      ['StegoForge', '/stegoforge.html', '▧', 'Media Assurance'],
      ['PERCIVAL OS', '/percival-os.html', '♜', 'Mission-Ready Agent Governance'],
      ['SENTINEL', '/sentinel.html', '◬', 'Geospatial Intelligence']
    ];
    var LINKS = [
      ['Vision', '/index.html#vision'],
      ['Services', '/index.html#services'],
      ['PRODUCTS'],
      ['Government', '/government.html'],
      ['Insights', '/blog/'],
      ['Contact', '/index.html#contact']
    ];

    var path = location.pathname.toLowerCase();
    function isHere(href) {
      var p = href.split('#')[0].toLowerCase();
      if (!p || p === '/index.html') return false;
      return path === p || (p.slice(-1) === '/' && path.indexOf(p) === 0);
    }
    function esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    var body = document.body;
    var title = body.getAttribute('data-cg-topbar-title');
    var sub = body.getAttribute('data-cg-topbar-sub') || 'Clarity is Power';
    var nameHtml = title ? esc(title) : 'ClearGlassInc. <em>2040</em>';

    var chev = '<svg class="cg-tb-chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>';
    var productActive = false;
    var ddHtml = '';
    PRODUCTS.forEach(function (p) {
      if (!p) { ddHtml += '<div class="cg-tb-dd-sep" role="separator"></div>'; return; }
      var cur = isHere(p[1]);
      if (cur) productActive = true;
      ddHtml += '<a href="' + p[1] + '" role="menuitem"' + (cur ? ' class="is-active" aria-current="page"' : '') + '>' +
        '<div class="cg-tb-dd-icon">' + p[2] + '</div>' +
        '<div class="cg-tb-dd-meta"><span class="cg-tb-dd-label">' + esc(p[0]) + '</span>' +
        '<span class="cg-tb-dd-sub">' + esc(p[3]).toUpperCase() + '</span></div></a>';
    });

    var linksHtml = '';
    LINKS.forEach(function (l) {
      if (l[0] === 'PRODUCTS') {
        linksHtml += '<div class="cg-tb-dropwrap">' +
          '<button type="button" class="cg-tb-dropbtn' + (productActive ? ' is-active' : '') + '" aria-haspopup="true" aria-expanded="false">Products⌄' + chev + '</button>' +
          '<div class="cg-tb-dropdown" role="menu">' + ddHtml + '</div></div>';
      } else {
        linksHtml += '<a href="' + l[1] + '"' + (isHere(l[1]) ? ' class="is-active" aria-current="page"' : '') + '>' + l[0] + '</a>';
      }
    });

    var mobHtml = '<a href="/index.html#vision">Vision</a><a href="/index.html#services">Services</a>' +
      '<div class="cg-tb-mob-sep"></div><div class="cg-tb-mob-label">Products</div>';
    PRODUCTS.forEach(function (p) {
      if (!p) return;
      mobHtml += '<a href="' + p[1] + '">' + esc(p[0]) + ' <span class="arr">→</span></a>';
    });
    mobHtml += '<div class="cg-tb-mob-sep"></div>' +
      '<a href="/government.html">Government <span class="arr">→</span></a>' +
      '<a href="/blog/">Insights</a>' +
      '<a href="/index.html#contact">Contact</a>' +
      '<a class="cg-tb-mob-cta" href="/store.html">Book a Security Engagement →</a>';

    var bar = document.createElement('div');
    bar.className = 'cg-topbar';
    bar.innerHTML =
      '<div class="cg-topbar-in">' +
        '<a class="cg-tb-brand" href="/index.html">' +
          '<span class="cg-tb-mark"><img src="/assets/images/clearglass-logo.png" alt="ClearGlass logo"><i class="cg-tb-ring" aria-hidden="true"></i></span>' +
          '<span class="cg-tb-id"><span class="cg-tb-name">' + nameHtml + '</span>' +
          '<span class="cg-tb-sub">' + esc(sub) + '</span></span>' +
        '</a>' +
        '<nav class="cg-tb-links" aria-label="Primary navigation">' + linksHtml + '</nav>' +
        '<div class="cg-tb-actions">' +
          '<a class="cg-tb-cta" href="/store.html"><svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 3.5l10 3.8v7.2c0 6.2-4 11.6-10 14-6-2.4-10-7.8-10-14V7.3l10-3.8z"/><path d="M12.2 15.7l2.5 2.5 5.5-6"/></svg>Book a Security Engagement</a>' +
          '<button type="button" class="cg-tb-toggle" aria-label="Open menu" aria-expanded="false">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12h16M4 6h16M4 18h16"/></svg>' +
          '</button>' +
        '</div>' +
      '</div>' +
      '<div class="cg-tb-mobile" role="dialog" aria-label="Navigation menu">' + mobHtml + '</div>';

    var spacer = document.createElement('div');
    spacer.className = 'cg-topbar-spacer';
    spacer.setAttribute('aria-hidden', 'true');
    body.insertBefore(spacer, body.firstChild);
    body.insertBefore(bar, spacer);

    // Adopt page-provided controls (e.g. the store's cart button) into
    // the action cluster, ahead of the CTA.
    var cta = bar.querySelector('.cg-tb-cta');
    var slots = document.querySelectorAll('[data-cg-topbar-slot]');
    for (var i = 0; i < slots.length; i++) {
      if (!bar.contains(slots[i])) cta.parentNode.insertBefore(slots[i], cta);
    }

    // Nudge compact fixed widgets below the global bar without deleting,
    // restyling, or replacing page content.
    function nudgeFixedWidgets() {
      var barH = bar.offsetHeight || 64;
      var cands = document.querySelectorAll('body > *, body > * > *');
      for (var j = 0; j < cands.length && j < 600; j++) {
        var item = cands[j];
        if (item === bar || bar.contains(item) || item.id === 'cg-nav') continue;
        if (item.hasAttribute('data-cg-tb-nudged')) continue;
        var cs = getComputedStyle(item);
        if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
        var r = item.getBoundingClientRect();
        if (r.height < 18 || r.height > 170 || r.width < 1) continue;
        if (r.top >= barH || r.bottom <= 0) continue;
        item.setAttribute('data-cg-tb-nudged', '1');
        item.style.top = (r.top + barH) + 'px';
      }
    }
    nudgeFixedWidgets();
    window.addEventListener('load', nudgeFixedWidgets);

    // Mobile menu + touch dropdown toggles.
    var toggle = bar.querySelector('.cg-tb-toggle');
    var mobile = bar.querySelector('.cg-tb-mobile');
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = mobile.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    var dropwrap = bar.querySelector('.cg-tb-dropwrap');
    var dropbtn = bar.querySelector('.cg-tb-dropbtn');
    dropbtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = dropwrap.classList.toggle('open');
      dropbtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    document.addEventListener('click', function (e) {
      if (!bar.contains(e.target)) {
        mobile.classList.remove('open');
        dropwrap.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        dropbtn.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        mobile.classList.remove('open');
        dropwrap.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        dropbtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Condense on scroll.
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        bar.classList.toggle('scrolled', (window.scrollY || 0) > 12);
        ticking = false;
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  function init() {
    if (optedOut()) return;
    if (document.body) document.body.classList.add('cg-neon-ready');
    ensureFonts();
    mergeSideStoreHeader();
    mountTopbar();
    mountAmbient();
    mountCursorGlow();
    bindParallax();
    bindReveal();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();