export function createAgentRun(input) {
  return {
    id: 'agentops-run',
    input,
    status: 'created'
  };
}
