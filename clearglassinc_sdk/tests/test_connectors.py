import sys

import pytest


@pytest.mark.parametrize(
    "module_name,class_name",
    [
        ("clearglassinc_sdk.connectors.github", "GitHubConnector"),
        ("clearglassinc_sdk.connectors.slack", "SlackConnector"),
        ("clearglassinc_sdk.connectors.outlook", "OutlookConnector"),
    ],
)
def test_connector_raises_clean_import_error_without_httpx(module_name, class_name, monkeypatch):
    if "httpx" in sys.modules:
        pytest.skip("httpx is installed in this environment; import-error path not exercised")

    import importlib

    module = importlib.import_module(module_name)
    connector_cls = getattr(module, class_name)

    with pytest.raises(ImportError, match="httpx"):
        connector_cls("fake-token")
