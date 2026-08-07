"""
Настраиваемые названия разделов справочника (кабинет/сезон/категория).

Разным клиентам подходят разные термины - "Категория" не всегда
удобное слово (может понадобиться "Калибр", "Паллета", "Корабль" и т.д.).
По умолчанию разделы называются нейтрально "Блок 1/2/3" - без привязки
к конкретной терминологии, переименовываются под клиента в вкладке
"Справочники".

Названия хранятся отдельно от самих данных справочника - переименование
не трогает id/code_latin записей, только подписи в интерфейсе.

Поддерживаются именованные шаблоны набора названий (как пресеты
этикетки) - можно сохранить несколько наборов и переключаться между
ними, как в настройках шаблонов МойСклад.
"""

import json
from app_paths import get_app_data_dir

LABELS_FILE = get_app_data_dir() / "dimension_labels.json"
LABEL_PRESETS_FILE = get_app_data_dir() / "dimension_label_presets.json"

DEFAULT_LABELS = {
    "cabinet": "Блок 1",
    "season": "Блок 2",
    "item": "Блок 3",
}


def load_dimension_labels() -> dict:
    labels = DEFAULT_LABELS.copy()
    if LABELS_FILE.exists():
        try:
            with open(LABELS_FILE, "r", encoding="utf-8") as f:
                labels.update(json.load(f))
        except Exception:
            pass
    return labels


def save_dimension_labels(labels: dict) -> None:
    with open(LABELS_FILE, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)


def load_label_presets() -> dict:
    """Вернуть словарь {имя_шаблона: {cabinet, season, item}}."""
    if LABEL_PRESETS_FILE.exists():
        try:
            with open(LABEL_PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_label_preset(name: str, labels: dict) -> None:
    presets = load_label_presets()
    presets[name] = labels
    with open(LABEL_PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def delete_label_preset(name: str) -> None:
    presets = load_label_presets()
    presets.pop(name, None)
    with open(LABEL_PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def list_label_preset_names() -> list[str]:
    return sorted(load_label_presets().keys())
