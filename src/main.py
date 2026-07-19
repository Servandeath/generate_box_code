"""
Точка входа GUI-приложения generate_box_code.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_connection
from gui.reference_tab import ReferenceTab
from gui.generator_tab import GeneratorTab

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("generate_box_code")
        self.resize(800, 550)

        init_db()
        self.conn = get_connection()

        self.tabs = QTabWidget()

        self.generator_tab = GeneratorTab(self.conn)
        self.cabinets_tab = ReferenceTab(self.conn, "cabinets", "Кабинеты", code_len=3)
        self.seasons_tab = ReferenceTab(self.conn, "seasons", "Сезоны", code_len=2)
        self.items_tab = ReferenceTab(self.conn, "item_types", "Категории", code_len=2)

        self.tabs.addTab(self.generator_tab, "Генератор")
        self.tabs.addTab(self.cabinets_tab, "Кабинеты")
        self.tabs.addTab(self.seasons_tab, "Сезоны")
        self.tabs.addTab(self.items_tab, "Категории")

        self.tabs.setCurrentWidget(self.generator_tab)

        # при переключении на "Генератор" обновляем выпадающие списки,
        # чтобы свежедобавленные в справочниках записи сразу были видны
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

    def _on_tab_changed(self, index: int):
        if self.tabs.widget(index) is self.generator_tab:
            self.generator_tab.refresh_lists()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
