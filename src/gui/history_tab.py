"""
Вкладка "История": все сгенерированные коды коробов с человекочитаемыми
именами кабинета/сезона/категории, новые сверху. Раскладка: слева
компактная таблица (тянется по ширине сплиттером), справа - счётчик,
кнопки и место под будущий поиск/фильтры.

Использует QTableView + QAbstractTableModel вместо QTableWidget -
данные хранятся как обычный питоновский список, отрисовываются только
видимые строки (как в любом лог-вьюере), поэтому тысячи записей не
подвешивают интерфейс.

"Перепечатать выбранный код" - печатает УЖЕ СУЩЕСТВУЮЩИЙ код повторно
(для случая утери/повреждения физической этикетки). Это НЕ создаёт
новый код и не пишет в базу заново - только рендерит тот же код в PDF.
Намеренно нет кнопки "очистить историю" в самом приложении: сброс базы
меняет проверку уникальности задним числом и рискует привести к
повторной печати уже использованного кода на реальном складе. Для
разовой очистки (например перед релизом) используется ручное удаление
файла базы вне приложения, не встроенная функция.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import list_history
from label_render import make_pdf_one_per_page, load_label_settings, register_pdf_font

from openpyxl import Workbook

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QMessageBox, QFileDialog, QHeaderView, QAbstractItemView,
    QSplitter, QScrollArea, QGroupBox,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class HistoryTableModel(QAbstractTableModel):
    COLUMNS = ["Код", "Кабинет", "Сезон", "Категория", "Дата создания"]
    FIELD_KEYS = ["code", "cabinet_name", "season_name", "item_name", "created_at"]

    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def code_at(self, row_index: int) -> str | None:
        if 0 <= row_index < len(self._rows):
            return self._rows[row_index]["code"]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        key = self.FIELD_KEYS[index.column()]
        return row[key]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return str(section + 1)


class HistoryTab(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._pdf_font_name = register_pdf_font()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ---- левая колонка: таблица ----
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.addWidget(QLabel("<b>История сгенерированных кодов</b>"))

        self.model = HistoryTableModel()
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.horizontalHeader().setStretchLastSection(False)
        self.view.setSortingEnabled(False)
        table_layout.addWidget(self.view)

        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setWidget(table_widget)

        # ---- правая колонка: счётчик, кнопки, место под будущий поиск ----
        side_widget = QWidget()
        side_layout = QVBoxLayout(side_widget)

        self.count_label = QLabel("")
        side_layout.addWidget(self.count_label)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        side_layout.addWidget(refresh_btn)

        export_btn = QPushButton("Экспорт всей истории в Excel")
        export_btn.clicked.connect(self._export_excel)
        side_layout.addWidget(export_btn)

        reprint_btn = QPushButton("Перепечатать выбранный код")
        reprint_btn.setToolTip(
            "Печатает уже существующий код повторно - для случая, если\n"
            "физическая этикетка повреждена или потеряна. НЕ создаёт\n"
            "новый код, база не изменяется."
        )
        reprint_btn.clicked.connect(self._reprint_selected)
        side_layout.addWidget(reprint_btn)

        future_group = QGroupBox("Поиск и фильтры (в разработке)")
        future_layout = QVBoxLayout()
        future_layout.addWidget(QLabel("Будет добавлено позже:\nпоиск по коду, фильтр по\nкабинету/сезону/дате, сортировка."))
        future_group.setLayout(future_layout)
        side_layout.addWidget(future_group)

        side_layout.addStretch()

        side_scroll = QScrollArea()
        side_scroll.setWidgetResizable(True)
        side_scroll.setWidget(side_widget)

        splitter.addWidget(table_scroll)
        splitter.addWidget(side_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(splitter)

        self.refresh()

    def refresh(self):
        rows = list_history(self.conn)
        self.model.set_rows(rows)
        self.view.resizeColumnsToContents()
        self.count_label.setText(f"Всего записей: {len(rows)}")

    def _selected_row_index(self) -> int | None:
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()

    def _reprint_selected(self):
        row_index = self._selected_row_index()
        if row_index is None:
            QMessageBox.information(self, "Внимание", "Выберите строку с кодом в таблице слева")
            return

        code = self.model.code_at(row_index)
        if not code:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Перепечатать этикетку", f"{code}_reprint.pdf", "PDF files (*.pdf)")
        if not path:
            return

        try:
            settings = load_label_settings()
            make_pdf_one_per_page([code], path, settings, self._pdf_font_name)
            QMessageBox.information(self, "Готово", f"Этикетка перепечатана: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _export_excel(self):
        rows = list_history(self.conn)
        if not rows:
            QMessageBox.information(self, "Внимание", "История пуста - нечего экспортировать")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Экспорт истории", "history.xlsx", "Excel files (*.xlsx)")
        if not path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "История кодов"
            ws.append(HistoryTableModel.COLUMNS)
            for row in rows:
                ws.append([row["code"], row["cabinet_name"], row["season_name"], row["item_name"], row["created_at"]])
            wb.save(path)
            QMessageBox.information(self, "Готово", f"История сохранена: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
