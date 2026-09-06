from scripts.validate_production_deploy import validate_configuration


VALID = {
    "CHANGE_TICKET": "CHG-1234",
    "RENDER_DEPLOY_HOOK_URL": "https://api.render.com/deploy/srv-a?key=deploy",
    "RENDER_ROLLBACK_HOOK_URL": "https://api.render.com/deploy/srv-a?key=rollback",
    "CONTROL_PLANE_URL": "https://control.example.com",
}


def test_valid_configuration_is_accepted() -> None:
    assert validate_configuration(VALID) == []


def test_missing_configuration_reports_names_without_values() -> None:
    errors = validate_configuration({})
    assert errors == [
        "change_ticket input is required",
        "RENDER_DEPLOY_HOOK_URL is required",
        "RENDER_ROLLBACK_HOOK_URL is required",
        "CONTROL_PLANE_URL is required",
    ]


def test_rejects_unsafe_or_ambiguous_configuration() -> None:
    configuration = {
        **VALID,
        "CHANGE_TICKET": "not a ticket",
        "RENDER_DEPLOY_HOOK_URL": "http://user:secret@example.com/hook#fragment",
        "RENDER_ROLLBACK_HOOK_URL": "http://user:secret@example.com/hook#fragment",
        "CONTROL_PLANE_URL": "https://control.example.com?token=secret",
    }

    errors = validate_configuration(configuration)

    assert "change_ticket must be a bounded reference such as CHG-1234" in errors
    assert "RENDER_DEPLOY_HOOK_URL must be an absolute HTTPS URL" in errors
    assert "RENDER_DEPLOY_HOOK_URL must not contain URL credentials" in errors
    assert "RENDER_DEPLOY_HOOK_URL must not contain a fragment" in errors
    assert "CONTROL_PLANE_URL must not contain a query string" in errors
    assert "deploy and rollback hooks must be different" in errors
