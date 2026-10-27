"""The coin API's dev server must not start exposed by default.

``clearglass_api.py`` shipped ``app.run(host='0.0.0.0', port=5000, debug=True)``:
the Werkzeug debugger, which executes code for whoever reaches it, on every
network interface. QUICKSTART.md and TECHNICAL_DOCS.md only ever document
``http://localhost:5000``, so loopback with the debugger off is the documented
behaviour; both stay available through explicit environment opt-ins.

Checked statically: importing the module needs Flask, which root CI does not
install.
"""
from __future__ import annotations

import ast
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "clearglass_api.py"


def run_call() -> ast.Call:
    calls = [
        node
        for node in ast.walk(ast.parse(API.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "app"
    ]
    assert len(calls) == 1, "expected exactly one app.run(...) call"
    return calls[0]


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def test_debugger_is_never_on_by_default() -> None:
    debug = keyword(run_call(), "debug")
    assert not (isinstance(debug, ast.Constant) and debug.value is True), (
        "app.run(debug=True) starts the Werkzeug debugger unconditionally"
    )


def test_server_binds_loopback_unless_told_otherwise() -> None:
    host = keyword(run_call(), "host")
    assert not (isinstance(host, ast.Constant) and host.value == "0.0.0.0"), (
        "app.run(host='0.0.0.0') listens on every interface by default"
    )
    if host is not None and not isinstance(host, ast.Constant):
        # An environment lookup: its fallback must be loopback.
        assert "'127.0.0.1'" in ast.unparse(host), ast.unparse(host)
