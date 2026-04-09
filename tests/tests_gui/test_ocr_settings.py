from PySide6 import QtWidgets

from normcap.gui import ocr_settings


def test_dialog_loads_values_from_settings(qtbot, temp_settings):
    temp_settings.setValue("ocr-engine", "baidu")
    temp_settings.setValue("baidu-api-key", "key-1")
    temp_settings.setValue("baidu-secret-key", "secret-1")
    temp_settings.setValue("baidu-language-type", "ENG")

    dialog = ocr_settings.OcrSettingsDialog(settings=temp_settings)
    qtbot.addWidget(dialog)

    assert dialog.engine_combo.currentData() == "baidu"
    assert dialog.baidu_api_key_input.text() == "key-1"
    assert dialog.baidu_secret_key_input.text() == "secret-1"
    assert dialog.baidu_language_type_combo.currentText() == "ENG"


def test_secret_key_input_uses_password_echo_mode(qtbot, temp_settings):
    dialog = ocr_settings.OcrSettingsDialog(settings=temp_settings)
    qtbot.addWidget(dialog)

    assert (
        dialog.baidu_secret_key_input.echoMode()
        == QtWidgets.QLineEdit.EchoMode.Password
    )


def test_dialog_save_persists_settings(qtbot, temp_settings):
    dialog = ocr_settings.OcrSettingsDialog(settings=temp_settings)
    qtbot.addWidget(dialog)

    dialog.engine_combo.setCurrentIndex(dialog.engine_combo.findData("baidu"))
    dialog.baidu_api_key_input.setText("api-value")
    dialog.baidu_secret_key_input.setText("secret-value")
    dialog.baidu_language_type_combo.setCurrentText("CHN_ENG")

    dialog.save_button.click()

    assert temp_settings.value("ocr-engine") == "baidu"
    assert temp_settings.value("baidu-api-key") == "api-value"
    assert temp_settings.value("baidu-secret-key") == "secret-value"
    assert temp_settings.value("baidu-language-type") == "CHN_ENG"


def test_dialog_cancel_discards_changes(qtbot, temp_settings):
    temp_settings.setValue("ocr-engine", "tesseract")
    temp_settings.setValue("baidu-api-key", "old-key")
    temp_settings.setValue("baidu-secret-key", "old-secret")
    temp_settings.setValue("baidu-language-type", "CHN_ENG")

    dialog = ocr_settings.OcrSettingsDialog(settings=temp_settings)
    qtbot.addWidget(dialog)

    dialog.engine_combo.setCurrentIndex(dialog.engine_combo.findData("baidu"))
    dialog.baidu_api_key_input.setText("new-key")
    dialog.baidu_secret_key_input.setText("new-secret")
    dialog.baidu_language_type_combo.setCurrentText("ENG")

    dialog.cancel_button.click()

    assert temp_settings.value("ocr-engine") == "tesseract"
    assert temp_settings.value("baidu-api-key") == "old-key"
    assert temp_settings.value("baidu-secret-key") == "old-secret"
    assert temp_settings.value("baidu-language-type") == "CHN_ENG"


def test_baidu_fields_are_disabled_for_tesseract(qtbot, temp_settings):
    temp_settings.setValue("ocr-engine", "tesseract")
    dialog = ocr_settings.OcrSettingsDialog(settings=temp_settings)
    qtbot.addWidget(dialog)

    assert not dialog.baidu_settings_group.isEnabled()

    dialog.engine_combo.setCurrentIndex(dialog.engine_combo.findData("baidu"))
    assert dialog.baidu_settings_group.isEnabled()
