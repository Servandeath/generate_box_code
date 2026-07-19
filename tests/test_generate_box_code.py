from datetime import date
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate_box_code import generate_box_code, MIN_RANDOM_CHARS

FIXED_DATE = date(2026, 7, 16)


def test_basic_format():
    code = generate_box_code("MAN", "DE", "BT", 1, gen_date=FIXED_DATE)
    assert code.startswith("MAN_16_07_2026_DE_BT_")
    assert code.endswith("001")


def test_seq_boundaries_default_max():
    generate_box_code("MAN", "DE", "BT", 300, gen_date=FIXED_DATE)
    with pytest.raises(ValueError):
        generate_box_code("MAN", "DE", "BT", 301, gen_date=FIXED_DATE)
    with pytest.raises(ValueError):
        generate_box_code("MAN", "DE", "BT", 0, gen_date=FIXED_DATE)


def test_max_seq_1000_uses_more_digits():
    code = generate_box_code("MAN", "DE", "BT", 1000, max_seq=1000, gen_date=FIXED_DATE)
    assert code.endswith("1000")
    with pytest.raises(ValueError):
        generate_box_code("MAN", "DE", "BT", 1001, max_seq=1000, gen_date=FIXED_DATE)


def test_all_three_cabinets_fit():
    for cab in ("MAN", "MIR", "MEL"):
        code = generate_box_code(cab, "DE", "BT", 1, gen_date=FIXED_DATE)
        assert len(code) <= 30


def test_too_long_inputs_raise():
    with pytest.raises(ValueError):
        generate_box_code("MAN", "SEASON123456", "ITEMTYPE123456", 1, gen_date=FIXED_DATE)


def test_random_part_has_minimum_entropy():
    code = generate_box_code("MAN", "DE", "BT", 1, gen_date=FIXED_DATE)
    randomseq_block = code.split("_")[-1]
    random_part = randomseq_block[:-3]
    assert len(random_part) >= MIN_RANDOM_CHARS


def test_no_wb_prefix():
    with pytest.raises(ValueError):
        generate_box_code("WBC", "DE", "BT", 1, gen_date=FIXED_DATE)
