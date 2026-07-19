import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from db import init_db, get_connection, add_reference, list_active
from box_service import create_box_code, MAX_GENERATION_ATTEMPTS


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    connection = get_connection(db_path)
    yield connection
    connection.close()


def test_full_flow_reference_to_generated_code(conn):
    # 1. Заполняем справочники (как это сделает CRUD в GUI)
    cab_id = add_reference(conn, "cabinets", "Мани", "MAN")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    # 2. Проверяем, что справочники реально видны (то, что покажет выпадающий список)
    cabinets = list_active(conn, "cabinets")
    assert len(cabinets) == 1
    assert cabinets[0]["code_latin"] == "MAN"

    # 3. Генерируем код короба через сервисный слой
    code = create_box_code(
        conn,
        cabinet_id=cab_id, cabinet_code="MAN",
        season_id=season_id, season_code="DE",
        item_id=item_id, item_code="BT",
        seq=1,
    )

    # 4. Проверяем результат: формат и факт записи в историю
    assert code.startswith("MAN_")
    assert code.endswith("001")
    row = conn.execute("SELECT * FROM box_codes WHERE code = ?", (code,)).fetchone()
    assert row is not None
    assert row["cabinet_id"] == cab_id


def test_sequential_codes_for_same_day_are_unique(conn):
    cab_id = add_reference(conn, "cabinets", "Мани", "MAN")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    codes = set()
    for seq in range(1, 11):
        code = create_box_code(
            conn,
            cabinet_id=cab_id, cabinet_code="MAN",
            season_id=season_id, season_code="DE",
            item_id=item_id, item_code="BT",
            seq=seq,
        )
        codes.add(code)

    assert len(codes) == 10  # все 10 кодов уникальны


def test_deactivated_reference_not_in_active_list_but_history_intact(conn):
    from db import deactivate_reference

    cab_id = add_reference(conn, "cabinets", "Мани", "MAN")
    season_id = add_reference(conn, "seasons", "Демисезон", "DE")
    item_id = add_reference(conn, "item_types", "Ботфорты", "BT")

    code = create_box_code(
        conn,
        cabinet_id=cab_id, cabinet_code="MAN",
        season_id=season_id, season_code="DE",
        item_id=item_id, item_code="BT",
        seq=1,
    )

    # Отключаем кабинет (мягко) - как будто он больше не используется
    deactivate_reference(conn, "cabinets", cab_id)

    # В активном списке кабинета больше нет
    assert len(list_active(conn, "cabinets")) == 0

    # Но история кода не пострадала
    row = conn.execute("SELECT * FROM box_codes WHERE code = ?", (code,)).fetchone()
    assert row is not None
