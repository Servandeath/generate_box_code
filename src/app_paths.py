"""
пределение постоянной директории для пользовательских данных приложения.

 про PyInstaller --onefile: при запуске собранного .exe приложение
распаковывается во  папку (sys._MEIPASS), которая создаётся
заново при каждом запуске. сли хранить базу/настройки "рядом с кодом"
(как это удобно при разработке), то в собранной версии они будут
создаваться в новой временной папке при каждом старте и теряться при
следующем запуске - именно поэтому справочники "терялись" в .exe.

ешение: при запуске из СХ (python src/main.py) - данные рядом
с кодом, как раньше. ри запуске С .exe - данные в постоянной
пользовательской директории (%APPDATA% на Windows и аналоги на других С).
"""

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True, если код выполняется как собранный PyInstaller .exe."""
    return getattr(sys, "frozen", False)


def get_app_data_dir() -> Path:
    """
    остоянная директория для базы данных и файлов настроек.
    Создаётся при первом обращении, если ещё не существует.
    """
    if not is_frozen():
        # азработка из исходников - поведение как раньше, рядом с src/
        return Path(__file__).parent

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    app_dir = base / "generate_box_code"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir
