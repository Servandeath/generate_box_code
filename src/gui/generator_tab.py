"""
Вкладка "Генератор": выбор кабинета/сезона/категории -> сразу генерация
и запись в БД за один шаг. Ручного подтверждения нет - что видно в таблице,
то уже реально записано в базу.

Если код-кандидат оказался дублем (после MAX_ATTEMPTS_PER_CODE попыток
подобрать уникальный вариант) - он пропускается безусловно и никогда
не попадает в таблицу/на печать. Такие случаи считаются и показываются
пользователю в итоговом сообщении.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import list_active, get_next_seq, code_exists, add_box_code
from generate_box_code import generate_box_code

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
)

MAX_ATTEMPTS_PER_CODE = 5


class GeneratorTab(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.conn = conn

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Генератор кодов короба</b>"))

        form = QHBoxLayout()
        self.cabinet_combo = QComboBox()
        self.season_combo = QComboBox()
        self.item_combo = QComboBox()
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)

        self.max_seq_spin = QSpinBox()
        self.max_seq_spin.setRange(1, 9999)
        self.max_seq_spin.setValue(300)
        self.max_seq_spin.setToolTip(
            "Максимум кодов на кабинет в сутки. Задайте с запасом на весь день "
            "и не меняйте до его конца - иначе ширина номера (кол-во цифр) "
            "будет отличаться у кодов одного дня."
        )

        form.addWidget(QLabel("Кабинет:"))
        form.addWidget(self.cabinet_combo)
        form.addWidget(QLabel("Сезон:"))
        form.addWidget(self.season_combo)
        form.addWidget(QLabel("Категория:"))
        form.addWidget(self.item_combo)
        form.addWidget(QLabel("Кол-во:"))
        form.addWidget(self.qty_spin)
        form.addWidget(QLabel("Макс. в сутки:"))
        form.addWidget(self.max_seq_spin)
        layout.addLayout(form)

        gen_btn = QPushButton("Сгенерировать и записать в БД")
        gen_btn.clicked.connect(self._generate_and_write)
        layout.addWidget(gen_btn)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Код короба (записан в БД)"])
        layout.addWidget(self.table)

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
        max_seq = self.max_seq_spin.value()

        start_seq = get_next_seq(self.conn, cabinet_id)
        last_seq = start_seq + qty - 1

        if last_seq > max_seq:
            QMessageBox.critical(
                self, "Недостаточно места",
                f"На сегодня для этого кабинета уже использовано номеров до {start_seq - 1}. "
                f"Запрошено ещё {qty}, потребуется до номера {last_seq}, "
                f"а лимит 'Макс. в сутки' сейчас {max_seq}.\n\n"
                f"Увеличьте 'Макс. в сутки' минимум до {last_seq} и повторите.",
            )
            return

        written_codes = []
        skipped_count = 0

        for offset in range(qty):
            seq = start_seq + offset
            code = None
            for _ in range(MAX_ATTEMPTS_PER_CODE):
                try:
                    candidate = generate_box_code(cabinet_code, season_code, item_code, seq, max_seq=max_seq)
                except ValueError as e:
                    QMessageBox.critical(self, "Ошибка генерации", str(e))
                    self._append_written(written_codes)
                    return

                if code_exists(self.conn, candidate):
                    continue  # дубль - пробуем ещё раз, этот кандидат не используется

                try:
                    add_box_code(self.conn, candidate, cabinet_id, season_id, item_id, seq)
                    code = candidate
                    break
                except sqlite3.IntegrityError:
                    # редчайший случай гонки: код заняли между проверкой и записью - пробуем снова
                    continue

            if code is None:
                # не удалось подобрать уникальный код за все попытки - этот seq пропускается безусловно
                skipped_count += 1
                continue

            written_codes.append(code)

        self._append_written(written_codes)

        msg = f"Записано в БД: {len(written_codes)}"
        if skipped_count:
            msg += f"\nПропущено из-за дублей (не напечатаны, не записаны): {skipped_count}"
        QMessageBox.information(self, "Готово", msg)

    def _append_written(self, codes: list[str]):
        start_row = self.table.rowCount()
        self.table.setRowCount(start_row + len(codes))
        for i, code in enumerate(codes):
            self.table.setItem(start_row + i, 0, QTableWidgetItem(code))
