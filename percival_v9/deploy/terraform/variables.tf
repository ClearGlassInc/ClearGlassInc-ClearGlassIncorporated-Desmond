# Percival v9 Terraform inputs. AUTHORED, NOT APPLIED.

variable "region" {
  description = "AWS region for the EKS cluster and audit bucket."
  type        = string
  default     = "ca-central-1" # Canada, matching ClearGlass's Ontario base
}

variable "environment" {
  description = "Deployment environment slug (nonprod first, always)."
  type        = string
  default     = "nonprod"

  validation {
    condition     = contains(["nonprod", "staging", "prod"], var.environment)
    error_message = "environment must be one of: nonprod, staging, prod."
  }
}
