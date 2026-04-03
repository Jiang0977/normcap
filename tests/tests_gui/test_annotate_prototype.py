from __future__ import annotations

from types import SimpleNamespace

from PySide6 import QtGui

from normcap.annotate_prototype import app, editor
from normcap.system.models import Rect


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
