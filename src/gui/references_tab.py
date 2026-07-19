"""
Вкладка "Справочники": кабинеты, сезоны, категории - три колонки рядом
(вместо трёх отдельных вкладок). Каждая мало весит по количеству полей,
объединять в одну вкладку с горизонтальным сплиттером логичнее.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from gui.reference_tab import ReferenceTab

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea
from PySide6.QtCore import Qt


class ReferencesTab(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        self.cabinets_tab = ReferenceTab(conn, "cabinets", "Кабинеты", code_len=3)
        self.seasons_tab = ReferenceTab(conn, "seasons", "Сезоны", code_len=2)
        self.items_tab = ReferenceTab(conn, "item_types", "Категории", code_len=2)

        for widget in (self.cabinets_tab, self.seasons_tab, self.items_tab):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            splitter.addWidget(scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)

        layout.addWidget(splitter)

    def refresh_all(self):
        self.cabinets_tab.refresh()
        self.seasons_tab.refresh()
        self.items_tab.refresh()
