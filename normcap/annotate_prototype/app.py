"""Standalone annotation prototype entrypoint."""

from __future__ import annotations

import logging
import signal
import sys

from PySide6 import QtCore, QtWidgets

from normcap import app_id
from normcap.annotate_prototype.editor import AnnotationWindow
from normcap.gui import utils as gui_utils
from normcap.gui.settings import Settings
from normcap.gui.window import Window
from normcap.logger_config import prepare_logging
from normcap.screenshot import capture
from normcap.system import info
from normcap.system.models import Rect, Screen

logger = logging.getLogger(__name__)


class PrototypeApp(QtWidgets.QApplication):
    """Small app reusing NormCap's capture/selection stack for annotation."""

    def __init__(self) -> None:
        super().__init__([])
        self.setQuitOnLastWindowClosed(False)
        self.setApplicationName(f"{app_id}.annotate_prototype")
        self.setDesktopFileName(app_id)

        self.settings = Settings(
            organization="normcap",
            application="annotate_prototype",
            init_settings={
                "parse-text": False,
                "tray": False,
                "notification": False,
                "update": False,
                "show-introduction": False,
            },
        )
        self.screens: list[Screen] = info.screens()
        self.windows: dict[int, Window] = {}
        self.annotation_window: AnnotationWindow | None = None

        self._show_capture_windows()

    def _show_capture_windows(self) -> None:
        screenshots = capture()
        if not screenshots:
            raise RuntimeError("No screenshot could be captured.")

        for idx, image in enumerate(screenshots):
            self.screens[idx].screenshot = image

        for index in range(len(self.screens)):
            self._create_window(index)

    def _create_window(self, index: int) -> None:
        window = Window(
            screen=self.screens[index],
            index=index,
            settings=self.settings,
            installed_languages=[],
        )
        if window.menu_button is not None:
            window.menu_button.hide()

        window.com.on_esc_key_pressed.connect(self._cancel_capture)
        window.com.on_region_selected.connect(self._open_annotation_window)
        window.set_fullscreen()
        self.windows[index] = window

    def _close_capture_windows(self) -> None:
        for window in self.windows.values():
            window.close()
            self.processEvents()
        self.windows = {}

    def _cancel_capture(self) -> None:
        self._close_capture_windows()
        self.quit()

    def _open_annotation_window(self, rect: Rect, screen_idx: int) -> None:
        self._close_capture_windows()
        logger.info(
            "Schedule annotation window for region %s on screen %s",
            rect.coords,
            screen_idx,
        )
        QtCore.QTimer.singleShot(
            20, lambda: self._show_annotation_window(rect, screen_idx)
        )

    def _show_annotation_window(self, rect: Rect, screen_idx: int) -> None:
        screenshot = self.screens[screen_idx].screenshot
        cropped = gui_utils.crop_image(image=screenshot, rect=rect)
        if cropped.isNull():
            self.quit()
            return

        self.annotation_window = AnnotationWindow(cropped)
        self.annotation_window.com.on_closed.connect(self.quit)
        self.annotation_window.destroyed.connect(
            lambda *_: setattr(self, "annotation_window", None)
        )
        self.annotation_window.show()
        QtCore.QTimer.singleShot(0, self._focus_annotation_window)

    def _focus_annotation_window(self) -> None:
        if self.annotation_window is None:
            return

        self.annotation_window.raise_()
        self.annotation_window.activateWindow()


def run() -> int:
    """Run the standalone screenshot annotation prototype."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    prepare_logging(log_level="INFO")

    app = PrototypeApp()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
