-- CreateEnum
CREATE TYPE "Role" AS ENUM ('ADMINISTRATOR', 'ANALYST', 'REVIEWER', 'READ_ONLY');

-- CreateEnum
CREATE TYPE "DataOrigin" AS ENUM ('SYNTHETIC', 'PUBLIC_SOURCE', 'INTERNAL_RECORD', 'ANALYST_ENTERED');

-- CreateEnum
CREATE TYPE "ClaimStatus" AS ENUM ('ALLEGATION', 'SOURCE_SUPPORTED_OBSERVATION', 'ANALYST_INTERPRETATION', 'REVIEWED_FINDING');

-- CreateEnum
CREATE TYPE "VerificationStatus" AS ENUM ('UNVERIFIED', 'PARTIALLY_VERIFIED', 'VERIFIED', 'DISPUTED', 'REJECTED');

-- CreateEnum
CREATE TYPE "AccessClassification" AS ENUM ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED');

-- CreateEnum
CREATE TYPE "ExtractionMethod" AS ENUM ('SYNTHETIC_FIXTURE', 'MANUAL_EXCERPT', 'CSV_IMPORT', 'JSON_IMPORT', 'MOCK_ADAPTER');

-- CreateEnum
CREATE TYPE "SourceKind" AS ENUM ('SYNTHETIC_FIXTURE', 'PUBLIC_WEB', 'PUBLIC_RECORD', 'INTERNAL_SYSTEM', 'ANALYST_PROVIDED');

-- CreateEnum
CREATE TYPE "TransactionType" AS ENUM ('PURCHASE_ORDER', 'INVOICE', 'PAYMENT', 'BANK_DETAIL_CHANGE', 'CHANGE_ORDER', 'CONTRACT');

-- CreateEnum
CREATE TYPE "IncidentStepKind" AS ENUM ('OBSERVATION', 'ACTOR', 'EVENT', 'EVIDENCE_GAP', 'CONTRADICTION');

-- CreateEnum
CREATE TYPE "RuleVersionStatus" AS ENUM ('DRAFT', 'PENDING_APPROVAL', 'ACTIVE', 'SUPERSEDED', 'REJECTED', 'RETIRED');

-- CreateEnum
CREATE TYPE "EvaluationOutcome" AS ENUM ('MATCH', 'NO_MATCH', 'INSUFFICIENT_DATA');

-- CreateEnum
CREATE TYPE "ReviewState" AS ENUM ('NEW', 'NEEDS_EVIDENCE', 'UNDER_REVIEW', 'ESCALATED_FOR_REVIEW', 'EXPLAINED_NO_FURTHER_ACTION', 'CLOSED');

-- CreateEnum
CREATE TYPE "ReviewPriority" AS ENUM ('LOW', 'MEDIUM', 'HIGH');

-- CreateEnum
CREATE TYPE "EntityKind" AS ENUM ('PERSON', 'ORGANIZATION', 'VENDOR', 'DOMAIN');

-- CreateEnum
CREATE TYPE "RelationshipBasis" AS ENUM ('EXPLICIT_IDENTIFIER', 'DOCUMENTED_IN_EVIDENCE', 'CANDIDATE_NAME_SIMILARITY', 'CANDIDATE_SHARED_ADDRESS', 'CANDIDATE_SHARED_DOMAIN', 'ANALYST_ASSERTED');

-- CreateEnum
CREATE TYPE "RelationshipStatus" AS ENUM ('CANDIDATE', 'CONFIRMED', 'REJECTED', 'REVERSED');

-- CreateEnum
CREATE TYPE "DecisionTarget" AS ENUM ('ALERT', 'INVESTIGATION', 'RULE_VERSION', 'RELATIONSHIP', 'EVIDENCE');

-- CreateEnum
CREATE TYPE "NoteKind" AS ENUM ('OBSERVATION', 'INTERPRETATION', 'QUESTION');

-- CreateEnum
CREATE TYPE "ImportFormat" AS ENUM ('CSV', 'JSON');

-- CreateEnum
CREATE TYPE "ImportRecordType" AS ENUM ('VENDOR', 'TRANSACTION', 'EVIDENCE', 'INCIDENT');

