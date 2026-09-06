# infra/github/rulesets.tf
#
# Repository rulesets supersede legacy branch protection: layerable, native
# merge-queue support, and managed as code. Applied to every production repo.
resource "github_repository_ruleset" "main_protection" {
  for_each    = toset(var.production_repos)
  name        = "main-protection"
  repository  = each.value
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
  }

  rules {
    # No direct deletion or force-push of the protected branch.
    deletion         = true
    non_fast_forward = true

    # Linear history — squash/rebase only, no merge commits.
    required_linear_history = true

    # Commit signing required.
    required_signatures = true

    pull_request {
      required_approving_review_count   = var.required_review_count
      dismiss_stale_reviews_on_push     = true
      require_code_owner_review         = true
      require_last_push_approval        = true # the last pusher cannot self-approve
      required_review_thread_resolution = true
    }

    required_status_checks {
      strict_required_status_checks_policy = true # branch must be current before merge

      dynamic "required_check" {
        for_each = toset(var.required_status_checks)
        content {
          context = required_check.value
        }
      }
    }
  }

  # Even org admins route through a PR — no silent bypass.
  bypass_actors {
    actor_id    = 1
    actor_type  = "OrganizationAdmin"
    bypass_mode = "pull_request"
  }
}
