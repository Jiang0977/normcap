import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from normcap.detection import ocr
from normcap.detection.models import DetectionResult, TextDetector, TextType
from normcap.gui.application import screenshot
from normcap.gui.settings import Settings


def test_debug_language_manager_is_deactivated(qapp):
    assert not qapp._DEBUG_LANGUAGE_MANAGER


@pytest.mark.parametrize(
    ("active", "available", "sanitized"),
    [
        ("eng", ["eng"], ["eng"]),
        (["eng"], ["deu"], ["deu"]),
        (["eng"], ["afr", "eng"], ["eng"]),
        (["eng"], ["afr", "deu"], ["afr"]),
        (["deu", "eng"], ["afr", "deu"], ["deu"]),
        (["afr", "deu", "eng"], ["afr", "ben", "deu"], ["afr", "deu"]),
    ],
)
def test_sanitize_active_language(qapp, monkeypatch, active, available, sanitized):
    monkeypatch.setattr(ocr.tesseract, "get_languages", lambda **kwargs: available)
    settings = Settings(organization="normcap_TEST")
    try:
        settings.setValue("language", active)
        qapp.settings = settings
        qapp.installed_languages = available
        qapp._sanitize_language_setting()
        assert settings.value("language") == sanitized
    finally:
        for k in settings.allKeys():
            settings.remove(k)


def test_update_installed_languages_skips_tesseract_for_baidu(qapp, monkeypatch):
    settings = Settings(organization="normcap_TEST")
    try:
        settings.setValue("ocr-engine", "baidu")
        qapp.settings = settings
        qapp.installed_languages = ["eng"]

        monkeypatch.setattr(
            ocr.tesseract,
            "get_languages",
            lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
        )

        qapp._update_installed_languages()

        assert qapp.installed_languages == []
    finally:
        for k in settings.allKeys():
            settings.remove(k)


@pytest.mark.gui
def test_baidu_engine_detection_copies_to_clipboard(
    monkeypatch, qtbot, qapp, select_region, test_signal
):
    settings = Settings(organization="normcap_TEST")
    try:
        settings.setValue("ocr-engine", "baidu")
        settings.setValue("notification", False)
        qapp.settings = settings

        some_image = QtGui.QImage(1200, 800, QtGui.QImage.Format.Format_RGB32)
        some_image.fill(QtGui.QColor("white"))
        monkeypatch.setattr(
            screenshot,
            "capture",
            lambda: [some_image.copy() for _ in qapp.screens],
        )
        monkeypatch.setattr(
            qapp.tray, "show_completion_icon", test_signal.on_event.emit
        )

        copy_to_clipboard_calls = {}
        monkeypatch.setattr(qapp, "_copy_to_clipboard", copy_to_clipboard_calls.update)
        monkeypatch.setattr(
            ocr.baidu,
            "get_text_from_image",
            lambda **_kwargs: [
                DetectionResult(
                    text="baidu text",
                    text_type=TextType.SINGLE_LINE,
                    detector=TextDetector.OCR_RAW,
                )
            ],
        )

        qapp._show_windows(delay_screenshot=False)
        selection = (QtCore.QPoint(50, 50), QtCore.QPoint(250, 160))

        with qtbot.waitSignal(test_signal.on_event):
            select_region(on=qapp.windows[0], pos=selection)
            qtbot.waitUntil(lambda: copy_to_clipboard_calls != {}, timeout=7000)

        assert copy_to_clipboard_calls == {"text": "baidu text"}
    finally:
        for k in settings.allKeys():
            settings.remove(k)


@pytest.mark.gui
def test_baidu_engine_detection_error_shows_message_box(
    monkeypatch, qtbot, qapp, select_region
):
    settings = Settings(organization="normcap_TEST")
    try:
        settings.setValue("ocr-engine", "baidu")
        settings.setValue("notification", False)
        qapp.settings = settings

        some_image = QtGui.QImage(1200, 800, QtGui.QImage.Format.Format_RGB32)
        some_image.fill(QtGui.QColor("white"))
        monkeypatch.setattr(
            screenshot,
            "capture",
            lambda: [some_image.copy() for _ in qapp.screens],
        )

        message_box_args = []
        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            "critical",
            lambda parent, title, text: message_box_args.extend([title, text]),
        )
        monkeypatch.setattr(
            ocr.baidu,
            "get_text_from_image",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("request failed")),
        )

        qapp._show_windows(delay_screenshot=False)
        selection = (QtCore.QPoint(50, 50), QtCore.QPoint(250, 160))

        select_region(on=qapp.windows[0], pos=selection)
        qtbot.waitUntil(lambda: bool(message_box_args), timeout=7000)

        assert "error" in message_box_args[0].lower()
        assert "request failed" in message_box_args[1].lower()
    finally:
        for k in settings.allKeys():
            settings.remove(k)
