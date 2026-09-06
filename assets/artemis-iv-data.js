window.ARTEMIS_IV_DATA = {
  executiveMetrics: {
    pipelineValue: '$2.14M',
    targetPercent: 63,
    targetProgressLabel: '$630K / $1M',
    threatLevel: 'ELEVATED',
    activeDeals: 7
  },
  threatActors: [
    { name: 'APT41', status: 'ELEVATED', severity: 'HIGH', industries: 'Telecom, Healthcare', salesRelevance: 'High', region: 'China-linked', impact: 87, opportunity: 78, recommendation: 'Lead with supply-chain hardening and managed detection bundle.' },
    { name: 'FIN7', status: 'ACTIVE', severity: 'HIGH', industries: 'Retail, Hospitality', salesRelevance: 'High', region: 'Russia-linked', impact: 80, opportunity: 74, recommendation: 'Push incident readiness and endpoint isolation controls.' },
    { name: 'Lazarus', status: 'MONITOR', severity: 'MED', industries: 'Finance, Crypto', salesRelevance: 'Medium', region: 'North Korea-linked', impact: 71, opportunity: 61, recommendation: 'Prioritize transaction monitoring and threat hunt sprint.' },
    { name: 'TA505', status: 'LOW', severity: 'MED', industries: 'Banking', salesRelevance: 'Medium', region: 'Eastern Europe', impact: 59, opportunity: 52, recommendation: 'Bundle anti-phishing automation with SOC playbooks.' },
    { name: 'APT29', status: 'MONITOR', severity: 'MED', industries: 'Government, Energy', salesRelevance: 'High', region: 'Russia-linked', impact: 75, opportunity: 82, recommendation: 'Executive brief + compliance alignment (C-26/NIS2).' }
  ],
  feedStatuses: ['NVD', 'GDELT', 'ADS-B', 'USGS', 'WHOIS', 'SIGINT', 'OSINT'],
  geopoliticalPulse: {
    label: 'Synthetic demo intelligence feed for UI/testing only.',
    events: [
      'Bill C-26 critical infrastructure reporting window drives urgent buyer activity.',
      'NIS2 enforcement milestones increase external SOC demand in energy operators.',
      'Emergency patch directives observed for edge appliances in public-sector estates.',
      'Managed service providers report exploitation pressure on remote access systems.'
    ]
  },
  quickCommands: ['CVE → SALES NORTH AMERICA', 'BURLINGTON CLOSE', 'HALTON SMS', 'C-26 BRIEF']
};
