"""
Виджет "Превью и настройки этикетки": живое превью (PIL -> QPixmap),
поля настроек, тестовый код, кнопка тестовой печати, а также именованные
шаблоны настроек (пресеты) - удобно, если нужны разные размеры этикеток
под разные задачи. Превью и блок настроек разделены вертикальным
сплиттером (можно тянуть границу), настройки можно скрыть/показать.
"""

import os
import sys
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from label_render import (
    DEFAULT_LABEL_SETTINGS,
    load_label_settings,
    save_label_settings,
    render_preview_image,
    register_pdf_font,
    make_pdf_one_per_page,
    load_presets,
    save_preset,
    delete_preset,
    list_preset_names,
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QSpinBox, QPushButton, QMessageBox, QFileDialog, QGroupBox,
    QSplitter, QComboBox, QInputDialog, QCheckBox,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

TEST_CODE_DEFAULT = "ALF_19_07_2026_DE_BS_TFNYZY419"


class LabelSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_label_settings()
        self.font_name = register_pdf_font()

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(QLabel("<b>Превью и настройки этикетки</b>"))

        # ---- строка пресетов ----
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Шаблон:"))
        self.preset_combo = QComboBox()
        self._reload_presets_list()
        preset_row.addWidget(self.preset_combo)

        load_preset_btn = QPushButton("Загрузить")
        load_preset_btn.clicked.connect(self._load_preset)
        save_preset_btn = QPushButton("Сохранить как шаблон...")
        save_preset_btn.clicked.connect(self._save_as_preset)
        delete_preset_btn = QPushButton("Удалить шаблон")
        delete_preset_btn.clicked.connect(self._delete_preset)

        preset_row.addWidget(load_preset_btn)
        preset_row.addWidget(save_preset_btn)
        preset_row.addWidget(delete_preset_btn)
        outer_layout.addLayout(preset_row)

        test_row = QHBoxLayout()
        test_row.addWidget(QLabel("Тестовый код:"))
        self.test_code_input = QLineEdit(TEST_CODE_DEFAULT)
        self.test_code_input.textChanged.connect(self.refresh_preview)
        test_row.addWidget(self.test_code_input)
        outer_layout.addLayout(test_row)

        # ---- вертикальный сплиттер: превью сверху, настройки снизу ----
        splitter = QSplitter(Qt.Vertical)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #eeeeee; border: 1px solid #999;")
        self.preview_label.setMinimumHeight(150)
        preview_layout.addWidget(self.preview_label)
        splitter.addWidget(preview_container)

        settings_container = QWidget()
        settings_layout = QVBoxLayout(settings_container)

        toggle_row = QHBoxLayout()
        self.toggle_settings_btn = QPushButton("Скрыть настройки")
        self.toggle_settings_btn.clicked.connect(self._toggle_settings_visible)
        toggle_row.addWidget(self.toggle_settings_btn)
        toggle_row.addStretch()
        settings_layout.addLayout(toggle_row)

        self.settings_group = QGroupBox("Настройки (мм / пт)")
        form = QFormLayout()

        self.spins = {}
        field_defs = [
            ("label_w_mm", "Ширина этикетки, мм", 20, 200),
            ("label_h_mm", "Высота этикетки, мм", 20, 200),
            ("margin_mm", "Отступ от края, мм", 0, 20),
            ("barcode_y", "Штрихкод: отступ снизу, мм", 0, 100),
            ("barcode_h", "Штрихкод: высота, мм", 5, 60),
            ("code_y", "Текст кода: отступ снизу, мм", 0, 100),
            ("code_font_size", "Шрифт кода (базовый), пт", 4, 40),
            ("seq_font_size", "Шрифт номера (крупный), пт", 4, 60),
            ("seq_digits", "Символов номера (крупным)", 1, 10),
            ("min_font_size", "Мин. размер шрифта при сжатии, пт", 4, 20),
        ]
        for key, label, lo, hi in field_defs:
            spin = QSpinBox()
            spin.setRange(lo, hi)
            spin.setValue(int(self.settings.get(key, DEFAULT_LABEL_SETTINGS[key])))
            spin.valueChanged.connect(self._on_setting_changed)
            self.spins[key] = spin
            form.addRow(label, spin)

        self.grid_checkbox = QCheckBox("Показывать сетку на превью")
        self.grid_checkbox.setChecked(bool(self.settings.get("show_grid", 1)))
        self.grid_checkbox.stateChanged.connect(self._on_setting_changed)
        form.addRow(self.grid_checkbox)

        self.settings_group.setLayout(form)
        settings_layout.addWidget(self.settings_group)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self._save_settings)
        print_test_btn = QPushButton("Печать тестовая (1 этикетка)")
        print_test_btn.clicked.connect(self._print_test)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(print_test_btn)
        settings_layout.addLayout(btn_row)
        settings_layout.addStretch()

        splitter.addWidget(settings_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(splitter)

        self.refresh_preview()

    def _on_setting_changed(self):
        for key, spin in self.spins.items():
            self.settings[key] = spin.value()
        self.settings["show_grid"] = 1 if self.grid_checkbox.isChecked() else 0
        self.refresh_preview()

    def _apply_settings_to_form(self):
        for key, spin in self.spins.items():
            spin.blockSignals(True)
            spin.setValue(int(self.settings.get(key, DEFAULT_LABEL_SETTINGS[key])))
            spin.blockSignals(False)
        self.grid_checkbox.blockSignals(True)
        self.grid_checkbox.setChecked(bool(self.settings.get("show_grid", 1)))
        self.grid_checkbox.blockSignals(False)

    def refresh_preview(self):
        code = self.test_code_input.text().strip() or TEST_CODE_DEFAULT
        try:
            img = render_preview_image(code, self.settings, self.font_name, px_per_mm=8)
        except Exception as e:
            self.preview_label.setText(f"Ошибка превью: {e}")
            return

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        self.preview_label.setPixmap(pixmap)

    def _toggle_settings_visible(self):
        visible = self.settings_group.isVisible()
        self.settings_group.setVisible(not visible)
        self.toggle_settings_btn.setText("Показать настройки" if visible else "Скрыть настройки")

    def _save_settings(self):
        save_label_settings(self.settings)
        QMessageBox.information(self, "Готово", "Настройки этикетки сохранены")

    def _reload_presets_list(self):
        self.preset_combo.clear()
        self.preset_combo.addItems(list_preset_names())

    def _save_as_preset(self):
        name, ok = QInputDialog.getText(self, "Сохранить шаблон", "Название шаблона (например '58x40 обувь'):")
        if not ok or not name.strip():
            return
        save_preset(name.strip(), self.settings)
        self._reload_presets_list()
        idx = self.preset_combo.findText(name.strip())
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "Готово", f"Шаблон '{name.strip()}' сохранён")

    def _load_preset(self):
        name = self.preset_combo.currentText()
        if not name:
            QMessageBox.information(self, "Внимание", "Нет сохранённых шаблонов")
            return
        presets = load_presets()
        if name not in presets:
            QMessageBox.warning(self, "Ошибка", "Шаблон не найден")
            return
        self.settings = presets[name].copy()
        self._apply_settings_to_form()
        self.refresh_preview()

    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if not name:
            return
        confirm = QMessageBox.question(self, "Удалить шаблон", f"Удалить шаблон '{name}'?")
        if confirm == QMessageBox.Yes:
            delete_preset(name)
            self._reload_presets_list()

    def _print_test(self):
        code = self.test_code_input.text().strip() or TEST_CODE_DEFAULT
        path, _ = QFileDialog.getSaveFileName(self, "Тестовая печать", "test_label.pdf", "PDF files (*.pdf)")
        if not path:
            return
        try:
            make_pdf_one_per_page([code], path, self.settings, self.font_name)
            QMessageBox.information(self, "Готово", f"Тестовая этикетка сохранена: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
