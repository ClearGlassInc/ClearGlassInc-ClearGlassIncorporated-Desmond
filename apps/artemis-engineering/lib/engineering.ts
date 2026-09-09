export type JobState = 'QUEUED'|'RUNNING'|'COMPLETED'|'FAILED'|'CANCELLED';
export type EvidenceState = 'PROTOTYPE'|'SIMULATION'|'VALIDATED'|'VERIFIED'|'CERTIFIED';

export interface EngineeringArtifact { id:string; version:string; created_at:string; updated_at:string; author:string; status:EvidenceState; parent?:string; provenance:string[]; }
export interface SimulationJob { id:string; domain:string; model:string; solver:string; mesh:string; state:JobState; provenance:string[]; created_at:string; }

export const adapters = ['CAD_KERNEL_ADAPTER','FEA_SOLVER_ADAPTER','CFD_SOLVER_ADAPTER','EM_SOLVER_ADAPTER','CONTROL_SIMULATOR_ADAPTER','MES_ADAPTER','PLM_ADAPTER','AI_MODEL_ADAPTER'] as const;

export const demoPolicy = {
  demoData: true,
  certifiedResultsRequireValidatedSolver: true,
  aiMayProposeChanges: true,
  aiMaySilentlyModifyValidatedArtifacts: false,
  auditEnabled: true
} as const;
