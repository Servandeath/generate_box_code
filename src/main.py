"""
Точка входа GUI-приложения generate_box_code.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, get_connection
from gui.references_tab import ReferencesTab
from gui.generator_tab import GeneratorTab

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("generate_box_code")
        self.resize(1100, 650)
        self.setMinimumSize(700, 450)

        init_db()
        self.conn = get_connection()

        self.tabs = QTabWidget()

        self.generator_tab = GeneratorTab(self.conn)
        self.references_tab = ReferencesTab(self.conn)

        self.tabs.addTab(self.generator_tab, "Генератор")
        self.tabs.addTab(self.references_tab, "Справочники")

        self.tabs.setCurrentWidget(self.generator_tab)
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
