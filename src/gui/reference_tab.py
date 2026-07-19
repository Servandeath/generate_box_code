"""
Переиспользуемый виджет для CRUD-редактирования одного справочника
(cabinets / seasons / item_types). Используется трижды - по разу
на каждый справочник, с разными table_name и code_len.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import add_reference, deactivate_reference, list_active
from transliterate import suggest_code, is_valid_ref_code

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QAbstractItemView,
)


class ReferenceTab(QWidget):
    def __init__(self, conn: sqlite3.Connection, table_name: str, title: str, code_len: int, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.table_name = table_name
        self.code_len = code_len
        self._row_ids = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{title}</b>"))

        form = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (рус.)")
        self.name_input.textChanged.connect(self._suggest_code)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(f"Код ({code_len} симв.)")
        self.code_input.setMaxLength(10)

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add)

        form.addWidget(self.name_input)
        form.addWidget(self.code_input)
        form.addWidget(add_btn)
        layout.addLayout(form)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Название", "Код"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        deactivate_btn = QPushButton("Отключить выбранное")
        deactivate_btn.clicked.connect(self._deactivate_selected)
        layout.addWidget(deactivate_btn)

        self.refresh()

    def _suggest_code(self, text: str):
        try:
            self.code_input.setText(suggest_code(text, self.code_len))
        except ValueError:
            self.code_input.clear()

    def _add(self):
        name = self.name_input.text().strip()
        code = self.code_input.text().strip().upper()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название")
            return
        if not is_valid_ref_code(code):
            QMessageBox.warning(self, "Ошибка", "Код должен содержать только латинские буквы, цифры, - или _")
            return

        add_reference(self.conn, self.table_name, name, code)
        self.name_input.clear()
        self.code_input.clear()
        self.refresh()

    def _deactivate_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Внимание", "Выберите строку для отключения")
            return
        ref_id = self._row_ids[row]
        deactivate_reference(self.conn, self.table_name, ref_id)
        self.refresh()

    def refresh(self):
        rows = list_active(self.conn, self.table_name)
        self.table.setRowCount(len(rows))
        self._row_ids = []
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(row["name_ru"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["code_latin"]))
            self._row_ids.append(row["id"])
