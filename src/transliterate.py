"""
Транслитерация кириллицы в латиницу для кодов справочников
(cabinets, seasons, item_types).

Логика простая и предсказуемая: побуквенный перевод по стандартной
таблице (упрощённый ГОСТ/бытовой стандарт), без попыток "угадать"
сокращение. Результат обрезается до нужной длины как ПОДСКАЗКА -
окончательное решение и ручную правку делает пользователь в GUI
перед сохранением в справочник.
"""

import re

CYRILLIC_TO_LATIN = {
    "а": "A", "б": "B", "в": "V", "г": "G", "д": "D", "е": "E", "ё": "E",
    "ж": "ZH", "з": "Z", "и": "I", "й": "Y", "к": "K", "л": "L", "м": "M",
    "н": "N", "о": "O", "п": "P", "р": "R", "с": "S", "т": "T", "у": "U",
    "ф": "F", "х": "H", "ц": "TS", "ч": "CH", "ш": "SH", "щ": "SCH",
    "ъ": "", "ы": "Y", "ь": "", "э": "E", "ю": "YU", "я": "YA",
}

_VALID_CHARS_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def transliterate(text: str) -> str:
    """
    Побуквенный перевод кириллицы в латиницу. Не-кириллические символы
    (латиница, цифры) остаются как есть в верхнем регистре; пробелы
    и прочие символы отбрасываются.
    """
    result = []
    for ch in text.strip():
        lower = ch.lower()
        if lower in CYRILLIC_TO_LATIN:
            result.append(CYRILLIC_TO_LATIN[lower])
        elif ch.isalnum():
            result.append(ch.upper())
        # пробелы, дефисы, прочие символы - пропускаем
    return "".join(result)


def suggest_code(text: str, length: int) -> str:
    """
    Предложить код нужной длины: транслитерировать и обрезать.
    Это ПОДСКАЗКА для пользователя, не финальное значение - в GUI
    результат должен быть редактируемым перед сохранением.
    """
    if length < 1:
        raise ValueError(f"length должен быть >= 1, получено {length}")
    full = transliterate(text)
    if not full:
        raise ValueError(f"Не удалось транслитерировать: '{text}'")
    return full[:length]


def is_valid_ref_code(code: str) -> bool:
    """Проверка, что код справочника соответствует алфавиту WB (латиница/цифры/-/_)."""
    return bool(code) and bool(_VALID_CHARS_RE.match(code))
