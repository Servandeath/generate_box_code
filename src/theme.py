"""
Темы оформления приложения: светлая, тёмная и авто (по системе).

Подход: используем стиль Fusion + QPalette. Fusion уважает палитру,
поэтому смена темы — это подмена палитры у QApplication, а не QSS-
простыни на каждый виджет. Захардкоженные цвета в коде переведены на
роли палитры (base/text/window и т.д.), чтобы следовать теме сами.

Режим хранится в постоянной пользовательской директории (%APPDATA% и
аналоги) рядом с прочими настройками приложения.
"""
import json
import sys

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app_paths import get_app_data_dir

THEME_FILE = get_app_data_dir() / "theme.json"

# три режима: "light" | "dark" | "auto"
DEFAULT_MODE = "auto"
VALID_MODES = ("light", "dark", "auto")


def detect_system_theme() -> str:
    """Определяет тему ОС. Возвращает 'light' или 'dark'.

    Windows: читаем ключ реестра AppsUseLightTheme (0 = тёмная, 1 =
    светлая). На других ОС или при ошибке — безопасный дефолт 'light'.
    """
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception:
            return "light"
    return "light"


def resolve_mode(mode: str) -> str:
    """Приводит режим к конкретной теме: 'auto' -> реальная тема ОС."""
    if mode == "auto":
        return detect_system_theme()
    if mode in ("light", "dark"):
        return mode
    return "light"


def _light_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, QColor(240, 240, 240))
    p.setColor(QPalette.WindowText, QColor(0, 0, 0))
    p.setColor(QPalette.Base, QColor(255, 255, 255))
    p.setColor(QPalette.AlternateBase, QColor(233, 233, 233))
    p.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    p.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    p.setColor(QPalette.Text, QColor(0, 0, 0))
    p.setColor(QPalette.Button, QColor(240, 240, 240))
    p.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    p.setColor(QPalette.BrightText, QColor(255, 0, 0))
    p.setColor(QPalette.Link, QColor(0, 100, 200))
    p.setColor(QPalette.Highlight, QColor(0, 120, 215))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.PlaceholderText, QColor(120, 120, 120))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(150, 150, 150))
    return p


def _dark_palette() -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, QColor(45, 45, 45))
    p.setColor(QPalette.WindowText, QColor(220, 220, 220))
    p.setColor(QPalette.Base, QColor(30, 30, 30))
    p.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    p.setColor(QPalette.ToolTipBase, QColor(45, 45, 45))
    p.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
    p.setColor(QPalette.Text, QColor(220, 220, 220))
    p.setColor(QPalette.Button, QColor(53, 53, 53))
    p.setColor(QPalette.ButtonText, QColor(220, 220, 220))
    p.setColor(QPalette.BrightText, QColor(255, 80, 80))
    p.setColor(QPalette.Link, QColor(80, 160, 240))
    p.setColor(QPalette.Highlight, QColor(0, 120, 215))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.PlaceholderText, QColor(130, 130, 130))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(110, 110, 110))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(110, 110, 110))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(110, 110, 110))
    return p


def apply_theme(app: QApplication, mode: str) -> None:
    """Применяет тему к приложению. mode: 'light' | 'dark' | 'auto'."""
    app.setStyle("Fusion")
    resolved = resolve_mode(mode)
    palette = _dark_palette() if resolved == "dark" else _light_palette()
    app.setPalette(palette)


def load_theme_mode() -> str:
    """Читает сохранённый режим темы. Дефолт — 'auto'."""
    if THEME_FILE.exists():
        try:
            with open(THEME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            mode = data.get("mode", DEFAULT_MODE)
            return mode if mode in VALID_MODES else DEFAULT_MODE
        except Exception:
            return DEFAULT_MODE
    return DEFAULT_MODE


def save_theme_mode(mode: str) -> None:
    """Сохраняет режим темы. Игнорирует некорректные значения."""
    if mode not in VALID_MODES:
        mode = DEFAULT_MODE
    with open(THEME_FILE, "w", encoding="utf-8") as f:
        json.dump({"mode": mode}, f, ensure_ascii=False, indent=2)
