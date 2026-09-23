"""Lifecycle invariants for the ClearGlass cinematic motion system.

`clearglass-motion.js` drives two long-lived requestAnimationFrame loops: the
constellation's connective field and the full-viewport atmospheric particle
field. Both are budgeted — paused offscreen, paused on a hidden tab, and torn
down when the visitor asks for reduced motion.

Four defects were measured in Chromium before these invariants existed:

1. Clicking "Reduce visual effects" tore down only the constellation, because
   the toggle looked up disposer properties by name and the atmosphere field
   stored its disposer under a different one. The WebGL field kept drawing
   into a `display:none` canvas after the visitor had opted out.
2. The `visibilitychange` handler called `start()` unconditionally, so
   returning to the tab resurrected an already-disposed renderer, which then
   drew into a detached, zero-sized canvas for the rest of the session.
3. The same handler also restarted a loop whose host was scrolled offscreen,
   defeating the IntersectionObserver pause.
4. The pointer handlers read the motion preference once at bind time, so glass
   highlight, tilt, magnet and cursor writes continued after the opt-out.

CI here has no browser, so these are pinned as structural invariants over the
source: each is the specific guard whose absence produced the defect above.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "clearglass-motion.js").read_text(encoding="utf-8")

# The two render loops, and the functions that must consult the live preference.
RENDER_LOOPS = ("startAmbient", "initAtmosphereField")
POINTER_INITS = ("initPointerGlass", "initCursorLight", "initCustomCursor")


def _function_body(name: str) -> str:
    """Return the body of `function <name>(...)`, matched by brace counting."""
    marker = f"function {name}("
    start = SOURCE.find(marker)
    assert start != -1, f"{name}() not found in clearglass-motion.js"
    open_brace = SOURCE.index("{", SOURCE.index(")", start))
    depth = 0
    for i in range(open_brace, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[open_brace : i + 1]
    raise AssertionError(f"unbalanced braces while reading {name}()")


@pytest.mark.parametrize("loop", RENDER_LOOPS)
def test_render_loops_gate_every_restart_on_one_condition_set(loop: str) -> None:
    """start() must refuse for a disposed or opted-out loop.

    Defect 2/3: any caller — a tab switch, a resize, an observer — could
    restart a torn-down renderer because start() only checked `running`.
    """
    body = _function_body(loop)
    assert "disposed = false" in body, f"{loop}() must track a disposed state"

    start = body[body.index("function start()") :]
    guard = start[: start.index("\n", start.index("return"))]
    assert "disposed" in guard, f"{loop}() start() must refuse once disposed"
    assert "motionReduced()" in guard, (
        f"{loop}() start() must refuse while the visitor has opted out of motion"
    )


def test_constellation_start_also_refuses_while_offscreen() -> None:
    """Defect 3: the offscreen pause must survive a tab switch."""
    body = _function_body("startAmbient")
    assert "onScreen" in body, "startAmbient() must track viewport presence"

    start = body[body.index("function start()") :]
    guard = start[: start.index("\n", start.index("return"))]
    assert "onScreen" in guard, (
        "startAmbient() start() must refuse while the stage is offscreen, or a "
        "tab switch will restart an invisible loop"
    )

    observer = body[body.index("IntersectionObserver(") :]
    assert "onScreen = entries[0].isIntersecting" in observer, (
        "the pause observer must record visibility, not just start/stop"
    )


@pytest.mark.parametrize("loop", RENDER_LOOPS)
def test_dispose_detaches_everything_that_could_restart_the_loop(loop: str) -> None:
    """Defect 2: teardown left live listeners holding the disposed renderer."""
    body = _function_body(loop)
    dispose = body[body.index("function dispose()") :]

    assert "if (disposed) return;" in dispose, f"{loop}() dispose() must be idempotent"
    assert "disposed = true" in dispose
    assert "removeEventListener('visibilitychange', onVisibility)" in dispose, (
        f"{loop}() must detach its visibilitychange listener on teardown"
    )
    assert "removeEventListener('pagehide', dispose)" in dispose
    assert "removeEventListener('resize', resize)" in dispose


def test_constellation_dispose_disconnects_its_observers() -> None:
    dispose = _function_body("startAmbient")
    dispose = dispose[dispose.index("function dispose()") :]
    assert "pauseObserver.disconnect()" in dispose, (
        "the offscreen-pause observer must be disconnected, or it can call "
        "start() again after teardown"
    )
    assert "ro.disconnect()" in dispose


@pytest.mark.parametrize("loop", RENDER_LOOPS)
def test_every_render_loop_registers_its_disposer(loop: str) -> None:
    """Defect 1: a loop the toggle cannot find is a loop it cannot stop."""
    assert "registerDisposer(dispose)" in _function_body(loop), (
        f"{loop}() must register its teardown so disposeAll() reaches it"
    )


def test_motion_toggle_tears_down_every_registered_loop() -> None:
    """Defect 1: the toggle used a name-based lookup and missed a whole loop."""
    body = _function_body("initMotionToggle")
    assert "disposeAll()" in body, (
        "the motion toggle must dispose through the registry so no loop is missed"
    )
    assert "cgDispose" not in body, (
        "the toggle must not hunt for disposer properties by name — that is the "
        "lookup that left the atmosphere field running after the opt-out"
    )


def test_dispose_all_drains_the_registry_and_survives_a_failing_teardown() -> None:
    body = _function_body("disposeAll")
    assert "disposers.length = 0" in body, "disposeAll() must drain the registry"
    assert "try {" in body and "catch" in body, (
        "one failing teardown must not block the remaining ones"
    )


@pytest.mark.parametrize("init", POINTER_INITS)
def test_pointer_handlers_read_the_preference_per_event(init: str) -> None:
    """Defect 4: the preference was read at bind time, so the opt-out was inert.

    Every pointermove handler must re-check, because a visitor can flip the
    preference long after the listener was attached.
    """
    body = _function_body(init)
    for handler in body.split("addEventListener('pointermove'")[1:]:
        head = handler[: handler.index("queueWrite")]
        assert "motionReduced()" in head, (
            f"{init}() has a pointermove handler that does not re-check the "
            "motion preference before doing layout-reading work"
        )


def test_disposer_registry_is_the_single_teardown_path() -> None:
    """Both public disposer properties stay, for tests and SPA unmount."""
    assert "stage.cgDispose = dispose" in SOURCE
    assert "atmos.cgmDispose = dispose" in SOURCE
    assert SOURCE.count("registerDisposer(dispose)") == len(RENDER_LOOPS)
