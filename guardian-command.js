(() => {
  'use strict';
  const root = document.querySelector('.gce');
  if (!root) return;

  const domainContent = {
    command: [['SYSTEM INTEGRITY', 'Read-only command layer ready', 'The browser shell is healthy; external platform status is unavailable.', 96], ['DECISION QUEUE', 'One demo candidate held', 'Human authorization is required before any consequential change.', 20], ['SOURCE HEALTH', 'No live sources connected', 'Four deterministic adapters demonstrate normalization without claiming live telemetry.', 0]],
    defense: [['DEFENSE MATRIX', 'No live findings', 'Asset, identity, service, and finding relationships require an authorized connector.', 0], ['CONTROL COVERAGE', 'Demonstration policy loaded', 'A deterministic policy example illustrates evidence-first risk scoring.', 72], ['EXPOSURE', 'Unavailable', 'GUARDIAN will not manufacture an incident or geographic attack layer.', 0]],
    agents: [['AGENT FLEET', 'No agent runtime connected', 'Agent state and permissions remain unavailable until a verified runtime registers.', 0], ['APPROVAL GATE', 'One simulated proposal', 'The proposal can be inspected but not approved or executed from this static page.', 20], ['SELF-IMPROVEMENT', 'Proposal only', 'Feedback may propose versioned changes; it cannot alter goals, privileges, or policy.', 34]],
    automation: [['WORKFLOW MATRIX', '3 of 4 demo paths valid', 'Validation → policy → approval → execution → verification is enforced by design.', 75], ['ROLLBACK', 'Designed, not connected', 'Production rollback requires an Apollo or deployment-system adapter.', 0], ['WRITE OPERATIONS', 'Disabled', 'This environment exposes no mutating tools or hidden execution paths.', 100]],
    infrastructure: [['SERVICE HEALTH', 'Unavailable', 'No API, container, cloud, CPU, memory, or network telemetry is connected.', 0], ['DATA PLANE', 'Local demo only', 'Deterministic objects render entirely in the browser.', 100], ['CAPABILITY TIER', 'Tier 2', 'Responsive glass and lightweight SVG; reduced-motion preferences are honored.', 66]],
    intelligence: [['EXTERNAL INTELLIGENCE', 'Unavailable', 'No OSINT, news, market, geographic, or reputation feeds are connected.', 0], ['CORRELATION', 'Schema demonstrated', 'Signals remain separated by state, confidence, classification, and provenance.', 60], ['KNOWLEDGE GRAPH', 'Four demo entities', 'Authorized Signal → Fabric → Policy Gate → Audit Plane.', 40]],
    governance: [['GOVERNANCE VAULT', 'Policy model active', 'Consequential action requires explicit human authority and post-action verification.', 88], ['AUDITABILITY', 'Design illustrated', 'The static page does not claim an immutable production ledger.', 52], ['COALITION BOUNDARIES', 'Not configured', 'Need-to-know controls require server-side identity and policy enforcement.', 0]],
    commercial: [['REVENUE INTELLIGENCE', 'Unavailable', 'No revenue, pipeline, customer, campaign, or procurement source is connected.', 0], ['OPPORTUNITY RADAR', 'Awaiting verified inputs', 'Projected revenue will remain distinct from observed revenue.', 0], ['BUSINESS IMPACT', 'Trace model ready', 'Findings can map to assets, products, and impact after source authorization.', 18]],
    evidence: [['PROVENANCE CONTRACT', 'GuardianSignal active', 'Source mode, state, timestamps, confidence, classification, methodology, and warnings.', 100], ['TRANSFORMATION', 'Deterministic local render', 'No network acquisition or undocumented transformation occurs.', 100], ['FRESHNESS', 'Live data unavailable', 'No stale value is silently represented as current.', 100]],
    forecast: [['PREDICTIVE ENGINE', 'No forecast produced', 'Observed history is insufficient; GUARDIAN abstains rather than inventing a projection.', 0], ['EVALUATION HARNESS', '12 simulated cases', 'The policy candidate is illustrative and does not represent a deployed model.', 32], ['LIMITATIONS', 'Explicit', 'No confidence interval can be calculated from live observations.', 0]]
  };

  const titles = {command:'Unified operational picture',defense:'Defense relationship matrix',agents:'Governed agent fleet',automation:'Authorization workflow matrix',infrastructure:'Infrastructure observability',intelligence:'Authorized intelligence correlation',governance:'Governance vault',commercial:'Commercial intelligence matrix',evidence:'Evidence and data lineage',forecast:'Predictive engine'};
  const signalEvidence = {
    integrity:['guardian-demo-shell','Local deterministic adapter','simulated','internal','96%','Browser initialization checks','No external health verification'],
    risk:['guardian-demo-policy','Derived demonstration rule','derived','internal','84%','Weighted demo controls; not an enterprise risk assessment','No authorized risk sources'],
    agents:['agent-registry','No source connected','unavailable','restricted','0%','No calculation performed','Agent runtime unavailable'],
    workflow:['guardian-demo-workflow','Local deterministic fixture','simulated','internal','92%','Three valid paths of four fixed examples','Not production workflow state'],
    freshness:['source-registry','No source connected','unavailable','internal','100%','Live-source count only','All external sources disconnected'],
    decisions:['guardian-demo-evals','Local deterministic fixture','simulated','internal','82%','Twelve fixed evaluation cases','Cannot authorize or execute'],
    decision:['guardian-demo-evals','Local deterministic fixture','simulated','internal','82%','Candidate improvement over twelve fixed cases','Human review and external deployment required']
  };

  const modules = root.querySelector('#gce-modules');
  const renderDomain = (domain) => {
    const entries = domainContent[domain] || domainContent.command;
    modules.replaceChildren(...entries.map(([label, title, body, value], index) => {
      const article = document.createElement('article');
      article.className = 'gce-module';
      article.innerHTML = `<header>${label}<span>${value ? '◆ SIMULATED' : '○ UNAVAILABLE'}</span></header><strong>${title}</strong><p>${body}</p><div class="bar" aria-label="Demonstration completeness ${value} percent"><i style="width:${value}%"></i></div><footer>SOURCE · GUARDIAN LOCAL DEMO / ${String(index + 1).padStart(2, '0')}</footer>`;
      return article;
    }));
    root.querySelector('#gce-domain-label').textContent = domain.toUpperCase();
    root.querySelector('#gce-title').textContent = titles[domain];
  };

  root.querySelectorAll('.gce-nav button[data-domain]').forEach(button => button.addEventListener('click', () => {
    root.querySelectorAll('.gce-nav button[data-domain]').forEach(item => { item.classList.toggle('active', item === button); item.removeAttribute('aria-current'); });
    button.setAttribute('aria-current', 'page');
    renderDomain(button.dataset.domain);
  }));

  const evidenceDialog = root.querySelector('#gce-evidence-dialog');
  const evidenceBody = root.querySelector('#gce-evidence-body');
  root.addEventListener('click', event => {
    const trigger = event.target.closest('[data-signal]');
    if (!trigger) return;
    const evidence = signalEvidence[trigger.dataset.signal];
    if (!evidence) return;
    const labels = ['Source ID','Source type','State','Classification','Confidence','Methodology','Warnings'];
    evidenceBody.innerHTML = `<dl>${labels.map((label, index) => `<div><dt>${label}</dt><dd>${evidence[index]}</dd></div>`).join('')}</dl><p>Observed and validated at page initialization. Responsible service: GUARDIAN local simulation adapter. No responsible agent is connected. Transformation history: fixed fixture → schema validation → accessible render.</p>`;
    evidenceDialog.showModal();
  });

  const commandDialog = root.querySelector('#gce-command-dialog');
  const commandInput = root.querySelector('#gce-command-input');
  const commandOutput = root.querySelector('#gce-command-output');
  const openCommand = () => { commandDialog.showModal(); requestAnimationFrame(() => commandInput.focus()); };
  root.querySelector('#gce-command-open').addEventListener('click', openCommand);
  document.addEventListener('keydown', event => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); openCommand(); } });
  const commandResponses = {stale:'VERIFIED EVIDENCE: zero live sources are registered. ANALYSIS: freshness cannot be established. RECOMMENDATION: connect and validate an authorized adapter. REQUIRED APPROVAL: source owner and security owner.',agents:'VERIFIED EVIDENCE: no agent runtime is connected. ANALYSIS: there are no real agent states to display. REQUIRED APPROVAL: platform owner before registering tools or permissions.',changed:'VERIFIED EVIDENCE: the local shell initialized, four deterministic demo adapters normalized, and one simulated policy candidate was held. INFERENCE and FORECAST: none produced.'};
  root.querySelector('#gce-command-list').addEventListener('click', event => { const button = event.target.closest('button'); if (button) { event.preventDefault(); commandInput.value = button.textContent; commandOutput.textContent = commandResponses[button.value]; } });
  commandInput.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); commandOutput.textContent = 'UNAVAILABLE: this static command surface supports only the listed deterministic queries. No remote model, search service, or hidden execution tool is connected.'; } });

  const safeButton = root.querySelector('#gce-safe-mode');
  safeButton.addEventListener('click', () => { const enabled = safeButton.getAttribute('aria-pressed') !== 'true'; safeButton.setAttribute('aria-pressed', String(enabled)); safeButton.textContent = enabled ? 'Safe Mode: Active' : 'Safe Mode'; root.classList.toggle('safe-mode', enabled); });
  const motionButton = root.querySelector('#gce-motion');
  motionButton.addEventListener('click', () => { const disabled = motionButton.getAttribute('aria-pressed') !== 'true'; motionButton.setAttribute('aria-pressed', String(disabled)); motionButton.textContent = disabled ? 'Motion: Off' : 'Motion: Auto'; root.classList.toggle('motion-off', disabled); });

  const clock = root.querySelector('#gce-utc');
  const updateClock = () => { clock.textContent = new Intl.DateTimeFormat('en-GB', {hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false,timeZone:'UTC'}).format(new Date()); };
  updateClock(); setInterval(updateClock, 1000);
  renderDomain('command');
})();
