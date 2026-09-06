@description('ClearGlass AgentOps deployment location')
param location string = resourceGroup().location

@description('Environment name')
param environmentName string = 'dev'

output agentopsEnvironment string = environmentName
output deploymentLocation string = location
