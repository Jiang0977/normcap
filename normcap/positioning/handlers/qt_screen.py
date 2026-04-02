"""Position windows on GNOME Wayland using Qt's native screen assignment."""

from __future__ import annotations

import logging

from PySide6 import QtWidgets

from normcap.system import info
from normcap.system.models import DesktopEnvironment, Screen

logger = logging.getLogger(__name__)

install_instructions = ""


def is_compatible() -> bool:
    """Check if the current system can use Qt-native screen assignment."""
    return (
        info.desktop_environment() == DesktopEnvironment.GNOME
        and info.display_manager_is_wayland()
    )


def is_installed() -> bool:
    """Qt-native screen assignment has no external runtime dependency."""
    return True


def move(window: QtWidgets.QMainWindow, screen: Screen) -> None:
    """Move a visible window to the target screen using Qt's native API."""
    handle = window.windowHandle()
    if handle is None:
        raise RuntimeError("Window handle is unavailable.")

    screens = QtWidgets.QApplication.screens()
    if screen.index >= len(screens):
        raise RuntimeError(
            "Target screen index "
            f"{screen.index} out of range for {len(screens)} screens."
        )

    target_screen = screens[screen.index]
    logger.debug(
        "Moving window '%s' to screen '%s' via Qt",
        window.windowTitle(),
        target_screen.name(),
    )

    handle.setScreen(target_screen)
    window.showFullScreen()
    window.setFocus()
