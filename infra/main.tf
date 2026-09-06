terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" { type = string default = "us-east-1" }
variable "github_app_id" { type = string }
variable "github_app_key_base64" { type = string sensitive = true }
variable "github_app_webhook_secret" { type = string sensitive = true }
variable "github_owner" { type = string }
variable "github_repo" { type = string }
variable "runner_os" { type = string default = "linux" }
variable "runner_architecture" { type = string default = "x64" }

module "github_runners" {
  source  = "github-aws-runners/terraform-aws-github-runner/aws"
  version = "~> 5.0"

  aws_region = var.aws_region

  prefix = "clearglass"

  github_app = {
    key_base64     = var.github_app_key_base64
    id             = var.github_app_id
    webhook_secret = var.github_app_webhook_secret
  }

  github_owner = var.github_owner
  github_repositories = [var.github_repo]

  instance_types = ["t3.large", "t3a.large"]
  enable_organization_runners = false
  runner_os = var.runner_os
  runner_architecture = var.runner_architecture

  idle_config = [{
    cron      = "* * * * *"
    timeZone  = "UTC"
    idleCount = 0
  }]

  minimum_running_time_in_minutes = 5
  runners_maximum_count = 10
  enable_ssm_on_runners = true
  enable_ephemeral_runners = true

  # network hardening
  runner_egress_rules = [
    { from_port = 443, to_port = 443, protocol = "tcp", cidr_blocks = ["0.0.0.0/0"] }
  ]
}
