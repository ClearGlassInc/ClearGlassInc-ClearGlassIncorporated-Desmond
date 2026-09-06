export function evaluatePolicy(request = {}) {
  const action = String(request.action || '').toLowerCase();
  const allowed = ['doctor', 'debug', 'deploy', 'release', 'status'];
  const pass = allowed.includes(action);
  return {
    pass,
    action,
    allowed,
    reason: pass ? 'allowed_action' : 'blocked_unknown_action'
  };
}
