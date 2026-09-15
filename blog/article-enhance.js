/* ClearGlass Insights — article enhancement layer.

   Runs on blog article pages only. Everything here is progressive enhancement:
   if this file fails to parse, fails to load, or the browser lacks a feature it
   reaches for, the article still renders and reads exactly as it did before.
   No code path in this file may hide, move, or remove authored content.

   It is deliberately loaded BEFORE insights.js so the mount points it creates
   (.endbar, #ixRelated) exist by the time insights.js looks for them. Both are
   deferred, so they execute in document order with the DOM fully parsed.

   Stdlib DOM only. No dependencies. Safe to execute twice. */
(function () {
  'use strict';

  var root = document.documentElement;
  var body = document.body;
  if (!body || root.hasAttribute('data-cga-on')) return;   // idempotent

  /* ---------- is this an article? ----------
     Trust the explicit marker first; fall back to structure so a page that was
     never tagged still gets the layer. The hub and the resume tool opt out. */
  var page = body.getAttribute('data-ix-page');
  if (page === 'hub') return;

  // Pick the element that actually holds the piece. Not every brief is one
  // <article>: some use several small <article class="fact"> cards, and taking
  // the first of those would anchor the whole layer to a single card in the
  // middle of the page. When the markup is ambiguous, prefer <main>.
  var article = pickRoot();
  if (!article) return;
  if (page !== 'article' && !document.querySelector('article')) return;
  if (!article.querySelector('h2, h3, p')) return;

  /* Pick the element that actually holds the piece. The blog's markup is not
     uniform: most briefs are one <article>, a few are several small
     <article class="fact"> cards, and at least one puts its <article> beside
     the headings rather than around them. Score the candidates on how much of
     the piece each really contains instead of trusting the first match. */
  function pickRoot() {
    var cands = [].slice.call(document.querySelectorAll('article'));
    var main = document.querySelector('main.wrap') || document.querySelector('main');
    if (main) cands.push(main);
    if (!cands.length) return null;

    var best = null, bestScore = -1;
    for (var i = 0; i < cands.length; i++) {
      var c = cands[i];
      // headings dominate: they are what the contents rail and anchors need
      var score = c.querySelectorAll('h2, h3').length * 1000 +
                  (c.textContent || '').length;
      if (score > bestScore) { bestScore = score; best = c; }
    }
    return best;
  }

  root.setAttribute('data-cga-on', '');
  root.classList.add('cga-on');

  var REDUCE = false;
  try { REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  /* insights.js owns the toast. Use it when it is present, stay quiet if not. */
  function say(msg) {
    var t = document.querySelector('.ix-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('on');
    clearTimeout(say._t);
    say._t = setTimeout(function () { t.classList.remove('on'); }, 1800);
  }

  function copyText(text, msg) {
    function ok() { say(msg || 'Copied'); }
    function legacy() {
      try {
        var ta = el('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.cssText = 'position:fixed;top:-1000px;opacity:0';
        body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        body.removeChild(ta);
        ok();
      } catch (e) { /* clipboard unavailable — nothing to do */ }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok, legacy);
    } else { legacy(); }
  }

  /* ================= 1. reading progress =================
     Measured against the article's own extent so the bar completes at the end
     of the piece, not at the end of the page furniture below it. Offsets are
     read once per resize/load; the scroll path only writes, which keeps it off
     the forced-layout path during scrolling. */
  (function progress() {
    // About 17 articles were authored with a progress bar of their own, each
    // wired to its own scroll handler. Two stacked bars is worse than one, so
    // defer to whatever the page already ships and only supply one where the
    // article has none.
    if (document.querySelector('.cga-progress, #progress, .progress, .future-progress, ' +
        '#readProgress, .read-progress, #reading-progress')) return;

    var bar = el('div', 'cga-progress');
    bar.setAttribute('aria-hidden', 'true');
    bar.appendChild(el('i'));
    var fill = bar.firstChild;
    body.appendChild(bar);

    var start = 0, span = 1, ticking = false, last = -1;

    function measure() {
      var r = article.getBoundingClientRect();
      start = r.top + (window.pageYOffset || 0);
      // finish when the article's last line clears the bottom of the viewport
      span = Math.max(1, article.offsetHeight - window.innerHeight * 0.6);
    }
    function paint() {
      ticking = false;
      var y = (window.pageYOffset || 0) - start;
      var pct = Math.max(0, Math.min(100, Math.round(y / span * 100)));
      if (pct !== last) { fill.style.width = pct + '%'; last = pct; }
    }
    function tick() {
      if (ticking) return;
      ticking = true;
      (window.requestAnimationFrame || setTimeout)(paint);
    }
    measure();
    addEventListener('scroll', tick, { passive: true });
    addEventListener('resize', function () { measure(); tick(); }, { passive: true });
    addEventListener('load', function () { measure(); tick(); });
    tick();
  })();

  /* ================= 2. measured meta strip =================
     Word count and read time are computed from the rendered article text.
     They are measurements, never authored numbers — if the text changes, these
     change with it. 225 wpm is the conventional prose reading rate; code and
     tables are excluded from the count because they are not read at prose speed. */
  (function meta() {
    var h1 = article.querySelector('h1') || document.querySelector('h1');
    if (!h1) return;

    var clone = article.cloneNode(true);
    ['pre', 'code', 'table', 'script', 'style', 'nav', '.toc', '.ix-toc',
     '.ix-toc-inline', 'figcaption'].forEach(function (sel) {
      var junk = clone.querySelectorAll(sel);
      for (var i = 0; i < junk.length; i++) {
        if (junk[i].parentNode) junk[i].parentNode.removeChild(junk[i]);
      }
    });
    var text = (clone.textContent || '').replace(/\s+/g, ' ').trim();
    var words = text ? text.split(' ').length : 0;
    if (words < 120) return;                       // too short to be worth a strip
    var mins = Math.max(1, Math.round(words / 225));
    var sections = article.querySelectorAll('h2').length;

    // Several briefs state their own reading time in the byline or deck
    // ("18-minute technical exploration", "12 min", "Estimated read: 7-9
    // minutes"). Printing a measured figure next to an authored one just puts
    // two different numbers on the page, so when the article already makes the
    // claim, leave it to the author and publish only what it does not say.
    var head = '';
    var scope = article.querySelector('header') || article;
    head = (scope.textContent || '').slice(0, 1400);
    var h1n = document.querySelector('h1');
    if (h1n && h1n.parentNode) head += ' ' + (h1n.parentNode.textContent || '').slice(0, 1400);
    var claimsTime = /\d+\s*[-–—]?\s*(?:to|–|—|-)?\s*\d*\s*min(?:ute)?s?\b/i.test(head);

    var strip = el('ul', 'cga-meta');
    strip.setAttribute('aria-label', 'Article measurements');
    var bits = [];
    if (!claimsTime) bits.push('<li><b>' + mins + '</b> min read</li>');
    bits.push('<li><b>' + words.toLocaleString() + '</b> words</li>');
    if (sections >= 2) bits.push('<li><b>' + sections + '</b> sections</li>');

    var when = document.querySelector('meta[property="article:published_time"]') ||
               document.querySelector('meta[name="date"]');
    if (when && when.content) {
      var d = new Date(when.content);
      if (!isNaN(d)) {
        bits.push('<li>' + d.toLocaleDateString('en-CA',
          { year: 'numeric', month: 'short', day: 'numeric' }) + '</li>');
      }
    }
    strip.innerHTML = bits.join('');

    // Place it directly under the title, inside whatever wrapper holds the h1.
    if (h1.nextSibling) h1.parentNode.insertBefore(strip, h1.nextSibling);
    else h1.parentNode.appendChild(strip);
  })();

  /* ================= 3. copy buttons on code blocks ================= */
  (function codeCopy() {
    var pres = article.querySelectorAll('pre');
    for (var i = 0; i < pres.length; i++) {
      (function (pre) {
        if (!(pre.textContent || '').trim()) return;
        if (pre.parentNode && pre.parentNode.classList.contains('cga-pre')) return;

        // Wrap rather than restyle the <pre>: each article styles its own code
        // blocks and this must not disturb them.
        var wrap = el('div', 'cga-pre');
        pre.parentNode.insertBefore(wrap, pre);
        wrap.appendChild(pre);

        var btn = el('button', 'cga-copy', 'Copy');
        btn.type = 'button';
        btn.setAttribute('aria-label', 'Copy this code block');
        btn.addEventListener('click', function () {
          copyText(pre.textContent, 'Code copied');
          btn.textContent = 'Copied';
          btn.classList.add('done');
          setTimeout(function () {
            btn.textContent = 'Copy';
            btn.classList.remove('done');
          }, 1600);
        });
        wrap.appendChild(btn);
      })(pres[i]);
    }
  })();

  /* ================= 4. mount points for the insights.js article layer =======
     insights.js attaches share / cite / save to .endbar and related briefs to
     #ixRelated, but only about a quarter of the articles were authored with
     those hooks. Create them where they are missing so every article gets the
     same controls. Articles that already have them are left untouched. */
  (function mounts() {
    var last = article.lastElementChild;

    if (!article.querySelector('.endbar') && !document.querySelector('.endbar')) {
      var bar = el('div', 'endbar cga-endbar');
      bar.appendChild(el('span', 'cga-endbar-label', 'Take this with you'));
      article.appendChild(bar);
    }
    if (!document.getElementById('ixRelated')) {
      var rel = el('div', 'ix-related');
      rel.id = 'ixRelated';
      article.appendChild(rel);
    }
    return last;
  })();

  /* ================= 5. keyboard shortcuts =================
     Deliberately narrow, and inert whenever the reader is typing so they can
     never interfere with the search palette or a form field. */
  (function keys() {
    addEventListener('keydown', function (e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var t = e.target || {};
      var tag = (t.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || t.isContentEditable) return;
      if (document.querySelector('.ix-palette.open')) return;

      if (e.key === 't') {
        scrollTo({ top: 0, behavior: REDUCE ? 'auto' : 'smooth' });
      } else if (e.key === 'c') {
        var inline = document.querySelector('.ix-toc-inline');
        if (inline) {
          inline.open = !inline.open;
          if (inline.open) inline.scrollIntoView({ block: 'nearest',
            behavior: REDUCE ? 'auto' : 'smooth' });
        }
      }
    });
  })();
})();
