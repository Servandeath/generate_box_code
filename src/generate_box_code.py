"""
Генерация уникального кода короба для Wildberries.

Формат: CABINET_[DATE_]SEASON_ITEM_RANDOMSEQ
Дата - опциональная часть (include_date=False убирает её из кода
полностью, вместе с разделителем). Формат даты выбирается через
date_format - см. DATE_FORMATS. RANDOMSEQ = случайные символы +
порядковый номер, без разделителя.

Случайная часть НЕ растягивается на весь свободный бюджет длины -
максимум MAX_RANDOM_CHARS символов (по умолчанию 5), даже если
освобождается больше места (например при отключённой дате). Если
доступно меньше MAX_RANDOM_CHARS, но не меньше MIN_RANDOM_CHARS -
используется столько, сколько есть. Итоговый код при этом может
получиться короче 30 символов - это нормально, 30 - верхний предел
формата, а не обязательная цель.

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
MAX_RANDOM_CHARS = 5
SEQ_MIN = 1
MIN_SEQ_DIGITS = 3

CABINET_CODE_LEN = 3
SEASON_CODE_LEN = 2
ITEM_CODE_LEN = 2

RANDOM_ALPHABET = string.ascii_uppercase + string.digits
_VALID_CHARS_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_MONTH_ABBR_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_dmonyy(d: date) -> str:
    return f"{d.day}{_MONTH_ABBR_EN[d.month - 1]}{d.strftime('%y')}"


DATE_FORMATS = {
    "dd_MM_YYYY": lambda d: d.strftime("%d_%m_%Y"),
    "dd-MM-YYYY": lambda d: d.strftime("%d-%m-%Y"),
    "ddMMYY": lambda d: d.strftime("%d%m%y"),
    "YYMMDD": lambda d: d.strftime("%y%m%d"),
    "YYYYMMDD": lambda d: d.strftime("%Y%m%d"),
    "MM_YY": lambda d: d.strftime("%m_%y"),
    "MM-YY": lambda d: d.strftime("%m-%y"),
    "DMonYY": _fmt_dmonyy,
}
DEFAULT_DATE_FORMAT = "dd_MM_YYYY"


def _random_chars(n: int) -> str:
    return "".join(random.choices(RANDOM_ALPHABET, k=n))


def generate_box_code(
    cabinet: str,
    season: str,
    item: str,
    seq: int,
    gen_date: date | None = None,
    include_date: bool = True,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> str:
    """
    Собирает код короба по формату:
    CABINET_[DATE_]SEASON_ITEM_RANDOMSEQ

    Бросает ValueError, если seq < 1, date_format не найден в DATE_FORMATS,
    входные коды содержат недопустимые символы, или не остаётся места
    даже на минимальную случайную часть (MIN_RANDOM_CHARS).
    """
    if seq < SEQ_MIN:
        raise ValueError(f"seq должен быть >= {SEQ_MIN}, получено {seq}")

    for name, value in [("cabinet", cabinet), ("season", season), ("item", item)]:
        if not value or not _VALID_CHARS_RE.match(value):
            raise ValueError(f"{name}='{value}' содержит недопустимые символы")

    if include_date:
        if date_format not in DATE_FORMATS:
            raise ValueError(f"Неизвестный формат даты: '{date_format}'. Доступные: {list(DATE_FORMATS)}")
        gen_date = gen_date or date.today()
        date_part = DATE_FORMATS[date_format](gen_date)
    else:
        date_part = None

    seq_digits = max(MIN_SEQ_DIGITS, len(str(seq)))
    seq_part = str(seq).zfill(seq_digits)

    parts = [cabinet]
    if date_part is not None:
        parts.append(date_part)
    parts.append(season)
    parts.append(item)

    fixed_len = sum(len(p) for p in parts) + len(parts)  # +1 разделитель "_" после каждой части
    fixed_len += seq_digits
    available_budget = MAX_CODE_LENGTH - fixed_len

    if available_budget < MIN_RANDOM_CHARS:
        raise ValueError(
            f"Не хватает места под случайную часть: доступно {available_budget}, "
            f"минимум {MIN_RANDOM_CHARS}. Сократите cabinet/season/item, "
            f"выберите более короткий формат даты, либо номер {seq} стал "
            f"слишком большим для формата."
        )

    # используем не весь доступный бюджет, а минимум из (доступно, MAX_RANDOM_CHARS) -
    # лишний освободившийся бюджет (например при отключённой дате) просто
    # не тратится, код получается короче 30 символов
    random_len = min(available_budget, MAX_RANDOM_CHARS)

    code = "_".join(parts) + f"_{_random_chars(random_len)}{seq_part}"

    if not (MIN_CODE_LENGTH <= len(code) <= MAX_CODE_LENGTH):
        raise ValueError(f"Итоговая длина кода {len(code)} вне диапазона 6-30")
    if code.upper().startswith("WB"):
        raise ValueError("Код не должен начинаться с 'WB'")
    if not _VALID_CHARS_RE.match(code):
        raise ValueError(f"Код содержит недопустимые символы: {code}")

    return code
