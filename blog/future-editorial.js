/* Adaptive editorial briefing. All ranking is local, deterministic, and derived
   from the public post index; static links remain the crawlable source of truth. */
(function () {
  'use strict';
  var root = document.documentElement;
  var body = document.body;
  if (!body || body.dataset.ixPage !== 'hub') return;

  var LENS_KEY = 'ix-editorial-lens';
  var CONTRAST_KEY = 'ix-high-contrast';
  var progress = document.getElementById('futureProgress');
  var recommendationGrid = document.getElementById('futureRecommendations');
  var status = document.getElementById('futureProfileStatus');
  var lensButtons = [].slice.call(document.querySelectorAll('[data-lens]'));
  var lens = readPreference(LENS_KEY) || '';

  function readPreference(key) {
    try { return localStorage.getItem(key) || ''; } catch (error) { return ''; }
  }
  function writePreference(key, value) {
    try { localStorage.setItem(key, value); } catch (error) { /* static fallback remains usable */ }
  }
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  }
  function updateProgress() {
    if (!progress) return;
    var maximum = root.scrollHeight - root.clientHeight;
    var ratio = maximum > 0 ? Math.min(1, Math.max(0, scrollY / maximum)) : 0;
    progress.style.transform = 'scaleX(' + ratio.toFixed(4) + ')';
  }
  addEventListener('scroll', updateProgress, { passive: true });
  addEventListener('resize', updateProgress, { passive: true });
  updateProgress();

  function configureToggle(id, storageKey, target, className) {
    var button = document.getElementById(id);
    if (!button) return;
    var enabled = readPreference(storageKey) === 'true';
    target.classList.toggle(className, enabled);
    button.setAttribute('aria-pressed', String(enabled));
    button.addEventListener('click', function () {
      enabled = !enabled;
      target.classList.toggle(className, enabled);
      button.setAttribute('aria-pressed', String(enabled));
      writePreference(storageKey, String(enabled));
    });
  }
  configureToggle('futureTheme', CONTRAST_KEY, root, 'future-contrast');
  configureToggle('futureFocus', 'ix-focus-mode', body, 'future-focus');

  function paintLens() {
    lensButtons.forEach(function (button) {
      button.setAttribute('aria-pressed', String(button.dataset.lens === lens));
    });
    if (status) status.textContent = lens ? 'Lens active · ' + lens.replace('-', ' ') + ' · stored locally' : 'No lens selected · showing desk-ranked intelligence';
  }
  lensButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      lens = lens === button.dataset.lens ? '' : button.dataset.lens;
      writePreference(LENS_KEY, lens);
      paintLens();
      loadRecommendations();
    });
  });
  paintLens();

  function rank(post) {
    var topicMatch = lens && (post.topics || []).indexOf(lens) !== -1 ? 60 : 0;
    var published = post.status === 'published' ? 20 : 0;
    var desk = post.deskRank ? Math.max(0, 20 - Math.min(post.deskRank, 20)) : 0;
    return topicMatch + published + desk;
  }
  function complexity(post) {
    var minutes = Number(post.readMinutes || post.readingMinutes) || 0;
    return minutes >= 20 ? 'Deep dive' : minutes >= 12 ? 'Technical' : 'Brief';
  }
  function render(posts) {
    var ranked = posts.filter(function (post) { return post.status === 'published' && post.url; })
      .map(function (post) { return { post: post, score: rank(post) }; })
      .sort(function (a, b) { return b.score - a.score || String(b.post.date).localeCompare(String(a.post.date)); })
      .slice(0, 3);
    if (!ranked.length) throw new Error('No published posts in index');
    recommendationGrid.innerHTML = ranked.map(function (item, index) {
      var post = item.post;
      var match = lens && (post.topics || []).indexOf(lens) !== -1 ? 'Lens match' : 'Desk pick';
      return '<a class="future-rec" href="' + escapeHtml(post.url) + '">' +
        '<div class="future-rec-top"><span>0' + (index + 1) + ' · ' + escapeHtml(post.category || 'Intelligence brief') + '</span><span class="future-rec-match">' + match + '</span></div>' +
        '<h3>' + escapeHtml(post.title) + '</h3><p>' + escapeHtml(post.description || '') + '</p>' +
        '<div class="future-rec-signals"><span>' + escapeHtml(complexity(post)) + '</span><span>' + escapeHtml(String(post.readMinutes || post.readingMinutes || '—')) + ' min</span><span>' + escapeHtml(post.date || post.published || 'Published') + '</span></div></a>';
    }).join('');
  }
  function showFallback() {
    recommendationGrid.innerHTML = '<p class="future-loading">The adaptive ranking is unavailable offline. Browse every article in Latest or open the <a href="posts.json">published post index</a>.</p>';
  }
  function loadRecommendations() {
    fetch('posts.json', { cache: 'no-cache' })
      .then(function (response) { if (!response.ok) throw new Error('Post index unavailable'); return response.json(); })
      .then(function (data) { render(data.posts || []); })
      .catch(showFallback);
  }
  loadRecommendations();
}());
