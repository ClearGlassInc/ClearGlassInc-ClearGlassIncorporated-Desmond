/* Additive hub cards for North America desk. Loaded by insights.js. Does not remove existing cards. */
(function () {
  if (!document.body || document.body.getAttribute('data-ix-page') !== 'hub') return;
  var feature = document.querySelector('.feature');
  var grid = document.getElementById('postGrid');
  if (!feature && !grid) return;
  var desk = [
    {href:'canada-us-cross-border-cybersecurity-evidence-controls.html',slug:'canada-us-cross-border-cybersecurity-evidence-controls',title:'The Canada US Control Problem Why North American Operations Fail at the Evidence Layer',tags:'canada united states pipeda bill c-8 circia cpcsc cmmc data residency evidence ledger',topics:'cyber systems governed-ai cross-border',quote:'Residency is not sovereignty.',cat:'North America Desk',mins:'14 min',h3:'The Canada–US Control Problem',desc:'Why North American operations fail at the evidence layer — PIPEDA transfers, Bill C-8, CIRCIA, CPCSC and CMMC on one proof problem.',cta:'Open the flagship brief →'},
    {href:'cpcsc-vs-cmmc-residency-split.html',slug:'cpcsc-vs-cmmc-residency-split',title:'CPCSC vs CMMC Control Reuse and the Data Residency Split',tags:'cpcsc cmmc defence data residency cloud act',topics:'cyber systems cross-border',quote:'Reuse the controls. Split the estate.',cat:'Defence Supply',mins:'8 min',h3:'CPCSC vs CMMC: the residency split',desc:'What Canadian defence suppliers can reuse from CMMC, and why specified information still has a Canada location problem.',cta:'Read the cluster brief →'},
    {href:'dual-clock-incident-runbook-ccspa-circia-pipeda.html',slug:'dual-clock-incident-runbook-ccspa-circia-pipeda',title:'Dual Clock Incident Runbook CCSPA CIRCIA PIPEDA',tags:'circia bill c-8 pipeda incident response dual clock',topics:'cyber systems governed-ai cross-border',quote:'One ledger. Two clocks.',cat:'Incident Readiness',mins:'7 min',h3:'Dual-clock incident runbook',desc:'CCSPA, CIRCIA and PIPEDA on a single timeline, with two tabletop drills and a shared field list.',cta:'Open the runbook →'}
  ];
  function paint(p) {
    var a = document.createElement('a');
    a.className = 'article-card tilt-card';
    a.href = p.href;
    a.setAttribute('data-title', p.title);
    a.setAttribute('data-tags', p.tags);
    a.setAttribute('data-slug', p.slug);
    a.setAttribute('data-topics', p.topics);
    a.innerHTML = '<div class="card-art"><div class="quote">' + p.quote + '</div></div><div class="card-body"><div class="meta"><span>New</span><span>' + p.cat + '</span><span>' + p.mins + '</span></div><h3>' + p.h3 + '</h3><p>' + p.desc + '</p><span class="read">' + p.cta + '</span></div>';
    return a;
  }
  desk.forEach(function (p) {
    if (document.querySelector('.article-card[data-slug="' + p.slug + '"]')) return;
    if (feature) feature.insertBefore(paint(p), feature.firstElementChild);
    if (grid) grid.insertBefore(paint(p), grid.firstElementChild);
  });
})();
