"""
Вкладка "Генератор": слева - выбор кабинета/сезона/категории (сверху),
настройка даты (под ней), генерация, компактная таблица кодов, экспорт
PDF/Excel. Справа - превью и настройки этикетки (LabelSettingsWidget).

Таблица кодов накапливает ВСЕ коды за сессию (не только последний
пакет) - можно выделить любые строки (Ctrl/Shift+клик) и распечатать
или экспортировать именно выделенное; если ничего не выделено -
используется последний сгенерированный пакет.
"""

import os
import sys
import sqlite3
from datetime import date as date_cls

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import list_active, get_next_seq, code_exists, add_box_code
from generate_box_code import generate_box_code, DATE_FORMATS, DEFAULT_DATE_FORMAT
from label_render import make_pdf_one_per_page, load_label_settings, register_pdf_font
from gui.label_settings_widget import LabelSettingsWidget

from openpyxl import Workbook

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QScrollArea, QSplitter, QHeaderView, QGroupBox, QDateEdit, QCheckBox,
    QAbstractItemView, QFrame,
)
from PySide6.QtCore import Qt, QDate

MAX_ATTEMPTS_PER_CODE = 5

DATE_FORMAT_EXAMPLES = {
    "dd_MM_YYYY": "01_01_2026",
    "dd-MM-YYYY": "01-01-2026",
    "ddMMYY": "010126",
    "YYMMDD": "260101",
    "YYYYMMDD": "20260101",
    "MM_YY": "01_26",
    "MM-YY": "01-26",
    "DMonYY": "1Jan26",
}

CALENDAR_STYLE = """
QCalendarWidget QToolButton {
    color: white;
    background-color: #3a3a3a;
    icon-size: 18px, 18px;
    border-radius: 3px;
}
QCalendarWidget QToolButton:hover {
    background-color: #505050;
}
QCalendarWidget QMenu {
    background-color: #3a3a3a;
    color: white;
}
"""


