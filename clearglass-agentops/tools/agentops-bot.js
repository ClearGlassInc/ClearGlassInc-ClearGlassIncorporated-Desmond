import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const workspace = process.cwd().endsWith('clearglass-agentops')
  ? process.cwd()
  : path.join(process.cwd(), 'clearglass-agentops');

const command = process.argv[2] || 'doctor';
const dirs = [
  'apps/bot-api/src',
  'apps/copilot-extension/src',
  'packages/agent-core/src',
  'packages/policy-engine/src',
  'packages/connectors/src',
  'packages/audit-logger/src',
  'packages/schemas',
  'infra/bicep',
  'infra/terraform',
  'docs/architecture',
  'docs/runbooks',
  'docs/compliance',
  'reports'
];

function makeDirs() {
  for (const d of dirs) mkdirSync(path.join(workspace, d), { recursive: true });
}

function save(name, payload) {
  mkdirSync(path.join(workspace, 'reports'), { recursive: true });
  writeFileSync(path.join(workspace, 'reports', `${name}.json`), JSON.stringify(payload, null, 2));
  console.log(JSON.stringify(payload, null, 2));
}

function doctor() {
  makeDirs();
  const report = { ok: true, command: 'doctor', checkedAt: new Date().toISOString(), node: process.version, workspace };
  save('doctor', report);
  return report;
}

function debug() {
  doctor();
  const checks = [
    ['bot-api', 'apps/bot-api/src/index.mjs'],
    ['extension', 'apps/copilot-extension/src/extension.js'],
    ['policy', 'packages/policy-engine/src/policy.js']
  ].map(([name, file]) => ({ name, file, pass: existsSync(path.join(workspace, file)) }));
  const report = { ok: checks.every(c => c.pass), command: 'debug', checkedAt: new Date().toISOString(), checks };
  save('debug', report);
  if (!report.ok) throw new Error('debug checks failed');
}

function release() {
  debug();
  const report = {
    ok: true,
    command: 'release',
    checkedAt: new Date().toISOString(),
    services: ['bot-api', 'copilot-extension'],
    evidence: ['reports/doctor.json', 'reports/debug.json']
  };
  save('release', report);
}

if (command === 'doctor') doctor();
else if (command === 'debug') debug();
else if (command === 'deploy' || command === 'release') release();
else throw new Error(`Unknown command: ${command}`);
