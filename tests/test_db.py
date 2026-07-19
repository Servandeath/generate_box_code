import os
import sys
import sqlite3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db import (
    init_db,
    get_connection,
    add_reference,
    deactivate_reference,
    list_active,
    add_box_code,
    code_exists,
)


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    connection = get_connection(db_path)
    yield connection
    connection.close()


def test_init_db_creates_tables(conn):
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"cabinets", "seasons", "item_types", "box_codes"}.issubset(tables)


def test_add_and_list_reference(conn):
    ref_id = add_reference(conn, "cabinets", "Мани", "MAN")
    active = list_active(conn, "cabinets")
    assert len(active) == 1
    assert active[0]["id"] == ref_id
    assert active[0]["code_latin"] == "MAN"


def test_deactivate_reference_hides_from_list(conn):
    ref_id = add_reference(conn, "seasons", "Демисезон", "DE")
    deactivate_reference(conn, "seasons", ref_id)
    active = list_active(conn, "seasons")
    assert len(active) == 0


def test_deactivate_does_not_delete_row(conn):
    ref_id = add_reference(conn, "item_types", "Ботфорты", "BT")
    deactivate_reference(conn, "item_types", ref_id)
    row = conn.execute("SELECT * FROM item_types WHERE id = ?", (ref_id,)).fetchone()
    assert row is not None
    assert row["is_active"] == 0


def test_add_box_code_and_check_exists(conn):
    cab_id = add_reference(conn, "cabinets", "Мани", "MAN")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    code = "MAN_16_07_2026_DE_BT_R4N001"
    add_box_code(conn, code, cab_id, season_id, item_id, 1)

    assert code_exists(conn, code) is True
    assert code_exists(conn, code.lower()) is True  # регистронезависимо
    assert code_exists(conn, "NOT_A_REAL_CODE") is False


def test_duplicate_code_case_insensitive_raises(conn):
    cab_id = add_reference(conn, "cabinets", "Мани", "MAN")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    code = "MAN_16_07_2026_DE_BT_R4N001"
    add_box_code(conn, code, cab_id, season_id, item_id, 1)

    with pytest.raises(sqlite3.IntegrityError):
        add_box_code(conn, code.lower(), cab_id, season_id, item_id, 2)
