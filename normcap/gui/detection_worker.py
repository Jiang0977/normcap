"""Async detection worker used for cloud OCR flows."""

import logging
from collections.abc import Callable

from PySide6 import QtCore

logger = logging.getLogger(__name__)


class Communicate(QtCore.QObject):
    on_detection_finished = QtCore.Signal(object)
    on_detection_failed = QtCore.Signal(str)


class DetectionWorker(QtCore.QRunnable):
    def __init__(self, detect_func: Callable[[], object]) -> None:
        super().__init__()
        self.detect_func = detect_func
        self.com = Communicate()

    @QtCore.Slot()
    def run(self) -> None:
        try:
            results = self.detect_func()
        except Exception as exc:
            logger.exception("Detection worker failed")
            self.com.on_detection_failed.emit(str(exc))
        else:
            self.com.on_detection_finished.emit(results)
