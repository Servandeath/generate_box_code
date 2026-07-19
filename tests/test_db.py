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
    get_next_seq,
    list_history,
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
    ref_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    active = list_active(conn, "cabinets")
    assert len(active) == 1
    assert active[0]["id"] == ref_id
    assert active[0]["code_latin"] == "ALF"


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
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    code = "ALF_16_07_2026_DE_BT_R4N001"
    add_box_code(conn, code, cab_id, season_id, item_id, 1)

    assert code_exists(conn, code) is True
    assert code_exists(conn, code.lower()) is True
    assert code_exists(conn, "NOT_A_REAL_CODE") is False


def test_duplicate_code_case_insensitive_raises(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    code = "ALF_16_07_2026_DE_BT_R4N001"
    add_box_code(conn, code, cab_id, season_id, item_id, 1)

    with pytest.raises(sqlite3.IntegrityError):
        add_box_code(conn, code.lower(), cab_id, season_id, item_id, 2)


def test_get_next_seq_starts_at_one(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    assert get_next_seq(conn, cab_id) == 1


def test_get_next_seq_increments_after_codes_added(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    add_box_code(conn, "ALF_16_07_2026_DE_BT_AAA001", cab_id, season_id, item_id, 1)
    add_box_code(conn, "ALF_16_07_2026_DE_BT_BBB002", cab_id, season_id, item_id, 2)

    assert get_next_seq(conn, cab_id) == 3


def test_get_next_seq_independent_per_cabinet(conn):
    cab1 = add_reference(conn, "cabinets", "Альфа", "ALF")
    cab2 = add_reference(conn, "cabinets", "Бета", "BET")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    add_box_code(conn, "ALF_16_07_2026_DE_BT_AAA001", cab1, season_id, item_id, 1)

    assert get_next_seq(conn, cab1) == 2
    assert get_next_seq(conn, cab2) == 1


def test_list_history_returns_readable_names(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    add_box_code(conn, "ALF_16_07_2026_DE_BT_AAA001", cab_id, season_id, item_id, 1)

    history = list_history(conn)
    assert len(history) == 1
    assert history[0]["code"] == "ALF_16_07_2026_DE_BT_AAA001"
    assert history[0]["cabinet_name"] == "Альфа"
    assert history[0]["season_name"] == "Демисезон"
    assert history[0]["item_name"] == "Ботфорты"


def test_list_history_newest_first(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    add_box_code(conn, "ALF_16_07_2026_DE_BT_AAA001", cab_id, season_id, item_id, 1)
    add_box_code(conn, "ALF_16_07_2026_DE_BT_BBB002", cab_id, season_id, item_id, 2)

    history = list_history(conn)
    assert history[0]["code"] == "ALF_16_07_2026_DE_BT_BBB002"


def test_list_history_respects_limit(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    for i in range(5):
        add_box_code(conn, f"ALF_16_07_2026_DE_BT_AAA{i:03d}", cab_id, season_id, item_id, i + 1)

    history = list_history(conn, limit=3)
    assert len(history) == 3


def test_list_history_deactivated_reference_still_shows_name(conn):
    cab_id = add_reference(conn, "cabinets", "Альфа", "ALF")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    add_box_code(conn, "ALF_16_07_2026_DE_BT_AAA001", cab_id, season_id, item_id, 1)
    deactivate_reference(conn, "cabinets", cab_id)

    history = list_history(conn)
    assert history[0]["cabinet_name"] == "Альфа"
