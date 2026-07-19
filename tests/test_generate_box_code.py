from datetime import date
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generate_box_code import generate_box_code, MIN_RANDOM_CHARS

FIXED_DATE = date(2026, 7, 16)


def test_basic_format():
    code = generate_box_code("ALF", "DE", "BT", 1, gen_date=FIXED_DATE)
    assert code.startswith("ALF_16_07_2026_DE_BT_")
    assert code.endswith("001")


def test_seq_below_min_raises():
    with pytest.raises(ValueError):
        generate_box_code("ALF", "DE", "BT", 0, gen_date=FIXED_DATE)


def test_no_upper_limit_seq_grows_digits():
    code_small = generate_box_code("ALF", "DE", "BT", 5, gen_date=FIXED_DATE)
    assert code_small.endswith("005")

    code_big = generate_box_code("ALF", "DE", "BT", 1234, gen_date=FIXED_DATE)
    assert code_big.endswith("1234")


def test_very_large_seq_eventually_raises_no_budget():
    huge_seq = 10**20
    with pytest.raises(ValueError):
        generate_box_code("ALF", "DE", "BT", huge_seq, gen_date=FIXED_DATE)


def test_all_three_cabinets_fit():
    for cab in ("ALF", "BET", "GAM"):
        code = generate_box_code(cab, "DE", "BT", 1, gen_date=FIXED_DATE)
        assert len(code) <= 30


def test_too_long_inputs_raise():
    with pytest.raises(ValueError):
        generate_box_code("ALF", "SEASON123456", "ITEMTYPE123456", 1, gen_date=FIXED_DATE)


def test_random_part_has_minimum_entropy():
    code = generate_box_code("ALF", "DE", "BT", 1, gen_date=FIXED_DATE)
    randomseq_block = code.split("_")[-1]
    random_part = randomseq_block[:-3]
    assert len(random_part) >= MIN_RANDOM_CHARS


def test_no_wb_prefix():
    with pytest.raises(ValueError):
        generate_box_code("WBC", "DE", "BT", 1, gen_date=FIXED_DATE)
