# infra/github/variables.tf
variable "github_owner" {
  type        = string
  description = "GitHub organization that owns the repositories."
  default     = "ClearGlassInc"
}

variable "production_repos" {
  type        = list(string)
  description = "Repositories that receive the hardened 'main' ruleset."
  default     = ["ClearGlassInc.github.io"]
}

variable "required_status_checks" {
  type        = list(string)
  description = "Status check contexts that must pass before merge."
  # Each entry must exactly match a job `name:` (the emitted check-run context),
  # not a workflow file/name. "Policy Gate" maps to the job in
  # .github/workflows/policy-gate.yml.
  default = [
    "Policy Gate",
    "Python Tests",
    "Lint (ruff)",
    "Site Reliability Audit",
  ]
}

variable "required_review_count" {
  type        = number
  description = "Approving reviews required on protected branches."
  default     = 1
}
