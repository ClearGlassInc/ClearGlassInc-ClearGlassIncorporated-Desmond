"""Lifecycle guards for pointer-driven motion components."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_glass_card_cancels_pending_pointer_frame_on_leave_and_mode_change() -> None:
    source = (ROOT / "components/motion/GlassCard.tsx").read_text(encoding="utf-8")
    leave = source[source.index("const onPointerLeave") : source.index("return (")]
    assert "cancelAnimationFrame(frame.current)" in leave
    assert "frame.current = null" in leave
    assert "useEffect(" in leave
    assert "[interactive]" in leave
    move = source[source.index("const onPointerMove") : source.index("const onPointerLeave")]
    assert "frame.current = null;" in move


def test_magnetic_button_cancels_pending_pointer_frame_on_reset_and_mode_change() -> None:
    source = (ROOT / "components/motion/MagneticButton.tsx").read_text(encoding="utf-8")
    reset = source[source.index("const reset") : source.index("return (")]
    assert "cancelAnimationFrame(frame.current)" in reset
    assert "frame.current = null" in reset
    assert "useEffect(" in reset
    assert "[enabled]" in reset
    assert "node.style.setProperty(\"--cgm-btn-x\", \"0px\")" in reset
