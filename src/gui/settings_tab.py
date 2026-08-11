"""
Вкладка "Настройки": параметры приложения.

Сейчас — выбор темы оформления (Светлая / Тёмная / Авто по системе).
При смене темы вкладка сохраняет выбор и испускает сигнал theme_changed,
чтобы MainWindow применил тему живьём (без перезапуска).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QRadioButton, QButtonGroup, QLabel,
)
from PySide6.QtCore import Signal

from theme import load_theme_mode, save_theme_mode


class SettingsTab(QWidget):
    # наружу отдаём выбранный режим: "light" | "dark" | "auto"
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)

        theme_group = QGroupBox("Тема оформления")
        theme_layout = QVBoxLayout()

        self.radio_light = QRadioButton("Светлая")
        self.radio_dark = QRadioButton("Тёмная")
        self.radio_auto = QRadioButton("Авто (по системе)")

        hint = QLabel(
            "«Авто» подбирает светлую или тёмную тему в зависимости от "
            "текущей темы Windows."
        )
        hint.setWordWrap(True)

        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.radio_light)
        self.button_group.addButton(self.radio_dark)
        self.button_group.addButton(self.radio_auto)

        theme_layout.addWidget(self.radio_light)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addWidget(self.radio_auto)
        theme_layout.addWidget(hint)
        theme_group.setLayout(theme_layout)

        outer.addWidget(theme_group)
        outer.addStretch()

        # выставляем текущий сохранённый режим без вызова обработчика
        current = load_theme_mode()
        self._set_checked_for_mode(current)

        # подключаем обработчики ПОСЛЕ начальной установки
        self.radio_light.toggled.connect(self._on_toggled)
        self.radio_dark.toggled.connect(self._on_toggled)
        self.radio_auto.toggled.connect(self._on_toggled)

    def _set_checked_for_mode(self, mode: str):
        if mode == "dark":
            self.radio_dark.setChecked(True)
        elif mode == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_auto.setChecked(True)

    def _current_mode(self) -> str:
        if self.radio_dark.isChecked():
            return "dark"
        if self.radio_light.isChecked():
            return "light"
        return "auto"

    def _on_toggled(self, checked: bool):
        # toggled срабатывает и на снятие — реагируем только на включение
        if not checked:
            return
        mode = self._current_mode()
        save_theme_mode(mode)
        self.theme_changed.emit(mode)
