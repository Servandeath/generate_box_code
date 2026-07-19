"""
Сервисный слой: соединяет generate_box_code, db и transliterate
в единый сценарий "сгенерировать код короба и записать в БД".

Это и есть точка входа, которую будет использовать GUI на PySide6.
"""

import sqlite3

from generate_box_code import generate_box_code, DEFAULT_MAX_SEQ
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
    max_seq: int = DEFAULT_MAX_SEQ,
) -> str:
    """
    Сгенерировать код короба и записать в историю (box_codes).

    Коды справочников (cabinet_code/season_code/item_code) передаются
    отдельно от id, потому что генерация не должна знать про SQL -
    GUI достаёт code_latin из справочника и передаёт сюда как строку.

    При случайной коллизии (сгенерированный код уже существует в БД)
    делается повторная попытка - вероятность крайне низкая при
    достаточном random_budget, но проверка обязательна: WB требует
    гарантированной уникальности.

    Бросает RuntimeError, если за MAX_GENERATION_ATTEMPTS попыток
    не удалось получить уникальный код (сигнал, что random_budget
    слишком мал для реального объёма генерации).
    """
    for attempt in range(MAX_GENERATION_ATTEMPTS):
        code = generate_box_code(cabinet_code, season_code, item_code, seq, max_seq=max_seq)
        if not code_exists(conn, code):
            add_box_code(conn, code, cabinet_id, season_id, item_id, seq)
            return code

    raise RuntimeError(
        f"Не удалось сгенерировать уникальный код за {MAX_GENERATION_ATTEMPTS} попыток. "
        f"Возможно, random_budget слишком мал для текущего объёма генерации."
    )
