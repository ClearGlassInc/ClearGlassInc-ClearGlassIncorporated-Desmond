export function activate(context = {}) {
  return {
    name: 'clearglass-agentops-extension',
    status: 'active',
    context
  };
}

console.log(JSON.stringify(activate({ source: 'cli' }), null, 2));
