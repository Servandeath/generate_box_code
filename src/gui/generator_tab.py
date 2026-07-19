"""
Вкладка "Генератор": слева - выбор кабинета/сезона/категории, генерация,
таблица кодов (столбец по ширине содержимого, сам блок регулируется
перетаскиванием сплиттера - и по ширине, и по высоте), экспорт PDF/Excel.
Справа - превью и настройки этикетки (LabelSettingsWidget).
Обе колонки внутри QScrollArea - при уменьшении окна появляются
скроллбары вместо расползания раскладки.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import list_active, get_next_seq, code_exists, add_box_code
from generate_box_code import generate_box_code
from label_render import make_pdf_one_per_page, load_label_settings, register_pdf_font
from gui.label_settings_widget import LabelSettingsWidget

from openpyxl import Workbook

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog,
    QScrollArea, QSplitter, QHeaderView,
)
from PySide6.QtCore import Qt

MAX_ATTEMPTS_PER_CODE = 5


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
        left_layout.addWidget(QLabel("<b>Генератор кодов короба</b>"))

        form = QHBoxLayout()
        self.cabinet_combo = QComboBox()
        self.season_combo = QComboBox()
        self.item_combo = QComboBox()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)

        form.addWidget(QLabel("Кабинет:"))
        form.addWidget(self.cabinet_combo)
        form.addWidget(QLabel("Сезон:"))
        form.addWidget(self.season_combo)
        form.addWidget(QLabel("Категория:"))
        form.addWidget(self.item_combo)
        form.addWidget(QLabel("Кол-во:"))
        form.addWidget(self.qty_spin)
        left_layout.addLayout(form)

        gen_btn = QPushButton("Сгенерировать и записать в БД")
        gen_btn.clicked.connect(self._generate_and_write)
        left_layout.addWidget(gen_btn)

        # таблица + кнопки экспорта - в вертикальном сплиттере, чтобы
        # блок можно было тянуть и по высоте (перетаскиванием), и по
        # ширине (перетаскиванием главного горизонтального сплиттера)
        left_splitter = QSplitter(Qt.Vertical)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.addWidget(QLabel("Сгенерированные коды:"))

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Код короба"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(False)
        table_layout.addWidget(self.table)
        left_splitter.addWidget(table_container)

        export_container = QWidget()
        export_layout = QVBoxLayout(export_container)
        export_row = QHBoxLayout()
        self.pdf_btn = QPushButton("Сохранить этикетки PDF (последний пакет)")
        self.pdf_btn.clicked.connect(self._save_pdf)
        self.pdf_btn.setEnabled(False)
        self.excel_btn = QPushButton("Экспорт в Excel (последний пакет)")
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

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_widget)

        # ---- правая колонка ----
        self.label_settings = LabelSettingsWidget()

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(self.label_settings)

        main_splitter.addWidget(left_scroll)
        main_splitter.addWidget(right_scroll)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(main_splitter)

        self.refresh_lists()

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
            QMessageBox.warning(self, "Ошибка", "Сначала добавьте записи во все справочники (вкладки выше)")
            return

        cabinet_id, cabinet_code = self.cabinet_combo.currentData()
        season_id, season_code = self.season_combo.currentData()
        item_id, item_code = self.item_combo.currentData()
        qty = self.qty_spin.value()

        start_seq = get_next_seq(self.conn, cabinet_id)

        written_codes = []
        skipped_count = 0

        for offset in range(qty):
            seq = start_seq + offset
            code = None
            for _ in range(MAX_ATTEMPTS_PER_CODE):
                try:
                    candidate = generate_box_code(cabinet_code, season_code, item_code, seq)
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
        has_batch = len(codes) > 0
        self.pdf_btn.setEnabled(has_batch)
        self.excel_btn.setEnabled(has_batch)

    def _save_pdf(self):
        if not self._last_batch:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить этикетки", "labels.pdf", "PDF files (*.pdf)")
        if not path:
            return
        try:
            settings = load_label_settings()
            make_pdf_one_per_page(self._last_batch, path, settings, self._pdf_font_name)
            QMessageBox.information(self, "Готово", f"Этикетки сохранены: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_excel(self):
        if not self._last_batch:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в Excel", "codes.xlsx", "Excel files (*.xlsx)")
        if not path:
            return
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Коды коробов"
            for code in self._last_batch:
                ws.append([code])
            wb.save(path)
            QMessageBox.information(self, "Готово", f"Excel сохранён: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
