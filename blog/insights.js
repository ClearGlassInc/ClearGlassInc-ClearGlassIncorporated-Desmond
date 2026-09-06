/* ClearGlass Insights — shared advanced blog layer.
   Progressive enhancement only: every feature degrades to the static page.
   Pages opt in via <body data-ix-page="hub|article" data-ix-slug="…" data-ix-theme="…">. */
(function () {
  'use strict';
  var body = document.body;
  var page = body.dataset.ixPage;
  if (!page) return;

  var slug = body.dataset.ixSlug || '';
  var REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var SAVED_KEY = 'ix-saved-posts';

  /* ---------- tiny utils ---------- */
  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function getSaved() {
    try { return JSON.parse(localStorage.getItem(SAVED_KEY)) || []; } catch (e) { return []; }
  }
  function setSaved(list) {
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(list)); } catch (e) { /* private mode */ }
  }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  var toast = el('div', 'ix-toast');
  toast.setAttribute('role', 'status');
  body.appendChild(toast);
  var toastTimer;
  function say(msg) {
    toast.textContent = msg;
    toast.classList.add('on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('on'); }, 1800);
  }

  function copyText(text, msg) {
    function done() { say(msg || 'Copied to clipboard'); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { legacy(); });
    } else { legacy(); }
    function legacy() {
      var ta = el('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { say('Copy failed'); }
      ta.remove();
    }
  }

  /* ---------- posts index (single source of truth: blog/posts.json) ---------- */
  var posts = [];
  var topicNames = {};
  var postsReady = fetch('posts.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (data && data.posts) { posts = data.posts; topicNames = data.topics || {}; }
    })
    .catch(function () { /* offline / file:// — static page still works */ });

  /* ---------- back to top (all pages) ---------- */
  var top = el('button', 'ix-top', '↑');
  top.type = 'button';
  top.setAttribute('aria-label', 'Back to top');
  top.addEventListener('click', function () {
    scrollTo({ top: 0, behavior: REDUCE ? 'auto' : 'smooth' });
  });
  body.appendChild(top);
  addEventListener('scroll', function () {
    top.classList.toggle('on', scrollY > 700);
  }, { passive: true });

  /* ---------- command palette (Ctrl/⌘ + K, all pages) ---------- */
  var palette, palInput, palList, palItems = [], palSel = 0;
  function buildPalette() {
    if (palette) return;
    palette = el('div', 'ix-palette');
    palette.innerHTML =
      '<div class="ix-palette-box" role="dialog" aria-label="Search ClearGlass Insights">' +
      '<input class="ix-palette-input" type="search" placeholder="Search briefs, series, topics…" aria-label="Search">' +
      '<ul class="ix-palette-list"></ul>' +
      '<div class="ix-palette-hint"><span><span class="ix-kbd">↑↓</span> navigate</span>' +
      '<span><span class="ix-kbd">↵</span> open</span><span><span class="ix-kbd">esc</span> close</span></div></div>';
    body.appendChild(palette);
    palInput = palette.querySelector('.ix-palette-input');
    palList = palette.querySelector('.ix-palette-list');
    palette.addEventListener('click', function (e) { if (e.target === palette) closePalette(); });
    palInput.addEventListener('input', function () { renderPalette(palInput.value); });
    palInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); movePal(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); movePal(-1); }
      else if (e.key === 'Enter') {
        var link = palList.querySelector('li.sel a');
        if (link) link.click();
      }
    });
  }
  function paletteEntries() {
    var items = posts.map(function (p) {
      return {
        kind: p.status === 'series' ? 'series' : (p.category || 'brief'),
        title: p.title,
        meta: p.readMinutes ? p.readMinutes + ' min' : 'coming',
        href: p.url ? p.url : (page === 'hub' ? '#latest' : 'index.html'),
        hay: (p.title + ' ' + (p.tags || []).join(' ') + ' ' + (p.series || '')).toLowerCase()
      };
    });
    items.push({ kind: 'navigate', title: 'All insights — the hub', meta: '', href: page === 'hub' ? '#latest' : 'index.html', hay: 'hub index all insights home' });
    items.push({ kind: 'navigate', title: 'Join the intelligence brief', meta: '', href: (page === 'hub' ? '' : 'index.html') + '#newsletter', hay: 'newsletter subscribe email brief' });
    items.push({ kind: 'navigate', title: 'RSS feed', meta: 'xml', href: 'feed.xml', hay: 'rss feed xml subscribe' });
    return items;
  }
  function renderPalette(q) {
    q = (q || '').toLowerCase().trim();
    palItems = paletteEntries().filter(function (it) { return !q || it.hay.indexOf(q) !== -1 || it.title.toLowerCase().indexOf(q) !== -1; }).slice(0, 8);
    palSel = 0;
    if (!palItems.length) {
      palList.innerHTML = '<li class="ix-palette-empty">No matches on the desk.</li>';
      return;
    }
    palList.innerHTML = palItems.map(function (it, i) {
      return '<li' + (i === palSel ? ' class="sel"' : '') + '><a href="' + esc(it.href) + '">' +
        '<span class="k">' + esc(it.kind) + '</span><span class="t">' + esc(it.title) + '</span>' +
        (it.meta ? '<span class="m">' + esc(it.meta) + '</span>' : '') + '</a></li>';
    }).join('');
  }
  function movePal(d) {
    var lis = palList.querySelectorAll('li');
    if (!lis.length || lis[0].classList.contains('ix-palette-empty')) return;
    lis[palSel].classList.remove('sel');
    palSel = (palSel + d + lis.length) % lis.length;
    lis[palSel].classList.add('sel');
    lis[palSel].scrollIntoView({ block: 'nearest' });
  }
  function openPalette() {
    buildPalette();
    palette.classList.add('open');
    palInput.value = '';
    postsReady.then(function () { renderPalette(''); });
    renderPalette('');
    palInput.focus();
  }
  function closePalette() { if (palette) palette.classList.remove('open'); }

  document.addEventListener('keydown', function (e) {
    var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || '')) && !(palette && palette.contains(e.target));
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      palette && palette.classList.contains('open') ? closePalette() : openPalette();
    } else if (e.key === 'Escape') {
      closePalette();
    } else if (e.key === '/' && page === 'hub' && !typing) {
      var s = document.getElementById('smartSearch');
      if (s) { e.preventDefault(); s.focus(); }
    }
  });

  /* ================================================================
     HUB — working topic filters, saved reading list, desk-rank badges
     ================================================================ */
  function initHub() {
    var cards = [].slice.call(document.querySelectorAll('.article-card[data-title]'));
    var archiveCards = [].slice.call(document.querySelectorAll('#postGrid .article-card[data-title]'));
    var search = document.getElementById('smartSearch');
    var chips = [].slice.call(document.querySelectorAll('#topics .chip[data-topic]'));
    var activeTopic = 'all';
    var pageSize = 6;
    var visiblePages = Math.max(1, parseInt(new URLSearchParams(location.search).get('page'), 10) || 1);
    var pageStatus = document.getElementById('postPageStatus');
    var loadMore = document.getElementById('loadMorePosts');
    var pageLinks = [].slice.call(document.querySelectorAll('[data-page]'));

    function updateArchivePage(push) {
      var matching = archiveCards.filter(function (card) { return card.dataset.filterMatch !== 'false'; });
      var shown = Math.min(matching.length, visiblePages * pageSize);
      matching.forEach(function (card, index) { card.hidden = index >= shown; });
      if (pageStatus) pageStatus.textContent = matching.length ? 'Showing ' + shown + ' of ' + matching.length + ' matching briefs · page ' + visiblePages : 'No briefs match this view.';
      if (loadMore) { loadMore.hidden = shown >= matching.length; loadMore.disabled = shown >= matching.length; }
      pageLinks.forEach(function (link) { link.setAttribute('aria-current', Number(link.dataset.page) === visiblePages ? 'page' : 'false'); });
      if (push && history.pushState) {
        var params = new URLSearchParams(location.search);
        if (visiblePages > 1) params.set('page', String(visiblePages)); else params.delete('page');
        var query = params.toString();
        history.pushState({ page: visiblePages }, '', location.pathname + (query ? '?' + query : '') + location.hash);
      }
    }

    function apply() {
      var q = (search && search.value || '').toLowerCase().trim();
      var saved = getSaved();
      var visible = 0;
      cards.forEach(function (card) {
        var hay = ((card.dataset.title || '') + ' ' + (card.dataset.tags || '')).toLowerCase();
        var topics = (card.dataset.topics || '').split(/\s+/);
        var okQ = !q || hay.indexOf(q) !== -1;
        var okT = activeTopic === 'all' ||
          (activeTopic === 'saved' ? saved.indexOf(card.dataset.slug) !== -1 : topics.indexOf(activeTopic) !== -1);
        var show = okQ && okT;
        card.dataset.filterMatch = String(show);
        card.style.display = show ? 'flex' : 'none';
        if (show) visible++;
      });
      updateArchivePage(false);
      if (activeTopic === 'saved' && !visible && !q) say('No saved briefs yet — save one from any article.');
    }

    function selectTopic(topic, push) {
      activeTopic = topic;
      if (push) visiblePages = 1;
      chips.forEach(function (c) { c.classList.toggle('on', c.dataset.topic === topic); });
      apply();
      if (push && history.replaceState) {
        var url = topic === 'all' ? location.pathname : location.pathname + '?topic=' + encodeURIComponent(topic);
        history.replaceState(null, '', url + location.hash);
      }
    }

    chips.forEach(function (chip) {
      chip.addEventListener('click', function (e) {
        e.preventDefault();
        selectTopic(chip.dataset.topic === activeTopic && chip.dataset.topic !== 'all' ? 'all' : chip.dataset.topic, true);
      });
    });
    if (search) search.addEventListener('input', function () { visiblePages = 1; apply(); });

    if (loadMore) loadMore.addEventListener('click', function () { visiblePages++; updateArchivePage(true); });
    pageLinks.forEach(function (link) { link.addEventListener('click', function (event) {
      event.preventDefault(); visiblePages = Math.max(1, Number(link.dataset.page) || 1); updateArchivePage(true);
      document.getElementById('postGrid').scrollIntoView({ behavior: REDUCE ? 'auto' : 'smooth', block: 'start' });
    }); });
    addEventListener('popstate', function () { visiblePages = Math.max(1, parseInt(new URLSearchParams(location.search).get('page'), 10) || 1); updateArchivePage(false); });
    var sentinel = document.getElementById('postScrollSentinel');
    if (sentinel && 'IntersectionObserver' in window) new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && loadMore && !loadMore.hidden) { visiblePages++; updateArchivePage(true); }
    }, { rootMargin: '240px 0px' }).observe(sentinel);

    /* deep links: /blog/?topic=osint and /blog/?q=agents (SearchAction target) */
    var params = new URLSearchParams(location.search);
    var qp = params.get('q');
    if (qp && search) search.value = qp;
    selectTopic(params.get('topic') || 'all', false);
    apply();

    /* topic counts + desk-rank badges from the index */
    postsReady.then(function () {
      chips.forEach(function (chip) {
        var t = chip.dataset.topic;
        if (t === 'all' || t === 'saved') return;
        var n = posts.filter(function (p) { return (p.topics || []).indexOf(t) !== -1; }).length;
        if (n) chip.appendChild(el('span', 'ix-count', String(n)));
      });
      posts.forEach(function (p) {
        if (!p.deskRank) return;
        var meta = document.querySelector('.article-card[data-slug="' + p.slug + '"] .meta');
        if (meta) meta.insertBefore(el('span', 'ix-rank', 'Desk pick #' + p.deskRank), meta.firstChild);
      });
    });

    /* keyboard hint under the search box */
    if (search && search.parentElement) {
      var hint = el('div', 'ix-hub-hint');
      hint.innerHTML = 'Press <span class="ix-kbd">/</span> to search · <span class="ix-kbd">Ctrl</span>+<span class="ix-kbd">K</span> for the command palette · chips filter the desk';
      search.parentElement.insertAdjacentElement('afterend', hint);
    }
  }

  /* ================================================================
     ARTICLE — scrollspy TOC, heading anchors, share/save, related
     ================================================================ */
  function slugify(s) {
    return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'section';
  }

  function initArticle() {
    var article = document.querySelector('article');
    if (!article) return;
    var heads = [].slice.call(article.querySelectorAll('h2'));

    heads.forEach(function (h) {
      if (!h.id) h.id = slugify(h.textContent.replace(/^\s*\d+\s*/, ''));
    });

    /* heading anchors — citable sections */
    heads.forEach(function (h) {
      var a = el('button', 'ix-anchor', '#');
      a.type = 'button';
      a.title = 'Copy link to this section';
      a.addEventListener('click', function () {
        copyText(location.origin + location.pathname + '#' + h.id, 'Section link copied');
      });
      h.appendChild(a);
    });

    /* table of contents: fixed rail on wide screens, collapsible inline on the rest */
    if (heads.length >= 3) {
      var items = heads.map(function (h) {
        var label = h.textContent.replace(/#$/, '').trim();
        var num = h.querySelector('.num');
        if (num) label = label.replace(num.textContent, '').trim();
        return '<li><a href="#' + h.id + '">' + esc(label) + '</a></li>';
      }).join('');

      var rail = el('nav', 'ix-toc');
      rail.setAttribute('aria-label', 'On this page');
      rail.innerHTML = '<b>On this page</b><ol>' + items + '</ol><div class="ix-toc-pct">0% read</div>';
      body.appendChild(rail);

      if (!article.querySelector('.toc')) {
        var inline = el('details', 'ix-toc-inline');
        inline.innerHTML = '<summary>On this page</summary><ol>' + items + '</ol>';
        article.insertBefore(inline, article.firstElementChild);
      }

      var railLis = [].slice.call(rail.querySelectorAll('li'));
      var pctEl = rail.querySelector('.ix-toc-pct');
      function spy() {
        var mark = scrollY + innerHeight * 0.28;
        var idx = 0;
        heads.forEach(function (h, i) {
          if (h.offsetTop <= mark) idx = i;
        });
        railLis.forEach(function (li, i) { li.classList.toggle('on', i === idx); });
        var h = document.documentElement;
        var max = h.scrollHeight - h.clientHeight;
        pctEl.textContent = (max > 0 ? Math.min(100, Math.round(scrollY / max * 100)) : 0) + '% read';
      }
      addEventListener('scroll', spy, { passive: true });
      spy();
    }

    /* share + save row */
    var endbar = article.querySelector('.endbar');
    if (endbar) {
      var row = el('div', 'ix-share-row');
      var here = location.origin + location.pathname;

      var cp = el('button', 'ix-chip', 'Copy link');
      cp.type = 'button';
      cp.addEventListener('click', function () { copyText(here, 'Article link copied'); });
      row.appendChild(cp);

      if (navigator.share) {
        var sh = el('button', 'ix-chip', 'Share…');
        sh.type = 'button';
        sh.addEventListener('click', function () {
          navigator.share({ title: document.title, url: here }).catch(function () {});
        });
        row.appendChild(sh);
      }

      var cite = el('button', 'ix-chip', 'Cite');
      cite.type = 'button';
      cite.addEventListener('click', function () {
        var author = (document.querySelector('meta[name="author"]') || {}).content || 'ClearGlass Inc.';
        var when = (document.querySelector('meta[property="article:published_time"]') || {}).content || '';
        copyText(author + (when ? ' (' + when + ')' : '') + '. "' + document.title.split('—')[0].trim() + '." ClearGlass Insights. ' + here, 'Citation copied');
      });
      row.appendChild(cite);

      if (slug) {
        var sv = el('button', 'ix-chip', '');
        sv.type = 'button';
        function paintSave() {
          var on = getSaved().indexOf(slug) !== -1;
          sv.textContent = on ? '★ Saved' : '☆ Save for later';
          sv.classList.toggle('on', on);
        }
        sv.addEventListener('click', function () {
          var s = getSaved();
          var i = s.indexOf(slug);
          if (i === -1) { s.push(slug); say('Saved — find it under the Saved filter on the hub'); }
          else { s.splice(i, 1); say('Removed from your reading list'); }
          setSaved(s);
          paintSave();
        });
        paintSave();
        row.appendChild(sv);
      }
      endbar.appendChild(row);
    }

    /* smart related posts — ranked by topic + tag overlap from posts.json */
    var relatedBox = document.getElementById('ixRelated');
    if (relatedBox) {
      postsReady.then(function () {
        if (!posts.length) return; // keep static fallback content
        var me = null;
        posts.forEach(function (p) { if (p.slug === slug) me = p; });
        function overlap(a, b) {
          a = a || []; b = b || [];
          return a.filter(function (x) { return b.indexOf(x) !== -1; }).length;
        }
        var ranked = posts
          .filter(function (p) { return p.slug !== slug && p.url; })
          .map(function (p) {
            return { p: p, score: (me ? overlap(p.topics, me.topics) * 2 + overlap(p.tags, me.tags) : 0) };
          })
          .sort(function (a, b) {
            if (b.score !== a.score) return b.score - a.score;
            return (b.p.date || '') < (a.p.date || '') ? -1 : 1;
          })
          .slice(0, 2);
        if (!ranked.length) return;
        var cards = ranked.map(function (r) {
          var p = r.p;
          return '<a class="ix-related-card" href="' + esc(p.url) + '">' +
            '<span class="k">' + esc(p.category || 'Brief') + '</span>' +
            '<h4>' + esc(p.title) + '</h4><p>' + esc(p.description || '') + '</p>' +
            '<span class="m">' + (p.readMinutes ? p.readMinutes + ' min read · ' : '') + esc(p.series || '') + '</span></a>';
        });
        if (cards.length < 2) {
          cards.push('<a class="ix-related-card" href="index.html"><span class="k">The hub</span>' +
            '<h4>All ClearGlass Insights</h4><p>Governed AI, cybersecurity architecture, autonomy, OSINT workflows, and high-trust software systems.</p>' +
            '<span class="m">Browse every brief →</span></a>');
        }
        relatedBox.innerHTML = '<b>Related from the desk</b><div class="ix-related-grid">' + cards.join('') + '</div>';
      });
    }
  }

  if (page === 'hub') initHub();
  if (page === 'article') initArticle();
})();