-- CreateEnum
CREATE TYPE "ImportStatus" AS ENUM ('VALIDATED', 'COMMITTED', 'REJECTED');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "role" "Role" NOT NULL,
    "isDemo" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Source" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "kind" "SourceKind" NOT NULL,
    "title" TEXT NOT NULL,
    "url" TEXT,
    "publisher" TEXT,
    "origin" "DataOrigin" NOT NULL,
    "accessClassification" "AccessClassification" NOT NULL,
    "limitations" TEXT,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Source_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Evidence" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "sourceId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "excerpt" TEXT NOT NULL,
    "url" TEXT,
    "documentLocation" TEXT,
    "publishedAt" TIMESTAMP(3),
    "observedAt" TIMESTAMP(3),
    "collectedAt" TIMESTAMP(3),
    "ingestedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "contentHash" TEXT NOT NULL,
    "hashAlgorithm" TEXT NOT NULL DEFAULT 'sha256',
    "verificationStatus" "VerificationStatus" NOT NULL DEFAULT 'UNVERIFIED',
    "verifiedById" TEXT,
    "verifiedAt" TIMESTAMP(3),
    "accessClassification" "AccessClassification" NOT NULL,
    "extractionMethod" "ExtractionMethod" NOT NULL,
    "origin" "DataOrigin" NOT NULL,
    "limitations" TEXT,
    "providedFields" TEXT[],
    "missingFields" TEXT[],
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "importBatchId" TEXT,

    CONSTRAINT "Evidence_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ExtractedFact" (
    "id" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,
    "statement" TEXT NOT NULL,
    "claimStatus" "ClaimStatus" NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ExtractedFact_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Incident" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "claimStatus" "ClaimStatus" NOT NULL,
    "origin" "DataOrigin" NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "documentedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Incident_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "IncidentEvidence" (
    "incidentId" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,

    CONSTRAINT "IncidentEvidence_pkey" PRIMARY KEY ("incidentId","evidenceId")
);

