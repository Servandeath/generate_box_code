"""
Генерация уникального кода короба для Wildberries.

Формат: CABINET_dd_MM_YYYY_SEASON_ITEM_RANDOMSEQ
RANDOMSEQ = случайные символы + порядковый номер, без разделителя.

Требования WB к коду:
- длина 6-30 символов
- не начинается с "WB"
- без пробелов
- только латинские буквы, цифры, "-", "_"
- уникальность регистронезависимая (проверяется на уровне БД, не здесь)
"""

import random
import re
import string
from datetime import date

MIN_CODE_LENGTH = 6
MAX_CODE_LENGTH = 30
MIN_RANDOM_CHARS = 3  # минимальный запас энтропии, ниже не опускаемся
SEQ_MIN = 1
DEFAULT_MAX_SEQ = 300

RANDOM_ALPHABET = string.ascii_uppercase + string.digits
_VALID_CHARS_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _random_chars(n: int) -> str:
    return "".join(random.choices(RANDOM_ALPHABET, k=n))


def generate_box_code(
    cabinet: str,
    season: str,
    item: str,
    seq: int,
    max_seq: int = DEFAULT_MAX_SEQ,
    gen_date: date | None = None,
) -> str:
    """
    Собирает код короба по формату:
    CABINET_dd_MM_YYYY_SEASON_ITEM_RANDOMSEQ

    max_seq задаёт верхнюю границу порядкового номера на сутки для
    кабинета; число цифр номера вычисляется как len(str(max_seq))
    и влияет на бюджет случайной части.

    Бросает ValueError, если seq вне диапазона, входные коды содержат
    недопустимые символы, или не остаётся места на случайную часть.
    """
    if max_seq < SEQ_MIN:
        raise ValueError(f"max_seq должен быть >= {SEQ_MIN}, получено {max_seq}")
    if not (SEQ_MIN <= seq <= max_seq):
        raise ValueError(f"seq должен быть в диапазоне {SEQ_MIN}-{max_seq}, получено {seq}")

    for name, value in [("cabinet", cabinet), ("season", season), ("item", item)]:
        if not value or not _VALID_CHARS_RE.match(value):
            raise ValueError(f"{name}='{value}' содержит недопустимые символы")

    gen_date = gen_date or date.today()
    date_part = gen_date.strftime("%d_%m_%Y")  # 10 символов

    seq_digits = len(str(max_seq))
    seq_part = str(seq).zfill(seq_digits)

    fixed_len = len(cabinet) + len(date_part) + len(season) + len(item) + seq_digits + 4  # 4 разделителя "_"
    random_budget = MAX_CODE_LENGTH - fixed_len

    if random_budget < MIN_RANDOM_CHARS:
        raise ValueError(
            f"Не хватает места под случайную часть: доступно {random_budget}, "
            f"минимум {MIN_RANDOM_CHARS}. Сократите cabinet/season/item или max_seq."
        )

    code = f"{cabinet}_{date_part}_{season}_{item}_{_random_chars(random_budget)}{seq_part}"

    if not (MIN_CODE_LENGTH <= len(code) <= MAX_CODE_LENGTH):
        raise ValueError(f"Итоговая длина кода {len(code)} вне диапазона 6-30")
    if code.upper().startswith("WB"):
        raise ValueError("Код не должен начинаться с 'WB'")
    if not _VALID_CHARS_RE.match(code):
        raise ValueError(f"Код содержит недопустимые символы: {code}")

    return code
