"""Dialog for OCR backend specific settings."""

from PySide6 import QtCore, QtWidgets

from normcap.gui.constants import BAIDU_LANGUAGE_TYPES, OCR_ENGINES
from normcap.gui.localization import _


class OcrSettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        settings: QtCore.QSettings,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent)
        self.settings = settings

        self.setModal(True)
        self.setWindowTitle(_("OCR Settings"))
        self.setMinimumWidth(520)

        self.engine_combo = QtWidgets.QComboBox()
        for value, label in OCR_ENGINES:
            self.engine_combo.addItem(label, userData=value)
        self.engine_combo.currentIndexChanged.connect(self._apply_engine_state)

        self.baidu_settings_group = QtWidgets.QGroupBox(_("Baidu OCR"))

        self.baidu_api_key_input = QtWidgets.QLineEdit()
        self.baidu_secret_key_input = QtWidgets.QLineEdit()
        self.baidu_secret_key_input.setEchoMode(
            QtWidgets.QLineEdit.EchoMode.Password
        )
        self.baidu_language_type_combo = QtWidgets.QComboBox()
        self.baidu_language_type_combo.setEditable(True)
        self.baidu_language_type_combo.addItems(BAIDU_LANGUAGE_TYPES)

        baidu_form = QtWidgets.QFormLayout()
        baidu_form.addRow(_("API Key"), self.baidu_api_key_input)
        baidu_form.addRow(_("Secret Key"), self.baidu_secret_key_input)
        baidu_form.addRow(_("Language Type"), self.baidu_language_type_combo)
        self.baidu_settings_group.setLayout(baidu_form)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save_and_accept)
        button_box.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()
        form.addRow(_("OCR Engine"), self.engine_combo)
        layout.addLayout(form)
        layout.addWidget(self.baidu_settings_group)
        layout.addWidget(button_box)
        self.setLayout(layout)

        self._load_settings()

    def _load_settings(self) -> None:
        engine = str(self.settings.value("ocr-engine", "tesseract"))
        index = self.engine_combo.findData(engine)
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)

        self.baidu_api_key_input.setText(
            str(self.settings.value("baidu-api-key", ""))
        )
        self.baidu_secret_key_input.setText(
            str(self.settings.value("baidu-secret-key", ""))
        )

        language_type = str(self.settings.value("baidu-language-type", "CHN_ENG"))
        index = self.baidu_language_type_combo.findText(language_type)
        if index >= 0:
            self.baidu_language_type_combo.setCurrentIndex(index)
        else:
            self.baidu_language_type_combo.setCurrentText(language_type)

        self._apply_engine_state()

    @QtCore.Slot()
    def _apply_engine_state(self) -> None:
        is_baidu = self.engine_combo.currentData() == "baidu"
        self.baidu_settings_group.setEnabled(is_baidu)

    @QtCore.Slot()
    def _save_and_accept(self) -> None:
        self.settings.setValue("ocr-engine", self.engine_combo.currentData())
        self.settings.setValue("baidu-api-key", self.baidu_api_key_input.text().strip())
        self.settings.setValue(
            "baidu-secret-key", self.baidu_secret_key_input.text().strip()
        )
        self.settings.setValue(
            "baidu-language-type",
            self.baidu_language_type_combo.currentText().strip() or "CHN_ENG",
        )
        self.accept()
