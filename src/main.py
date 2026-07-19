"""
Точка входа GUI-приложения generate_box_code.
Пока только справочники (кабинеты, сезоны, предметы) - генератор
и этикетка будут отдельными вкладками позже.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_connection
from gui.reference_tab import ReferenceTab

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("generate_box_code")
        self.resize(700, 500)

        init_db()
        self.conn = get_connection()

        tabs = QTabWidget()
        tabs.addTab(ReferenceTab(self.conn, "cabinets", "Кабинеты", code_len=3), "Кабинеты")
        tabs.addTab(ReferenceTab(self.conn, "seasons", "Сезоны", code_len=2), "Сезоны")
        tabs.addTab(ReferenceTab(self.conn, "item_types", "Категории", code_len=2), "Категории")

        self.setCentralWidget(tabs)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