class GeneratorTab(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn
        self._last_batch = []
        self._pdf_font_name = register_pdf_font()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        main_splitter = QSplitter(Qt.Horizontal)

        # ---- левая колонка ----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # -- блок 1: выбор справочников и количество --
        refs_group = QGroupBox("Генератор кодов короба")
        refs_layout = QVBoxLayout()
        refs_form = QHBoxLayout()
        self.cabinet_combo = QComboBox()
        self.season_combo = QComboBox()
        self.item_combo = QComboBox()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)

        refs_form.addWidget(QLabel("Кабинет:"))
        refs_form.addWidget(self.cabinet_combo)
        refs_form.addWidget(QLabel("Сезон:"))
        refs_form.addWidget(self.season_combo)
        refs_form.addWidget(QLabel("Категория:"))
        refs_form.addWidget(self.item_combo)
        refs_form.addWidget(QLabel("Кол-во:"))
        refs_form.addWidget(self.qty_spin)
        refs_layout.addLayout(refs_form)
        refs_group.setLayout(refs_layout)
        left_layout.addWidget(refs_group)

        # -- блок 2 (ПОД блоком 1): настройка и выбор даты --
        date_group = QGroupBox("Настройка и выбор даты")
        date_layout = QVBoxLayout()
        date_form = QHBoxLayout()

        self.date_format_combo = QComboBox()
        for key in DATE_FORMATS:
            self.date_format_combo.addItem(f"{key} ({DATE_FORMAT_EXAMPLES.get(key, '?')})", key)
        idx = self.date_format_combo.findData(DEFAULT_DATE_FORMAT)
        if idx >= 0:
            self.date_format_combo.setCurrentIndex(idx)
        self.date_format_combo.currentIndexChanged.connect(self._update_date_example)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.calendarWidget().setStyleSheet(CALENDAR_STYLE)
        self.date_edit.dateChanged.connect(self._update_date_example)

        self.no_date_checkbox = QCheckBox("Без даты")
        self.no_date_checkbox.stateChanged.connect(self._on_no_date_toggled)

        date_form.addWidget(QLabel("Формат:"))
        date_form.addWidget(self.date_format_combo)
        date_form.addWidget(QLabel("Дата:"))
        date_form.addWidget(self.date_edit)
        date_form.addWidget(self.no_date_checkbox)
        date_layout.addLayout(date_form)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #555;")
        date_layout.addWidget(separator)

        self.date_example_label = QLabel("")
        self.date_example_label.setStyleSheet(
            "border: 1px solid #666; border-radius: 4px; padding: 4px; background-color: #2a2a2a;"
        )
        date_layout.addWidget(self.date_example_label)

        date_group.setLayout(date_layout)
        left_layout.addWidget(date_group)

        gen_btn = QPushButton("Сгенерировать и записать в БД")
        gen_btn.clicked.connect(self._generate_and_write)
        left_layout.addWidget(gen_btn)

        left_splitter = QSplitter(Qt.Vertical)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.addWidget(QLabel("Сгенерированные коды (выделите строки для печати/экспорта части списка):"))

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Код короба"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table_layout.addWidget(self.table)
        left_splitter.addWidget(table_container)

        export_container = QWidget()
        export_layout = QVBoxLayout(export_container)
        export_row = QHBoxLayout()
        self.pdf_btn = QPushButton("Сохранить PDF")
        self.pdf_btn.setToolTip("Печатает выделенные строки; если ничего не выделено - последний сгенерированный пакет")
        self.pdf_btn.clicked.connect(self._save_pdf)
        self.pdf_btn.setEnabled(False)
        self.excel_btn = QPushButton("Экспорт в Excel")
        self.excel_btn.setToolTip("Экспортирует выделенные строки; если ничего не выделено - последний сгенерированный пакет")
        self.excel_btn.clicked.connect(self._save_excel)
        self.excel_btn.setEnabled(False)
        export_row.addWidget(self.pdf_btn)
        export_row.addWidget(self.excel_btn)
        export_layout.addLayout(export_row)
        export_layout.addStretch()
        left_splitter.addWidget(export_container)

        left_splitter.setStretchFactor(0, 3)
        left_splitter.setStretchFactor(1, 1)

        left_layout.addWidget(left_splitter)

        
        # ---- правая колонка ----
        self.label_settings = LabelSettingsWidget()

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(self.label_settings)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_scroll)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(main_splitter)

        self.refresh_lists()
        self._update_date_example()

    def _on_no_date_toggled(self):
        disabled = self.no_date_checkbox.isChecked()
        self.date_format_combo.setEnabled(not disabled)
        self.date_edit.setEnabled(not disabled)
        self._update_date_example()

    def _update_date_example(self):
        if self.no_date_checkbox.isChecked():
            self.date_example_label.setText("Пример: дата не будет включена в код")
            return
        date_key = self.date_format_combo.currentData()
        qd = self.date_edit.date()
        py_date = date_cls(qd.year(), qd.month(), qd.day())
        try:
            formatted = DATE_FORMATS[date_key](py_date)
            self.date_example_label.setText(f"Пример: ...{formatted}...")
        except Exception:
            self.date_example_label.setText("Пример: -")

    def refresh_lists(self):
        self.cabinet_combo.clear()
        self.season_combo.clear()
        self.item_combo.clear()
        for row in list_active(self.conn, "cabinets"):
            self.cabinet_combo.addItem(f"{row['name_ru']} ({row['code_latin']})", (row["id"], row["code_latin"]))
        for row in list_active(self.conn, "seasons"):
            self.season_combo.addItem(f"{row['name_ru']} ({row['code_latin']})", (row["id"], row["code_latin"]))
        for row in list_active(self.conn, "item_types"):
            self.item_combo.addItem(f"{row['name_ru']} ({row['code_latin']})", (row["id"], row["code_latin"]))

    def _generate_and_write(self):
        if self.cabinet_combo.count() == 0 or self.season_combo.count() == 0 or self.item_combo.count() == 0:
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте записи во все справочники (вкладка Справочники)")
            return

        cabinet_id, cabinet_code = self.cabinet_combo.currentData()
        season_id, season_code = self.season_combo.currentData()
        item_id, item_code = self.item_combo.currentData()
        qty = self.qty_spin.value()

        include_date = not self.no_date_checkbox.isChecked()
        date_format = self.date_format_combo.currentData()
        qd = self.date_edit.date()
        gen_date = date_cls(qd.year(), qd.month(), qd.day())

        start_seq = get_next_seq(self.conn, cabinet_id)

        written_codes = []
        skipped_count = 0

        for offset in range(qty):
            seq = start_seq + offset
            code = None
            for _ in range(MAX_ATTEMPTS_PER_CODE):
                try:
                    candidate = generate_box_code(
                        cabinet_code, season_code, item_code, seq,
                        gen_date=gen_date, include_date=include_date, date_format=date_format,
                    )
                except ValueError as e:
                    QMessageBox.critical(self, "Ошибка генерации", str(e))
                    self._finish_batch(written_codes)
                    return

                if code_exists(self.conn, candidate):
                    continue

                try:
                    add_box_code(self.conn, candidate, cabinet_id, season_id, item_id, seq)
                    code = candidate
                    break
                except sqlite3.IntegrityError:
                    continue

            if code is None:
                skipped_count += 1
                continue

            written_codes.append(code)

        self._finish_batch(written_codes)

        msg = f"Записано в БД: {len(written_codes)}"
        if skipped_count:
            msg += f"\nПропущено из-за дублей (не напечатаны, не записаны): {skipped_count}"
        QMessageBox.information(self, "Готово", msg)

    def _finish_batch(self, codes: list[str]):
        start_row = self.table.rowCount()
        self.table.setRowCount(start_row + len(codes))
        for i, code in enumerate(codes):
            self.table.setItem(start_row + i, 0, QTableWidgetItem(code))
        self.table.resizeColumnsToContents()

        self._last_batch = codes
        # кнопки активны, если в таблице ЕСТЬ строки вообще (не только
        # из последнего пакета) - можно выделить и распечатать любые
        has_rows = self.table.rowCount() > 0
        self.pdf_btn.setEnabled(has_rows)
        self.excel_btn.setEnabled(has_rows)

    def _get_export_codes(self) -> list[str]:
        """Выделенные в таблице строки, если есть выделение; иначе последний пакет."""
        selected_rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if selected_rows:
            return [self.table.item(r, 0).text() for r in selected_rows]
        return self._last_batch

    def _save_pdf(self):
        codes = self._get_export_codes()
        if not codes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить этикетки", "labels.pdf", "PDF files (*.pdf)")
        if not path:
            return
        try:
            settings = load_label_settings()
            make_pdf_one_per_page(codes, path, settings, self._pdf_font_name)
            QMessageBox.information(self, "Готово", f"Этикетки сохранены ({len(codes)} шт.): {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_excel(self):
        codes = self._get_export_codes()
        if not codes:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "codes.xlsx", "Excel files (*.xlsx)")
        if not path:
            return
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Коды коробов"
            for code in codes:
                ws.append([code])
            wb.save(path)
            QMessageBox.information(self, "Готово", f"Excel сохранён ({len(codes)} шт.): {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))



