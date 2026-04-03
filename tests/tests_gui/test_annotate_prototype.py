from __future__ import annotations

from types import SimpleNamespace

from PySide6 import QtCore, QtGui

from normcap.annotate_prototype import app, editor
from normcap.annotate_prototype.models import EffectAnnotation, Tool
from normcap.system.models import Rect


def _changed_pixels(
    before: QtGui.QImage,
    after: QtGui.QImage,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> int:
    changed = 0
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            if before.pixelColor(x, y) != after.pixelColor(x, y):
                changed += 1
    return changed


def test_open_annotation_window_is_scheduled(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_close_capture_windows() -> None:
        calls["closed"] = True

    def fake_show_annotation_window(rect: Rect, screen_idx: int) -> None:
        calls["rect"] = rect
        calls["screen_idx"] = screen_idx

    def fake_single_shot(delay: int, callback) -> None:
        calls["delay"] = delay
        calls["callback"] = callback

    fake_app = SimpleNamespace(
        _close_capture_windows=fake_close_capture_windows,
        _show_annotation_window=fake_show_annotation_window,
    )
    monkeypatch.setattr(app.QtCore.QTimer, "singleShot", staticmethod(fake_single_shot))

    rect = Rect(left=1, top=2, right=3, bottom=4)
    app.PrototypeApp._open_annotation_window(fake_app, rect, 7)

    assert calls["closed"] is True
    assert calls["delay"] == 20

    callback = calls["callback"]
    callback()

    assert calls["rect"] == rect
    assert calls["screen_idx"] == 7


def test_annotation_window_emits_closed_signal(qtbot) -> None:
    image = QtGui.QImage(40, 30, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)

    with qtbot.waitSignal(window.com.on_closed, timeout=1000):
        window.close()


def test_blur_tool_creates_effect_annotation(qtbot) -> None:
    image = QtGui.QImage(80, 60, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("white"))

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.canvas.set_tool(Tool.BLUR)

    qtbot.mousePress(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(10, 10),
    )
    qtbot.mouseMove(window.canvas, pos=QtCore.QPoint(30, 30))
    qtbot.mouseRelease(
        window.canvas,
        QtCore.Qt.MouseButton.LeftButton,
        pos=QtCore.QPoint(30, 30),
    )

    assert isinstance(window.canvas.annotations[-1], EffectAnnotation)
    assert window.canvas.annotations[-1].effect == Tool.BLUR


def test_effect_preview_changes_display_image(qtbot) -> None:
    image = QtGui.QImage(40, 40, QtGui.QImage.Format.Format_ARGB32)
    for y in range(40):
        for x in range(40):
            color = QtGui.QColor("black") if (x + y) % 2 == 0 else QtGui.QColor("white")
            image.setPixelColor(x, y, color)

    window = editor.AnnotationWindow(image)
    qtbot.add_widget(window)
    window.canvas.set_tool(Tool.MOSAIC)
    window.canvas._drag_start = QtCore.QPointF(8, 8)
    window.canvas._drag_end = QtCore.QPointF(24, 24)

    display = window.canvas.display_image()

    assert _changed_pixels(image, display, 8, 8, 24, 24) > 0
