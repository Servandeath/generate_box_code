"""
Генерация уникального кода короба для Wildberries.

Формат: CABINET_dd_MM_YYYY_SEASON_ITEM_RANDOMSEQ
RANDOMSEQ = случайные символы + порядковый номер, без разделителя.

Порядковый номер не ограничен сверху - ширина (кол-во цифр) считается
динамически под ТЕКУЩЕЕ значение seq (минимум 3 цифры, растёт по мере
роста номера: 001..999, затем 1000, 1001...).
"""

import random
import re
import string
from datetime import date

MIN_CODE_LENGTH = 6
MAX_CODE_LENGTH = 30
MIN_RANDOM_CHARS = 3
SEQ_MIN = 1
MIN_SEQ_DIGITS = 3  # минимальная ширина номера, даже если seq однозначный (001, не 1)

CABINET_CODE_LEN = 3
SEASON_CODE_LEN = 2
ITEM_CODE_LEN = 2

RANDOM_ALPHABET = string.ascii_uppercase + string.digits
_VALID_CHARS_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _random_chars(n: int) -> str:
    return "".join(random.choices(RANDOM_ALPHABET, k=n))


def generate_box_code(
    cabinet: str,
    season: str,
    item: str,
    seq: int,
    gen_date: date | None = None,
) -> str:
    """
    Собирает код короба по формату:
    CABINET_dd_MM_YYYY_SEASON_ITEM_RANDOMSEQ

    seq не ограничен сверху. Ширина номера = max(MIN_SEQ_DIGITS, len(str(seq))),
    т.е. растёт сама по мере роста номера, не требуя заранее заданного лимита.

    Бросает ValueError, если seq < 1, входные коды содержат недопустимые
    символы, или не остаётся места на случайную часть (например, если
    кабинет/сезон/предмет слишком длинные, либо seq стал настолько большим,
    что съел весь бюджет длины кода).
    """
    if seq < SEQ_MIN:
        raise ValueError(f"seq должен быть >= {SEQ_MIN}, получено {seq}")

    for name, value in [("cabinet", cabinet), ("season", season), ("item", item)]:
        if not value or not _VALID_CHARS_RE.match(value):
            raise ValueError(f"{name}='{value}' содержит недопустимые символы")

    gen_date = gen_date or date.today()
    date_part = gen_date.strftime("%d_%m_%Y")

    seq_digits = max(MIN_SEQ_DIGITS, len(str(seq)))
    seq_part = str(seq).zfill(seq_digits)

    fixed_len = len(cabinet) + len(date_part) + len(season) + len(item) + seq_digits + 4
    random_budget = MAX_CODE_LENGTH - fixed_len

    if random_budget < MIN_RANDOM_CHARS:
        raise ValueError(
            f"Не хватает места под случайную часть: доступно {random_budget}, "
            f"минимум {MIN_RANDOM_CHARS}. Сократите cabinet/season/item, "
            f"либо номер {seq} стал слишком большим для формата."
        )

    code = f"{cabinet}_{date_part}_{season}_{item}_{_random_chars(random_budget)}{seq_part}"

    if not (MIN_CODE_LENGTH <= len(code) <= MAX_CODE_LENGTH):
        raise ValueError(f"Итоговая длина кода {len(code)} вне диапазона 6-30")
    if code.upper().startswith("WB"):
        raise ValueError("Код не должен начинаться с 'WB'")
    if not _VALID_CHARS_RE.match(code):
        raise ValueError(f"Код содержит недопустимые символы: {code}")

    return code
