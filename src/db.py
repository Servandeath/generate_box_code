"""
Слой доступа к SQLite для generate_box_code.

Таблицы:
- cabinets, seasons, item_types - редактируемые справочники с полями
  name_ru (человекочитаемое имя) и code_latin (код для генератора кода короба).
  is_active - мягкое отключение (не удаляем физически, чтобы не терять историю).
- box_codes - история сгенерированных кодов коробов. code уникален
  регистронезависимо (COLLATE NOCASE) - это и есть проверка уникальности
  из требований WB (AbCdEfG = abcdefg).
"""

import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).with_name("box_codes.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cabinets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ru TEXT NOT NULL,
    code_latin TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ru TEXT NOT NULL,
    code_latin TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS item_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ru TEXT NOT NULL,
    code_latin TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS box_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    cabinet_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    seq INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cabinet_id) REFERENCES cabinets(id),
    FOREIGN KEY (season_id) REFERENCES seasons(id),
    FOREIGN KEY (item_id) REFERENCES item_types(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_box_codes_code_nocase
    ON box_codes (code COLLATE NOCASE);
"""


def get_connection(db_path: Path | str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DB_FILE) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def add_reference(
    conn: sqlite3.Connection,
    table: str,
    name_ru: str,
    code_latin: str,
) -> int:
    """Добавить запись в справочник (cabinets/seasons/item_types). Возвращает id."""
    if table not in ("cabinets", "seasons", "item_types"):
        raise ValueError(f"Неизвестная таблица справочника: {table}")
    cur = conn.execute(
        f"INSERT INTO {table} (name_ru, code_latin) VALUES (?, ?)",
        (name_ru, code_latin),
    )
    conn.commit()
    return cur.lastrowid


def deactivate_reference(conn: sqlite3.Connection, table: str, ref_id: int) -> None:
    """Мягкое отключение записи справочника (is_active = 0), история не теряется."""
    if table not in ("cabinets", "seasons", "item_types"):
        raise ValueError(f"Неизвестная таблица справочника: {table}")
    conn.execute(f"UPDATE {table} SET is_active = 0 WHERE id = ?", (ref_id,))
    conn.commit()


def list_active(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    if table not in ("cabinets", "seasons", "item_types"):
        raise ValueError(f"Неизвестная таблица справочника: {table}")
    return conn.execute(
        f"SELECT * FROM {table} WHERE is_active = 1 ORDER BY name_ru"
    ).fetchall()


def add_box_code(
    conn: sqlite3.Connection,
    code: str,
    cabinet_id: int,
    season_id: int,
    item_id: int,
    seq: int,
) -> int:
    """
    Записать сгенерированный код короба в историю.
    Бросает sqlite3.IntegrityError при регистронезависимом дубликате.
    """
    cur = conn.execute(
        """INSERT INTO box_codes (code, cabinet_id, season_id, item_id, seq)
           VALUES (?, ?, ?, ?, ?)""",
        (code, cabinet_id, season_id, item_id, seq),
    )
    conn.commit()
    return cur.lastrowid


def code_exists(conn: sqlite3.Connection, code: str) -> bool:
    """Проверка уникальности кода без попытки вставки (регистронезависимо)."""
    row = conn.execute(
        "SELECT 1 FROM box_codes WHERE code = ? COLLATE NOCASE", (code,)
    ).fetchone()
    return row is not None


def get_next_seq(conn: sqlite3.Connection, cabinet_id: int) -> int:
    """
    Следующий свободный порядковый номер для кабинета за СЕГОДНЯ.
    Счётчик общий на кабинет за сутки (не зависит от сезона/категории),
    сбрасывается на новый день автоматически - т.к. считается по дате
    записи created_at, а не по отдельному хранимому счётчику.
    """
    row = conn.execute(
        """SELECT COALESCE(MAX(seq), 0) AS max_seq
           FROM box_codes
           WHERE cabinet_id = ?
             AND date(created_at) = date('now')""",
        (cabinet_id,),
    ).fetchone()
    return row["max_seq"] + 1
