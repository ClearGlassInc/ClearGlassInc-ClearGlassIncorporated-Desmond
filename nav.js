/* ClearGlass · homepage-matched global navigation.
   Injects the same premium glass top bar, complete product catalog, mobile menu,
   and clear CTA language on every static page without removing page content. */
(function () {
  "use strict";
  if (window.__cgNavLoaded) return;
  window.__cgNavLoaded = true;

  var PRODUCTS = [
    ["Artemis IV Core", "artemis-iv.html", "Tactical intelligence core", "🧭"],
    ["Artemis VI", "artemis.html", "Ontario intelligence deployment", "🛰"],
    ["Artemis OS", "artemis-os.html", "Intelligence operating system", "◎"],
    ["Artemis 2040", "artemis-2040.html", "Long-horizon intelligence", "◌"],
    ["Artemis Self-Evolving", "artemis-self-evolving-platform.html", "Governed improvement loop", "↻"],
    ["AI Cyber Intelligence", "artemis-ai-cyber-intelligence-platform.html", "Cyber intelligence platform", "✦"],
    ["AVALON · Artemis + Percival", "artemis-percival.html", "Unified fusion core", "⬣"],
    ["PERCIVAL OS", "percival-os.html", "Governed command center", "◐"],
    ["SENTINEL", "sentinel.html", "Live geospatial command", "◉"],
    ["GUARDIAN", "guardian.html", "Intelligence command interface", "🌐"],
    ["BLUEDESK", "bluedesk.html", "CISO risk console", "🛡"],
    ["BLUEDESK Mobile", "bluedesk-mobile.html", "Phone-first risk console", "▣"],
    ["ClearGlass NEXUS", "clearglass-nexus.html", "Full-spectrum intelligence", "◆"],
    ["NEXUS v12", "ClearGlass-NEXUS-v12-FINAL.html", "Flagship platform build", "◇"],
    ["Intelligence Command Surface", "intelligence-command-surface.html", "Unified operational picture", "🗺"],
    ["Intelligence Interface", "intelligence-interface.html", "Analyst workspace", "🖥"],
    ["Flowsint", "flowsint.html", "OSINT investigation graph", "🕸"],
    ["Network Flow Intelligence", "clearglass.html", "Living network structure", "⌁"],
    ["Ontario OSINT Deck", "Ontario-osint.html", "Regional OSINT control", "⌖"],
    ["Agent Mesh", "agentmesh.html", "Multi-agent orchestration", "⌗"],
    ["AI Operator Workspace", "ai-operator.html", "Human-in-the-loop ops", "🜂"],
    ["CONDUIT", "conduit.html", "Self-hosted automation", "⟿"],
    ["PostLoop", "postloop.html", "Content engine", "⟲"],
    ["AutoMap", "automap.html", "Architecture orchestration", "⌘"],
    ["Command Console", "command-console.html", "Cyber operations hub", "▤"],
    ["Event Control Surface", "saas-platform.html", "Event-driven operations", "◆"],
    ["Systems Console", "systems.html", "PERCIVAL operations", "▦"],
    ["Control Surface", "control-surface.html", "Live command dashboard", "▧"],
    ["CG OS", "CG-os.html", "ClearGlass command HUD", "◫"],
    ["Command Center", "command-center.html", "Executive operations deck", "⌁"],
    ["Platform Command Center", "platform-command-center.html", "Live monorepo dashboard", "🗂"],
    ["Authority Network", "authority-network.html", "Connected knowledge graph", "🔗"],
    ["CLEARSIGHT", "clearsight.html", "Edge-AI camera vision", "🎥"],
    ["ZEPHYR Air Control", "air-control.html", "Air systems control", "🜁"],
    ["Air Systems Control", "air-systems-control.html", "Airspace control surface", "✈"],
    ["ClearPulse", "clearpulse.html", "Healthcare intelligence", "📡"],
    ["ClearPulse Architecture", "clearpulse-architecture.html", "Forensic-AI whitepaper", "✚"],
    ["AEGIS", "aegis.html", "Legal process shield", "⚖"],
    ["ClearCounsel", "corporate-legal-advisor.html", "Corporate legal AI", "§"],
    ["ClearBank Legal AI", "banking-law-advisor.html", "Banking law intelligence", "🏦"],
    ["ClearTax AI", "tax.html", "Tax intelligence", "🧾"],
    ["Government Solutions", "government.html", "Public-sector systems", "🏛"],
    ["Counter-UAS OS", "counter-uas-commercialization-os.html", "Counter-drone platform", "◎"],
    ["Speed Vision AI", "traffic-enforcement.html", "Traffic enforcement AI", "◈"],
    ["SATS Digital Twin", "sats-digital-twin.html", "Transit simulation", "▱"],
    ["SMB Suite", "smb.html", "Small-business systems", "▰"],
    ["SMB Cyber Trust Kit", "smb-cyber-trust-kit.html", "Cyber resilience kit", "🔐"],
    ["Revenue Engine", "revenue-engine.html", "AI growth system", "💹"],
    ["Opal-Koboi Assets", "products/opal-koboi/index.html", "Product asset library", "✧"],
    ["Artemis IV Core · Asset", "products/opal-koboi/artemis-iv-core.html", "Product sheet", "🧭"],
    ["Artemis VI · Asset", "products/opal-koboi/artemis-vi.html", "Product sheet", "🛰"],
    ["Guardian · Asset", "products/opal-koboi/guardian.html", "Product sheet", "🌐"],
    ["Revenue Engine · Asset", "products/opal-koboi/revenue-engine.html", "Product sheet", "💹"],
    ["SMB Suite · Asset", "products/opal-koboi/smb-suite.html", "Product sheet", "▰"],
    ["Ultra Glass", "ultra-glass.html", "Glass intelligence UI", "◫"],
    ["ClearGlass Ultra", "clearglass-ultra.html", "See-through command UI", "◩"],
    ["Aurora Glass", "futuristic.html", "Design study", "✺"],
    ["Button System", "button-system.html", "Glass UI components", "◍"],
    ["Button Lab", "button-lab.html", "Control components", "◌"],
    ["Hover Menu", "hover-menu.html", "Glass interaction study", "◔"],
    ["Web Design & Development", "web-design.html", "Growth infrastructure", "💻"],
    ["Store", "store.html", "Book an engagement", "🛒"],
    ["Side Store", "side-store.html", "Electronics and components", "🔌"],

    ["Advanced Systems Catalog", "advanced-features-tools-systems.html", "Governed systems index", "▨"],
    ["Artemis Blue Team", "artemis-blue-team.html", "Defensive automation", "🛡"],
    ["Cyber Defense Console", "cyber-defense-console.html", "Command center brief", "▤"],
    ["Environmental Cyber Risk", "environmental-cyber-risk.html", "Environmental threat model", "♧"],
    ["StegoForge", "stegoforge.html", "Media assurance terminal", "🖼"],
    ["ATT&CK Prompt Core", "attack-prompt-core.html", "Threat-informed prompt core", "🎯"],
    ["Intelligence Platform", "intelligence-platform.html", "Full-stack intel architecture", "✦"],
    ["Intelligence Services", "intelligence.html", "Advisory and OSINT", "◈"],
    ["Percival Build", "percival-build.html", "Build architecture", "◐"],
    ["Procurement Legal Tech", "procurement-legal-tech.html", "Procurement integrity AI", "⚖"],
    ["Pricing", "pricing.html", "Plans and engagements", "₵"]
  ];
  var TOP = [["Vision","index.html#vision"],["Services","index.html#services"],["Products","products.html"],["Government","index.html#government"],["Insights","blog/"],["Contact","index.html#contact"]];
  var COMPANY = [
    ["Authority Grid", "authority-network.html", "⌁"]
  ];
  var script = document.currentScript || Array.prototype.slice.call(document.scripts).filter(function(s){return /nav\.js(?:\?|$)/.test(s.src);}).pop();
  var base = script ? new URL('.', script.src).href : new URL('.', location.href).href;
  function href(path){ return /^https?:|^mailto:|^#/.test(path) ? path : new URL(path, base).href; }
  var here = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  var css = [
    ".cg-native-nav-hidden,.cg-native-header-hidden{display:none!important}.cg-global-nav-enabled{--cg-unified-nav-offset:clamp(82px,7vw,108px)}",
    ".cg-topnav{position:fixed;top:clamp(10px,1.25vw,18px);left:50%;transform:translateX(-50%);width:min(1480px,calc(100% - clamp(1rem,2.4vw,3rem)));z-index:2147483000;min-height:76px;display:flex;align-items:center;justify-content:space-between;gap:clamp(.75rem,1.5vw,1.75rem);padding:clamp(.5rem,.7vw,.7rem) clamp(.75rem,1.2vw,1.25rem);border-radius:999px;border:1px solid rgba(221,228,255,.78);background:linear-gradient(90deg,rgba(233,241,255,.26),rgba(20,31,61,.88) 13%,rgba(11,18,38,.94) 48%,rgba(41,32,82,.9) 78%,rgba(139,92,246,.32));backdrop-filter:blur(34px) saturate(1.85);-webkit-backdrop-filter:blur(34px) saturate(1.85);box-shadow:0 30px 88px rgba(18,24,52,.18),0 16px 44px rgba(87,54,170,.26),inset 0 1px 0 rgba(255,255,255,.72),inset 0 -1px 0 rgba(196,142,255,.72),0 0 0 1px rgba(133,163,255,.22);font-family:Urbanist,Inter,system-ui,sans-serif;isolation:isolate;overflow:visible;transition:transform .24s cubic-bezier(.4,0,.2,1),opacity .18s ease,visibility 0s linear;will-change:transform,opacity}",
    ".cg-topnav.cg-scroll-hidden{transform:translate(-50%,calc(-100% - 32px));opacity:0;visibility:hidden;pointer-events:none;transition-delay:0s,0s,.24s}",
    ".cg-topnav:before{content:\"\";position:absolute;inset:7px;border-radius:inherit;z-index:-1;pointer-events:none;background:linear-gradient(180deg,rgba(255,255,255,.18),transparent 34%),linear-gradient(90deg,rgba(133,183,255,.22),transparent 28%,rgba(176,91,255,.23) 72%,rgba(235,244,255,.14)),repeating-linear-gradient(90deg,transparent 0 154px,rgba(172,202,255,.2) 155px,transparent 157px);box-shadow:inset 0 0 42px rgba(112,87,255,.44),inset 0 0 0 1px rgba(255,255,255,.18)}",
    ".cg-topnav:after{content:\"\";position:absolute;left:48px;right:48px;top:8px;height:2px;border-radius:999px;background:linear-gradient(90deg,transparent,rgba(127,180,255,.9) 18%,rgba(255,255,255,.98) 42%,rgba(206,119,255,.98) 64%,transparent);box-shadow:0 0 16px rgba(190,109,255,.9),0 0 34px rgba(96,165,250,.44);pointer-events:none}",
    ".cg-topnav *{box-sizing:border-box}.cg-brand{position:relative;display:flex;align-items:center;gap:clamp(9px,1vw,14px);min-width:max-content;color:#f9fbff;text-decoration:none;text-shadow:0 0 22px rgba(255,255,255,.18)}.cg-brand:after{content:\"\";position:absolute;left:52px;right:-64px;bottom:-12px;height:1px;background:linear-gradient(90deg,rgba(137,184,255,.58),rgba(137,184,255,.22),transparent);box-shadow:0 0 18px rgba(132,175,255,.42)}",
    ".cg-mark{position:relative;width:54px;height:54px;border-radius:50%;display:grid;place-items:center;background:radial-gradient(circle at 34% 24%,rgba(255,255,255,.96),rgba(222,230,244,.86) 25%,rgba(132,140,158,.76) 50%,rgba(21,27,45,.9) 78%);border:1px solid rgba(247,250,255,.82);box-shadow:0 0 10px rgba(85,140,255,.55),0 0 22px rgba(128,76,255,.35),inset 0 4px 12px rgba(255,255,255,.72),inset 0 -10px 22px rgba(0,0,0,.42);overflow:visible;flex:0 0 auto;isolation:isolate}.cg-mark.logo-orb::before{content:\"\";position:absolute;inset:-4px;z-index:-1;border-radius:inherit;pointer-events:none;border:1px solid rgba(176,113,255,.75);box-shadow:0 0 12px rgba(82,145,255,.8),0 0 28px rgba(154,78,255,.65),0 0 48px rgba(154,78,255,.3);opacity:.48;transform:scale(.96);animation:clearGlassNeonPulse 2.8s ease-in-out infinite;will-change:transform,opacity}.cg-mark.logo-orb::after{content:\"\";position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:conic-gradient(from 220deg,transparent,rgba(255,255,255,.68),transparent 24%,rgba(192,132,252,.36),transparent 48%);mix-blend-mode:screen;z-index:1}.cg-mark img{position:relative;z-index:2;width:96%;height:96%;object-fit:contain;border-radius:50%;filter:none;transform:none}@keyframes clearGlassNeonPulse{0%,100%{opacity:.42;transform:scale(.96);filter:hue-rotate(0deg)}50%{opacity:.95;transform:scale(1.06);filter:hue-rotate(18deg)}}@media (prefers-reduced-motion:reduce){.cg-mark.logo-orb::before{animation:none;opacity:.6;transform:none}}",
    ".cg-name{font-family:'Cormorant Garamond',Georgia,serif;font-size:clamp(1.15rem,1.55vw,1.75rem);font-weight:650;letter-spacing:-.035em;line-height:1;white-space:nowrap}.cg-name em{font-family:'Cormorant Garamond',Georgia,serif;font-style:italic;font-weight:400;color:#cbb7ff;letter-spacing:.01em;margin-left:.32rem;text-shadow:0 0 18px rgba(190,160,255,.7)}",
    ".cg-links{display:flex;align-items:center;gap:clamp(.15rem,.45vw,.5rem);margin-left:auto}.cg-links a,.cg-dropbtn{position:relative;color:rgba(242,246,255,.93);text-decoration:none;font-size:clamp(.78rem,.78vw,.9rem);font-weight:650;padding:10px 9px 13px;border-radius:15px;border:0;background:transparent;cursor:pointer;text-shadow:0 2px 16px rgba(255,255,255,.12)}.cg-links a:after,.cg-dropbtn:after{content:\"\";position:absolute;left:50%;bottom:3px;width:28px;height:2px;border-radius:999px;transform:translateX(-50%) scaleX(.72);background:linear-gradient(90deg,transparent,#91b4ff,#ca78ff,transparent);box-shadow:0 0 14px rgba(190,103,255,.92);opacity:.72;transition:.2s}.cg-links a:hover,.cg-dropbtn:hover{color:#fff;background:rgba(255,255,255,.065)}.cg-links a:hover:after,.cg-dropbtn:hover:after{opacity:1;transform:translateX(-50%) scaleX(1.18)}",
    ".cg-cta{display:inline-flex!important;align-items:center;gap:8px;background:linear-gradient(180deg,rgba(11,14,28,.98),rgba(3,5,13,.99))!important;color:#fff!important;margin-left:clamp(.45rem,1vw,1.15rem);padding:11px 16px!important;border:1px solid rgba(205,146,255,.82)!important;border-radius:15px!important;box-shadow:0 0 0 1px rgba(123,92,255,.3),0 0 26px rgba(186,92,255,.78),0 16px 38px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.16)}.cg-cta svg{width:22px;height:22px;flex:0 0 auto;color:#e4c5ff;filter:drop-shadow(0 0 10px rgba(190,103,255,.72))}.cg-cta:after{display:none}",
    ".cg-drop{position:relative}.cg-menu{position:absolute;top:calc(100% + 10px);left:50%;transform:translateX(-50%) translateY(-6px);width:min(900px,92vw);max-height:min(72vh,720px);overflow:auto;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;padding:10px;background:rgba(16,24,50,.96);border:1px solid rgba(185,156,255,.36);border-radius:24px;box-shadow:0 22px 70px rgba(8,13,35,.42),0 0 34px rgba(176,103,255,.22);opacity:0;pointer-events:none;transition:.18s;backdrop-filter:blur(24px)}.cg-drop:hover .cg-menu,.cg-drop:focus-within .cg-menu{opacity:1;pointer-events:auto;transform:translateX(-50%) translateY(0)}.cg-prod{display:flex!important;gap:10px!important;align-items:center!important;padding:8px!important;border-radius:12px!important;color:#eef4ff!important;background:transparent!important}.cg-prod:hover{background:rgba(255,255,255,.08)!important}.cg-ic{width:26px;height:26px;border-radius:10px;background:rgba(255,255,255,.08);display:grid;place-items:center;flex:0 0 auto}.cg-prod b{display:block;font-size:13px;line-height:1.15}.cg-prod small{display:block;margin-top:3px;font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:#aeb9d5}",
    ".cg-toggle{display:none;border:1px solid rgba(196,139,255,.55);background:rgba(7,10,24,.7);color:#fff;border-radius:14px;padding:10px}.cg-mobile{position:fixed;top:104px;left:.75rem;right:.75rem;z-index:2147482999;display:none;grid-template-columns:1fr;gap:4px;max-height:calc(100vh - 120px);overflow:auto;padding:10px;background:rgba(16,24,50,.98);border:1px solid rgba(185,156,255,.36);border-radius:24px;box-shadow:0 12px 48px rgba(10,12,16,.28)}.cg-mobile.open{display:grid}.cg-mobile a{padding:12px 14px;border-radius:12px;text-decoration:none;color:#eef4ff;font-weight:650}.cg-mobile a:hover{background:rgba(255,255,255,.08)}.cg-label{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:#aeb9d5;padding:10px 14px 4px}",
    ".cg-topnav+main,.cg-topnav~main{scroll-margin-top:106px}.cg-topnav~:is(main,.page,.wrap){padding-top:max(104px,env(safe-area-inset-top))}.cg-unified-page :is(section,.section,.panel,.card){border-radius:clamp(16px,2vw,24px)}body{--cg-home-rhythm:clamp(80px,12vw,140px)}main :is(h1,h2){letter-spacing:-.025em}main :is(.eyebrow,.kicker,.label,.mono){letter-spacing:.12em;text-transform:uppercase}.btn,.button,a[class*=cta],button[class*=cta]{border-radius:999px}@media(max-width:1240px){.cg-links{display:none}.cg-toggle{display:block}.cg-topnav{min-height:68px}.cg-mark{width:48px;height:48px}.cg-menu{grid-template-columns:1fr}.cg-brand:after{display:none}}@media(max-width:760px){.cg-topnav{top:6px;width:calc(100% - .75rem);min-height:58px;padding:.35rem .65rem}.cg-name{font-size:18px}.cg-name em{display:none}.cg-mark{width:42px;height:42px}.cg-mobile{top:72px;max-height:calc(100vh - 84px)}}@media(prefers-reduced-motion:reduce){.cg-topnav{transition:none}.cg-topnav.cg-scroll-hidden{transition:none}}"
  ].join("");
  function isNativePrimaryNav(el){
    if (!el || el.id === 'cg-global-nav' || el.id === 'cg-mobile-nav') return false;
    if (el.closest('#cg-related,footer,.footer,.site-footer,.gov-footer,.cgr-box,.cg-topnav,.cg-mobile')) return false;
    var label = (el.getAttribute('aria-label') || '').toLowerCase();
    var role = (el.getAttribute('role') || '').toLowerCase();
    var cls = (' ' + (el.className || '') + ' ').toLowerCase();
    var id = (' ' + (el.id || '') + ' ').toLowerCase();
    if (/related|footer|breadcrumb|pagination/.test(label + cls + id)) return false;
    if (/primary|main|navigation/.test(label) || role === 'navigation') return true;
    return /( nav | navbar | topbar | header-nav | ag-nav | site-nav )/.test(cls) || /( navbar | nav )/.test(id);
  }
  function hideNativeNavigation(){
    Array.prototype.forEach.call(document.querySelectorAll('nav,[role="navigation"]'), function(el){
      if (!isNativePrimaryNav(el)) return;
      el.classList.add('cg-native-nav-hidden');
      var shell = el.closest('header,.st-header,.site-header,.topbar,.navbar');
      if (shell && shell !== document.body && !shell.closest('footer,.footer,.site-footer,.cgr-box')) {
        shell.classList.add('cg-native-header-hidden');
      }
    });
    document.body.classList.add('cg-global-nav-enabled');
  }
  function build(){
    if (document.getElementById('cg-global-nav')) return;
    var st=document.createElement('style'); st.textContent=css; document.head.appendChild(st);
    hideNativeNavigation();
    var nav=document.createElement('nav'); nav.id='cg-global-nav'; nav.className='cg-topnav'; nav.setAttribute('aria-label','Primary navigation');
    var menu=PRODUCTS.map(function(p){return '<a class="cg-prod" href="'+href(p[1])+'"><span class="cg-ic">'+p[3]+'</span><span><b>'+esc(p[0])+'</b><small>'+esc(p[2])+'</small></span></a>';}).join('');
    menu+=COMPANY.map(function(c){return '<a class="cg-prod" href="'+href(c[1])+'"><span class="cg-ic">'+c[2]+'</span><span><b>'+esc(c[0])+'</b><small>Company</small></span></a>';}).join('');
    nav.innerHTML='<a class="cg-brand" href="'+href('index.html')+'"><span class="cg-mark logo-orb" aria-hidden="true"><img src="'+href('assets/images/clearglass-logo-256.webp')+'" alt="" class="site-logo"></span><span class="cg-name">ClearGlassInc. <em>2040</em></span></a><div class="cg-links">'+TOP.map(function(t){return t[0]==='Products'?'<span class="cg-drop"><a class="cg-dropbtn" href="'+href('products.html')+'" aria-haspopup="true">Products⌄</a><span class="cg-menu"><a class="cg-prod" href="'+href('products.html')+'"><span class="cg-ic">▨</span><span><b>All Products</b><small>Unified catalog</small></span></a>'+menu+'</span></span>':'<a href="'+href(t[1])+'">'+t[0]+'</a>';}).join('')+'<a class="cg-cta" href="'+href('store.html')+'"><svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 3.5l10 3.8v7.2c0 6.2-4 11.6-10 14-6-2.4-10-7.8-10-14V7.3l10-3.8z"/><path d="M12.2 15.7l2.5 2.5 5.5-6"/></svg>Book a Security Engagement</a></div><button class="cg-toggle" aria-label="Open navigation" aria-expanded="false">☰</button>';
    var mob=document.createElement('div'); mob.className='cg-mobile'; mob.id='cg-mobile-nav'; mob.innerHTML='<div class="cg-label">Navigation</div>'+TOP.map(function(t){return '<a href="'+href(t[1])+'">'+t[0]+'</a>';}).join('')+'<a href="'+href('store.html')+'">Book a Security Engagement</a><div class="cg-label">Products</div>'+PRODUCTS.map(function(p){return '<a href="'+href(p[1])+'">'+esc(p[0])+'</a>';}).join('')+'<div class="cg-label">Company</div>'+COMPANY.map(function(c){return '<a href="'+href(c[1])+'">'+esc(c[0])+'</a>';}).join('');
    document.body.appendChild(nav); document.body.appendChild(mob);
    var btn=nav.querySelector('.cg-toggle'); btn.addEventListener('click',function(){var open=mob.classList.toggle('open');btn.setAttribute('aria-expanded',open?'true':'false');});
    var scrollTimer=0;
    var scrollFrame=0;
    function showNavigation(){
      window.clearTimeout(scrollTimer);
      nav.classList.remove('cg-scroll-hidden');
    }
    function hideNavigationDuringScroll(){
      window.clearTimeout(scrollTimer);
      scrollTimer=window.setTimeout(showNavigation,180);
      if(!scrollFrame){
        scrollFrame=window.requestAnimationFrame(function(){
          scrollFrame=0;
          nav.classList.add('cg-scroll-hidden');
          mob.classList.remove('open');
          btn.setAttribute('aria-expanded','false');
        });
      }
    }
    window.addEventListener('scroll',hideNavigationDuringScroll,{passive:true});
    window.addEventListener('scrollend',showNavigation,{passive:true});
    nav.addEventListener('focusin',showNavigation);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',build);else build();
})();