-- CreateTable
CREATE TABLE "IncidentStep" (
    "id" TEXT NOT NULL,
    "incidentId" TEXT NOT NULL,
    "kind" "IncidentStepKind" NOT NULL,
    "position" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "evidenceId" TEXT,
    "isAssumption" BOOLEAN NOT NULL DEFAULT false,
    "occurredAt" TIMESTAMP(3),

    CONSTRAINT "IncidentStep_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Organization" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "registrationNumber" TEXT,
    "domain" TEXT,
    "address" TEXT,
    "origin" "DataOrigin" NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Organization_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Vendor" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "taxId" TEXT,
    "domain" TEXT,
    "address" TEXT,
    "organizationId" TEXT,
    "origin" "DataOrigin" NOT NULL,
    "providedFields" TEXT[],
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "importBatchId" TEXT,
    "contentHash" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Vendor_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Person" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "displayName" TEXT NOT NULL,
    "roleTitle" TEXT,
    "organizationId" TEXT,
    "origin" "DataOrigin" NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Person_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Transaction" (
    "id" TEXT NOT NULL,
    "recordId" TEXT NOT NULL,
    "type" "TransactionType" NOT NULL,
    "vendorRecordId" TEXT,
    "vendorId" TEXT,
    "amount" DECIMAL(16,2),
    "currency" TEXT,
    "occurredAt" TIMESTAMP(3),
    "recordedAt" TIMESTAMP(3),
    "approvedAt" TIMESTAMP(3),
    "workStartedAt" TIMESTAMP(3),
    "approvedBy" TEXT,
    "poReference" TEXT,
    "invoiceReference" TEXT,
    "documents" TEXT[],
    "description" TEXT,
    "providedFields" TEXT[],
    "missingFields" TEXT[],
    "origin" "DataOrigin" NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "evidenceId" TEXT,
    "importBatchId" TEXT,
    "contentHash" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Transaction_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Relationship" (
    "id" TEXT NOT NULL,
    "fromKind" "EntityKind" NOT NULL,
    "fromId" TEXT NOT NULL,
    "toKind" "EntityKind" NOT NULL,
    "toId" TEXT NOT NULL,
    "relationType" TEXT NOT NULL,
    "basis" "RelationshipBasis" NOT NULL,
    "basisDetail" TEXT NOT NULL,
    "status" "RelationshipStatus" NOT NULL,
    "claimStatus" "ClaimStatus" NOT NULL,
    "evidenceId" TEXT,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Relationship_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "DetectionRule" (
    "id" TEXT NOT NULL,
    "ruleKey" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "isIllustrative" BOOLEAN NOT NULL DEFAULT false,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "DetectionRule_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RuleVersion" (
    "id" TEXT NOT NULL,
    "ruleId" TEXT NOT NULL,
    "version" INTEGER NOT NULL,
    "definition" JSONB NOT NULL,
    "changeSummary" TEXT NOT NULL,
    "status" "RuleVersionStatus" NOT NULL,
    "proposedById" TEXT NOT NULL,
    "approvedById" TEXT,
    "approvedAt" TIMESTAMP(3),
    "approvalRationale" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RuleVersion_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RuleSupport" (
    "id" TEXT NOT NULL,
    "ruleVersionId" TEXT NOT NULL,
    "conditionId" TEXT,
    "evidenceId" TEXT,
    "incidentId" TEXT,

    CONSTRAINT "RuleSupport_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "EvaluationRun" (
    "id" TEXT NOT NULL,
    "triggeredById" TEXT NOT NULL,
    "startedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "finishedAt" TIMESTAMP(3),
    "summary" JSONB,

    CONSTRAINT "EvaluationRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RuleEvaluation" (
    "id" TEXT NOT NULL,
    "runId" TEXT NOT NULL,
    "ruleVersionId" TEXT NOT NULL,
    "subjectKey" TEXT NOT NULL,
    "outcome" "EvaluationOutcome" NOT NULL,
    "matchedRecordIds" TEXT[],
    "conditions" JSONB NOT NULL,
    "missingFields" JSONB NOT NULL,
    "evidenceRefs" TEXT[],
    "explanation" TEXT NOT NULL,
    "evaluatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "RuleEvaluation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Alert" (
    "id" TEXT NOT NULL,
    "ruleId" TEXT NOT NULL,
    "ruleVersionId" TEXT NOT NULL,
    "evaluationId" TEXT NOT NULL,
    "outcome" "EvaluationOutcome" NOT NULL,
    "status" "ReviewState" NOT NULL,
    "priority" "ReviewPriority" NOT NULL,
    "subjectKey" TEXT NOT NULL,
    "explanation" TEXT NOT NULL,
    "matchedRecordIds" TEXT[],
    "missingFields" JSONB NOT NULL,
    "conditions" JSONB NOT NULL,
    "evidenceRefs" TEXT[],
    "isSynthetic" BOOLEAN NOT NULL,
    "dedupeKey" TEXT NOT NULL,
    "investigationId" TEXT,
    "assignedToId" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Alert_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Investigation" (
    "id" TEXT NOT NULL,
    "caseKey" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "status" "ReviewState" NOT NULL,
    "priority" "ReviewPriority" NOT NULL,
    "claimStatus" "ClaimStatus" NOT NULL,
    "ownerId" TEXT NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Investigation_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "InvestigationNote" (
    "id" TEXT NOT NULL,
    "investigationId" TEXT NOT NULL,
    "authorId" TEXT NOT NULL,
    "kind" "NoteKind" NOT NULL,
    "body" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "InvestigationNote_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "NoteEvidence" (
    "noteId" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,

    CONSTRAINT "NoteEvidence_pkey" PRIMARY KEY ("noteId","evidenceId")
);

-- CreateTable
CREATE TABLE "ReviewDecision" (
    "id" TEXT NOT NULL,
    "targetType" "DecisionTarget" NOT NULL,
    "targetId" TEXT NOT NULL,
    "fromState" TEXT,
    "toState" TEXT NOT NULL,
    "rationale" TEXT NOT NULL,
    "ruleVersionId" TEXT,
    "decidedById" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ReviewDecision_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ImportBatch" (
    "id" TEXT NOT NULL,
    "format" "ImportFormat" NOT NULL,
    "recordType" "ImportRecordType" NOT NULL,
    "filename" TEXT NOT NULL,
    "fileHash" TEXT NOT NULL,
    "sizeBytes" INTEGER NOT NULL,
    "origin" "DataOrigin" NOT NULL,
    "isSynthetic" BOOLEAN NOT NULL,
    "status" "ImportStatus" NOT NULL,
    "totalRows" INTEGER NOT NULL,
    "acceptedRows" INTEGER NOT NULL,
    "rejectedRows" INTEGER NOT NULL,
    "duplicateRows" INTEGER NOT NULL,
    "report" JSONB NOT NULL,
    "submittedById" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ImportBatch_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AuditEvent" (
    "id" TEXT NOT NULL,
    "at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actorId" TEXT,
    "actorRole" TEXT,
    "action" TEXT NOT NULL,
    "targetType" TEXT,
    "targetId" TEXT,
    "outcome" TEXT NOT NULL DEFAULT 'ok',
    "details" JSONB,

    CONSTRAINT "AuditEvent_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Source_recordId_key" ON "Source"("recordId");

-- CreateIndex
CREATE UNIQUE INDEX "Evidence_recordId_key" ON "Evidence"("recordId");

-- CreateIndex
CREATE INDEX "Evidence_contentHash_idx" ON "Evidence"("contentHash");

-- CreateIndex
CREATE UNIQUE INDEX "Incident_recordId_key" ON "Incident"("recordId");

-- CreateIndex
CREATE INDEX "IncidentStep_incidentId_position_idx" ON "IncidentStep"("incidentId", "position");

-- CreateIndex
CREATE UNIQUE INDEX "Organization_recordId_key" ON "Organization"("recordId");

-- CreateIndex
CREATE UNIQUE INDEX "Vendor_recordId_key" ON "Vendor"("recordId");

-- CreateIndex
CREATE UNIQUE INDEX "Person_recordId_key" ON "Person"("recordId");

-- CreateIndex
CREATE UNIQUE INDEX "Transaction_recordId_key" ON "Transaction"("recordId");

-- CreateIndex
CREATE INDEX "Transaction_vendorRecordId_occurredAt_idx" ON "Transaction"("vendorRecordId", "occurredAt");

-- CreateIndex
CREATE INDEX "Transaction_contentHash_idx" ON "Transaction"("contentHash");

-- CreateIndex
CREATE UNIQUE INDEX "Relationship_fromKind_fromId_toKind_toId_relationType_basis_key" ON "Relationship"("fromKind", "fromId", "toKind", "toId", "relationType", "basis");

-- CreateIndex
CREATE UNIQUE INDEX "DetectionRule_ruleKey_key" ON "DetectionRule"("ruleKey");

-- CreateIndex
CREATE UNIQUE INDEX "RuleVersion_ruleId_version_key" ON "RuleVersion"("ruleId", "version");

-- CreateIndex
CREATE INDEX "RuleSupport_evidenceId_idx" ON "RuleSupport"("evidenceId");

-- CreateIndex
CREATE INDEX "RuleSupport_incidentId_idx" ON "RuleSupport"("incidentId");

-- CreateIndex
CREATE INDEX "RuleEvaluation_ruleVersionId_outcome_idx" ON "RuleEvaluation"("ruleVersionId", "outcome");

-- CreateIndex
CREATE UNIQUE INDEX "Alert_evaluationId_key" ON "Alert"("evaluationId");

-- CreateIndex
CREATE UNIQUE INDEX "Alert_dedupeKey_key" ON "Alert"("dedupeKey");

-- CreateIndex
CREATE INDEX "Alert_status_idx" ON "Alert"("status");

-- CreateIndex
CREATE UNIQUE INDEX "Investigation_caseKey_key" ON "Investigation"("caseKey");

-- CreateIndex
CREATE INDEX "ReviewDecision_targetType_targetId_idx" ON "ReviewDecision"("targetType", "targetId");

-- CreateIndex
CREATE INDEX "AuditEvent_action_at_idx" ON "AuditEvent"("action", "at");

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_sourceId_fkey" FOREIGN KEY ("sourceId") REFERENCES "Source"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_verifiedById_fkey" FOREIGN KEY ("verifiedById") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_importBatchId_fkey" FOREIGN KEY ("importBatchId") REFERENCES "ImportBatch"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ExtractedFact" ADD CONSTRAINT "ExtractedFact_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "IncidentEvidence" ADD CONSTRAINT "IncidentEvidence_incidentId_fkey" FOREIGN KEY ("incidentId") REFERENCES "Incident"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "IncidentEvidence" ADD CONSTRAINT "IncidentEvidence_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "IncidentStep" ADD CONSTRAINT "IncidentStep_incidentId_fkey" FOREIGN KEY ("incidentId") REFERENCES "Incident"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "IncidentStep" ADD CONSTRAINT "IncidentStep_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Vendor" ADD CONSTRAINT "Vendor_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Vendor" ADD CONSTRAINT "Vendor_importBatchId_fkey" FOREIGN KEY ("importBatchId") REFERENCES "ImportBatch"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Person" ADD CONSTRAINT "Person_organizationId_fkey" FOREIGN KEY ("organizationId") REFERENCES "Organization"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Transaction" ADD CONSTRAINT "Transaction_vendorId_fkey" FOREIGN KEY ("vendorId") REFERENCES "Vendor"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Transaction" ADD CONSTRAINT "Transaction_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Transaction" ADD CONSTRAINT "Transaction_importBatchId_fkey" FOREIGN KEY ("importBatchId") REFERENCES "ImportBatch"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Relationship" ADD CONSTRAINT "Relationship_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleVersion" ADD CONSTRAINT "RuleVersion_ruleId_fkey" FOREIGN KEY ("ruleId") REFERENCES "DetectionRule"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleVersion" ADD CONSTRAINT "RuleVersion_proposedById_fkey" FOREIGN KEY ("proposedById") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleVersion" ADD CONSTRAINT "RuleVersion_approvedById_fkey" FOREIGN KEY ("approvedById") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleSupport" ADD CONSTRAINT "RuleSupport_ruleVersionId_fkey" FOREIGN KEY ("ruleVersionId") REFERENCES "RuleVersion"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleSupport" ADD CONSTRAINT "RuleSupport_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleSupport" ADD CONSTRAINT "RuleSupport_incidentId_fkey" FOREIGN KEY ("incidentId") REFERENCES "Incident"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleEvaluation" ADD CONSTRAINT "RuleEvaluation_runId_fkey" FOREIGN KEY ("runId") REFERENCES "EvaluationRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RuleEvaluation" ADD CONSTRAINT "RuleEvaluation_ruleVersionId_fkey" FOREIGN KEY ("ruleVersionId") REFERENCES "RuleVersion"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_ruleId_fkey" FOREIGN KEY ("ruleId") REFERENCES "DetectionRule"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_ruleVersionId_fkey" FOREIGN KEY ("ruleVersionId") REFERENCES "RuleVersion"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_evaluationId_fkey" FOREIGN KEY ("evaluationId") REFERENCES "RuleEvaluation"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_investigationId_fkey" FOREIGN KEY ("investigationId") REFERENCES "Investigation"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_assignedToId_fkey" FOREIGN KEY ("assignedToId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Investigation" ADD CONSTRAINT "Investigation_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "InvestigationNote" ADD CONSTRAINT "InvestigationNote_investigationId_fkey" FOREIGN KEY ("investigationId") REFERENCES "Investigation"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "InvestigationNote" ADD CONSTRAINT "InvestigationNote_authorId_fkey" FOREIGN KEY ("authorId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NoteEvidence" ADD CONSTRAINT "NoteEvidence_noteId_fkey" FOREIGN KEY ("noteId") REFERENCES "InvestigationNote"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NoteEvidence" ADD CONSTRAINT "NoteEvidence_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ReviewDecision" ADD CONSTRAINT "ReviewDecision_decidedById_fkey" FOREIGN KEY ("decidedById") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ImportBatch" ADD CONSTRAINT "ImportBatch_submittedById_fkey" FOREIGN KEY ("submittedById") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AuditEvent" ADD CONSTRAINT "AuditEvent_actorId_fkey" FOREIGN KEY ("actorId") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
