(() => {
  const missions = window.CLEARGLASS_MISSIONS || [];
  const metrics = window.CLEARGLASS_MISSION_METRICS || [];
  const timeline = window.CLEARGLASS_MISSION_TIMELINE || [];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const grid = document.getElementById('mission-grid');
  const empty = document.getElementById('mission-empty');
  const results = document.getElementById('mission-results-count');
  const search = document.getElementById('mission-search');
  const classification = document.getElementById('classification-filter');
  const status = document.getElementById('status-filter');
  const year = document.getElementById('year-filter');
  const form = document.getElementById('mission-filters');
  const modal = document.getElementById('mission-modal');
  const modalContent = document.getElementById('mission-modal-content');
  const closeButton = modal.querySelector('.mc-modal__close');
  const prevButton = document.getElementById('mission-prev');
  const nextButton = document.getElementById('mission-next');
  let visibleMissions = [...missions];
  let activeIndex = 0;
  let lastFocused = null;

  const escapeHtml = value => String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const assetCandidates = image => {
    const base = image.replace(/\.[^.]+$/, '');
    return { avif: `${base}.avif`, webp: `${base}.webp`, fallback: image };
  };

  function fillSelect(select, values) {
    values.forEach(value => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
  }

  fillSelect(classification, [...new Set(missions.map(m => m.classification))].sort());
  fillSelect(status, [...new Set(missions.map(m => m.status))].sort());
  fillSelect(year, [...new Set(missions.map(m => m.year))].sort((a,b) => b-a));

  function pictureMarkup(mission, eager = false) {
    const paths = assetCandidates(mission.image);
    return `<picture>
      <source srcset="${escapeHtml(paths.avif)}" type="image/avif">
      <source srcset="${escapeHtml(paths.webp)}" type="image/webp">
      <img src="${escapeHtml(paths.fallback)}" alt="${escapeHtml(mission.alt)}" ${eager ? 'fetchpriority="high"' : 'loading="lazy"'} decoding="async" data-mission-image>
    </picture><div class="mc-card__fallback" hidden>MISSION IMAGE OFFLINE<br>Replace local asset in /assets/images/missions/</div>`;
  }

  function bindImageFallbacks(scope = document) {
    scope.querySelectorAll('[data-mission-image]').forEach(img => {
      img.addEventListener('error', () => {
        img.closest('picture')?.setAttribute('hidden', '');
        const fallback = img.closest('.mc-card__media, .mc-briefing__media')?.querySelector('.mc-card__fallback');
        if (fallback) fallback.hidden = false;
      }, { once: true });
    });
  }

  function cardMarkup(mission) {
    return `<article class="mc-card mc-reveal" data-id="${escapeHtml(mission.id)}">
      <div class="mc-card__media">${pictureMarkup(mission)}</div>
      <div class="mc-card__body">
        <div class="mc-card__meta"><span class="mc-label">${escapeHtml(mission.classification)}</span><span class="mc-state">${escapeHtml(mission.status)} · ${mission.year}</span></div>
        <h3>${escapeHtml(mission.title)}</h3><p>${escapeHtml(mission.objective)}</p>
        <div class="mc-tags">${mission.technologies.slice(0,4).map(t => `<span class="mc-tag">${escapeHtml(t)}</span>`).join('')}</div>
      </div>
      <button class="mc-card__button" type="button" aria-label="Open mission briefing for ${escapeHtml(mission.title)}"></button>
    </article>`;
  }

  function render() {
    const q = search.value.trim().toLowerCase();
    visibleMissions = missions.filter(m => {
      const haystack = `${m.title} ${m.technologies.join(' ')}`.toLowerCase();
      return (!q || haystack.includes(q)) &&
        (classification.value === 'all' || m.classification === classification.value) &&
        (status.value === 'all' || m.status === status.value) &&
        (year.value === 'all' || String(m.year) === year.value);
    });
    grid.innerHTML = visibleMissions.map(cardMarkup).join('');
    empty.hidden = visibleMissions.length !== 0;
    results.textContent = `${visibleMissions.length} mission${visibleMissions.length === 1 ? '' : 's'} displayed`;
    bindImageFallbacks(grid);
    bindCards();
    observeReveals();
  }

  function bindCards() {
    grid.querySelectorAll('.mc-card').forEach(card => {
      const button = card.querySelector('.mc-card__button');
      button.addEventListener('click', () => openMission(card.dataset.id, button));
      if (!reducedMotion) {
        card.addEventListener('pointermove', event => {
          const rect = card.getBoundingClientRect();
          const x = (event.clientX - rect.left) / rect.width - .5;
          const y = (event.clientY - rect.top) / rect.height - .5;
          card.style.transform = `perspective(900px) rotateX(${(-y*4).toFixed(2)}deg) rotateY(${(x*5).toFixed(2)}deg) translateY(-3px)`;
        });
        card.addEventListener('pointerleave', () => card.style.transform = '');
      }
    });
  }

  function modalMarkup(mission) {
    return `<article class="mc-briefing">
      <div class="mc-briefing__media">${pictureMarkup(mission, true)}</div>
      <div class="mc-briefing__body">
        <p class="mc-kicker">${escapeHtml(mission.classification)} // ${escapeHtml(mission.status)} // ${mission.year}</p>
        <h2 id="mission-modal-title">${escapeHtml(mission.title)}</h2>
        <div class="mc-briefing__grid"><div><h3>Objective</h3><p>${escapeHtml(mission.objective)}</p><h3>Technology Stack</h3><div class="mc-tags">${mission.technologies.map(t => `<span class="mc-tag">${escapeHtml(t)}</span>`).join('')}</div></div>
        <div><h3>Impact / Results</h3><ul>${mission.impact.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul></div></div>
      </div>
    </article>`;
  }

  function openMission(id, trigger) {
    activeIndex = Math.max(0, visibleMissions.findIndex(m => m.id === id));
    lastFocused = trigger || document.activeElement;
    updateModal();
    modal.showModal();
    closeButton.focus();
  }

  function updateModal() {
    const mission = visibleMissions[activeIndex];
    if (!mission) return;
    modalContent.innerHTML = modalMarkup(mission);
    bindImageFallbacks(modalContent);
    prevButton.disabled = visibleMissions.length < 2;
    nextButton.disabled = visibleMissions.length < 2;
  }

  function moveModal(direction) {
    if (visibleMissions.length < 2) return;
    activeIndex = (activeIndex + direction + visibleMissions.length) % visibleMissions.length;
    updateModal();
  }

  closeButton.addEventListener('click', () => modal.close());
  prevButton.addEventListener('click', () => moveModal(-1));
  nextButton.addEventListener('click', () => moveModal(1));
  modal.addEventListener('close', () => lastFocused?.focus());
  modal.addEventListener('click', event => { if (event.target === modal) modal.close(); });
  modal.addEventListener('keydown', event => {
    if (event.key === 'ArrowLeft') moveModal(-1);
    if (event.key === 'ArrowRight') moveModal(1);
    if (event.key === 'Tab') {
      const focusable = [...modal.querySelectorAll('button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])')];
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });

  [search, classification, status, year].forEach(el => el.addEventListener(el === search ? 'input' : 'change', render));
  form.addEventListener('reset', () => requestAnimationFrame(render));

  const metricsEl = document.getElementById('mission-metrics');
  metricsEl.innerHTML = metrics.map(m => `<div class="mc-metric"><strong>${escapeHtml(m.value)}</strong><span>${escapeHtml(m.label)}</span>${m.sample ? '<small>SAMPLE VALUE</small>' : ''}</div>`).join('');

  const timelineEl = document.getElementById('mission-timeline-list');
  timelineEl.innerHTML = timeline.map(item => `<article class="mc-timeline__item"><div class="mc-timeline__year">${escapeHtml(item.year)}</div><div class="mc-timeline__content"><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.text)}</p></div></article>`).join('');

  let observer;
  function observeReveals() {
    if (reducedMotion) {
      document.querySelectorAll('.mc-reveal,.mc-timeline__item').forEach(el => el.classList.add('is-visible'));
      return;
    }
    if (!observer) observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); } }), { threshold: .12 });
    document.querySelectorAll('.mc-reveal:not(.is-visible),.mc-timeline__item:not(.is-visible)').forEach(el => observer.observe(el));
  }

  const root = document.documentElement;
  const toggle = document.querySelector('.mc-theme-toggle');
  const toggleLabel = toggle.querySelector('.mc-theme-toggle__label');
  const savedTheme = localStorage.getItem('clearglass-mission-theme');
  if (savedTheme === 'light') root.dataset.missionTheme = 'light';
  function syncThemeControl() {
    const light = root.dataset.missionTheme === 'light';
    toggle.setAttribute('aria-pressed', String(light));
    toggle.setAttribute('aria-label', light ? 'Switch to glass tactical theme' : 'Switch to light technical theme');
    toggleLabel.textContent = light ? 'GLASS TACTICAL' : 'LIGHT TECHNICAL';
  }
  toggle.addEventListener('click', () => {
    root.dataset.missionTheme = root.dataset.missionTheme === 'light' ? 'glass' : 'light';
    localStorage.setItem('clearglass-mission-theme', root.dataset.missionTheme);
    syncThemeControl();
  });

  syncThemeControl();
  render();
  observeReveals();
})();
