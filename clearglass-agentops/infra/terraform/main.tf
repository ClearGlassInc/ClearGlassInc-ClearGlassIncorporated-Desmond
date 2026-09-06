terraform {
  required_version = ">= 1.6.0"
}

variable "environment_name" {
  type    = string
  default = "dev"
}

output "agentops_environment" {
  value = var.environment_name
}
