from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from PySide6 import QtWidgets

from normcap.positioning import main
from normcap.positioning.handlers import qt_screen
from normcap.positioning.models import Handler
from normcap.system.models import Screen


def test_get_available_handlers_prefers_qt_screen_on_gnome_wayland(
    monkeypatch,
) -> None:
    monkeypatch.setattr(main.qt_screen, "is_compatible", lambda: True)
    monkeypatch.setattr(main.qt_screen, "is_installed", lambda: True)
    monkeypatch.setattr(main.window_calls, "is_compatible", lambda: True)
    monkeypatch.setattr(main.window_calls, "is_installed", lambda: False)
    monkeypatch.setattr(main.kscript, "is_compatible", lambda: False)
    monkeypatch.setattr(main.kscript, "is_installed", lambda: False)

    assert main.get_available_handlers() == [Handler.QT_SCREEN]


def test_qt_screen_move_assigns_target_qscreen(monkeypatch) -> None:
    assigned: dict[str, object] = {}

    class FakeHandle:
        def setScreen(self, screen: object) -> None:  # noqa: N802
            assigned["screen"] = screen

    class FakeWindow:
        def __init__(self) -> None:
            self.handle = FakeHandle()
            self.fullscreen_called = False
            self.focus_called = False

        def windowHandle(self) -> FakeHandle:  # noqa: N802
            return self.handle

        def showFullScreen(self) -> None:  # noqa: N802
            self.fullscreen_called = True

        def set_focus(self) -> None:
            self.focus_called = True

        setFocus = set_focus  # noqa: N815

        def windowTitle(self) -> str:  # noqa: N802
            return "test-window"

    target = SimpleNamespace(name=lambda: "HDMI-1")
    monkeypatch.setattr(
        QtWidgets.QApplication,
        "screens",
        staticmethod(lambda: [target]),
    )

    window = FakeWindow()
    screen = Screen(
        left=0,
        top=0,
        right=1919,
        bottom=1079,
        device_pixel_ratio=1,
        index=0,
    )

    qt_screen.move(window=cast(QtWidgets.QMainWindow, window), screen=screen)

    assert assigned["screen"] is target
    assert window.fullscreen_called is True
    assert window.focus_called is True
