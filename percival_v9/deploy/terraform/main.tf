# Percival v9 — EKS control-plane skeleton. AUTHORED, NOT APPLIED.
# `terraform plan` requires operator-supplied credentials (via the environment's
# secret store) and runs against a NON-PROD account first. Never a blind apply.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # backend "s3" {}  # configured out-of-band per environment; never commit state.
}

provider "aws" {
  region = var.region
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "~> 20.0"
  cluster_name    = "percival-v9-${var.environment}"
  cluster_version = "1.30"

  cluster_endpoint_public_access = false # private endpoint; access via VPN/bastion
  enable_irsa                    = true  # IAM Roles for Service Accounts

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 5
      desired_size   = 3
    }
  }

  tags = {
    Project    = "percival-v9"
    Managed_by = "terraform"
    Env        = var.environment
  }
}

# Audit ledger durability (WORM): S3 with versioning + object lock.
resource "aws_s3_bucket" "audit_ledger" {
  bucket              = "clearglass-percival-audit-${var.environment}"
  object_lock_enabled = true
  tags                = { Project = "percival-v9", Purpose = "audit-worm" }
}

resource "aws_s3_bucket_versioning" "audit_ledger" {
  bucket = aws_s3_bucket.audit_ledger.id
  versioning_configuration { status = "Enabled" }
}
