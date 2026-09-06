# infra/github/providers.tf
#
# GitHub-as-code: org configuration (rulesets, teams, repo settings) is
# declarative and version-controlled. `terraform plan` in CI detects drift —
# nobody configures protections by clicking in the UI.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.2"
    }
  }
}

provider "github" {
  owner = var.github_owner
  # Auth via GITHUB_TOKEN / GitHub App env vars in CI (OIDC-minted, short-lived).
}
