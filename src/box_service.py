"""
Сервисный слой: соединяет generate_box_code, db и transliterate
в единый сценарий "сгенерировать код короба и записать в БД".

Это и есть точка входа, которую использует GUI на PySide6.
"""

import sqlite3

from generate_box_code import generate_box_code
from db import add_box_code, code_exists

MAX_GENERATION_ATTEMPTS = 5


def create_box_code(
    conn: sqlite3.Connection,
    cabinet_id: int,
    cabinet_code: str,
    season_id: int,
    season_code: str,
    item_id: int,
    item_code: str,
    seq: int,
) -> str:
    """
    Сгенерировать код короба и записать в историю (box_codes).

    При случайной коллизии (сгенерированный код уже существует в БД)
    делается повторная попытка - вероятность крайне низкая при
    достаточном random_budget, но проверка обязательна: WB требует
    гарантированной уникальности.

    Бросает RuntimeError, если за MAX_GENERATION_ATTEMPTS попыток
    не удалось получить уникальный код.
    """
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        code = generate_box_code(cabinet_code, season_code, item_code, seq)
        if not code_exists(conn, code):
            add_box_code(conn, code, cabinet_id, season_id, item_id, seq)
            return code

    raise RuntimeError(
        f"Не удалось сгенерировать уникальный код за {MAX_GENERATION_ATTEMPTS} попыток."
    )
