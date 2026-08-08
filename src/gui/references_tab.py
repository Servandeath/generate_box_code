"""
Вкладка "Справочники": кабинеты, сезоны, категории - три колонки рядом.

Сверху - блок переименования разделов (кабинет/сезон/категория ->
произвольные названия под клиента, например "Корабль"/"Калибр"/
"Паллета"), с именованными шаблонами набора названий (сохранить/
загрузить/удалить, как шаблоны в МойСклад). Переименование применяется
СРАЗУ (без перезапуска) - и в этой вкладке, и в остальных (через
сигнал labels_changed, на который подписывается MainWindow).
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.reference_tab import ReferenceTab
from dimension_labels import (
    load_dimension_labels,
    save_dimension_labels,
    load_label_presets,
    save_label_preset,
    delete_label_preset,
    list_label_preset_names,
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QScrollArea,
    QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal


class ReferencesTab(QWidget):
    labels_changed = Signal(dict)

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- блок переименования разделов ----
        rename_group = QGroupBox("Названия разделов")
        rename_layout = QVBoxLayout()

        current_labels = load_dimension_labels()

        rename_form = QHBoxLayout()
        rename_form.addWidget(QLabel("Кабинет:"))
        self.cabinet_name_edit = QLineEdit(current_labels["cabinet"])
        rename_form.addWidget(self.cabinet_name_edit)

        rename_form.addWidget(QLabel("Сезон:"))
        self.season_name_edit = QLineEdit(current_labels["season"])
        rename_form.addWidget(self.season_name_edit)

        rename_form.addWidget(QLabel("Категория:"))
        self.item_name_edit = QLineEdit(current_labels["item"])
        rename_form.addWidget(self.item_name_edit)

        save_names_btn = QPushButton("Сохранить названия")
        save_names_btn.clicked.connect(self._save_names)
        rename_form.addWidget(save_names_btn)
        rename_form.addStretch()
        rename_layout.addLayout(rename_form)

        preset_form = QHBoxLayout()
        preset_form.addWidget(QLabel("Шаблон названий:"))
        self.preset_combo = QComboBox()
        self._reload_presets_list()
        preset_form.addWidget(self.preset_combo)

        load_preset_btn = QPushButton("Загрузить")
        load_preset_btn.clicked.connect(self._load_preset)
        save_preset_btn = QPushButton("Сохранить как шаблон...")
        save_preset_btn.clicked.connect(self._save_as_preset)
        delete_preset_btn = QPushButton("Удалить шаблон")
        delete_preset_btn.clicked.connect(self._delete_preset)

        preset_form.addWidget(load_preset_btn)
        preset_form.addWidget(save_preset_btn)
        preset_form.addWidget(delete_preset_btn)
        preset_form.addStretch()
        rename_layout.addLayout(preset_form)

        rename_layout.addStretch()
        rename_group.setLayout(rename_layout)
        layout.addWidget(rename_group)

        # ---- три колонки справочников ----
        splitter = QSplitter(Qt.Horizontal)

        self.cabinets_tab = ReferenceTab(conn, "cabinets", current_labels["cabinet"], code_len=3)
        self.seasons_tab = ReferenceTab(conn, "seasons", current_labels["season"], code_len=2)
        self.items_tab = ReferenceTab(conn, "item_types", current_labels["item"], code_len=2)

        for widget in (self.cabinets_tab, self.seasons_tab, self.items_tab):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)

        layout.addWidget(splitter, 1)

    def refresh_all(self):
        self.cabinets_tab.refresh()
        self.seasons_tab.refresh()
        self.items_tab.refresh()

    def _current_labels_from_form(self) -> dict:
        return {
            "cabinet": self.cabinet_name_edit.text().strip() or "Кабинет",
            "season": self.season_name_edit.text().strip() or "Сезон",
            "item": self.item_name_edit.text().strip() or "Категория",
        }

    def _apply_labels(self, labels: dict):
        self.cabinet_name_edit.setText(labels["cabinet"])
        self.season_name_edit.setText(labels["season"])
        self.item_name_edit.setText(labels["item"])

        self.cabinets_tab.set_title(labels["cabinet"])
        self.seasons_tab.set_title(labels["season"])
        self.items_tab.set_title(labels["item"])

        save_dimension_labels(labels)
        self.labels_changed.emit(labels)

    def _save_names(self):
        labels = self._current_labels_from_form()
        self._apply_labels(labels)
        QMessageBox.information(self, "Готово", "Названия разделов обновлены")

    def _reload_presets_list(self):
        self.preset_combo.clear()
        self.preset_combo.addItems(list_label_preset_names())

    def _save_as_preset(self):
        name, ok = QInputDialog.getText(self, "Сохранить шаблон названий", "Название шаблона (например 'Обувь - калибры'):")
        if not ok or not name.strip():
            return
        labels = self._current_labels_from_form()
        save_label_preset(name.strip(), labels)
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
        presets = load_label_presets()
        if name not in presets:
            QMessageBox.warning(self, "Ошибка", "Шаблон не найден")
            return
        self._apply_labels(presets[name])

    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if not name:
            return
        confirm = QMessageBox.question(self, "Удалить шаблон", f"Удалить шаблон '{name}'?")
        if confirm == QMessageBox.Yes:
            delete_label_preset(name)
            self._reload_presets_list()


