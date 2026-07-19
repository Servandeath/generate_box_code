import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from transliterate import transliterate, suggest_code, is_valid_ref_code


def test_basic_word():
    assert transliterate("Демисезон") == "DEMISEZON"


def test_word_with_zh_and_multi_letter_sounds():
    # ж -> ZH (2 буквы), щ -> SCH (3 буквы), ю -> YU (2 буквы)
    assert transliterate("Женский") == "ZHENSKIY"
    assert transliterate("Плащ") == "PLASCH"
    assert transliterate("Юбка") == "YUBKA"


def test_strips_spaces_and_soft_signs():
    assert transliterate("Мяг кий") == "MYAGKIY"
    assert transliterate("Ботфорты") == "BOTFORTY"


def test_mixed_cyrillic_and_latin_input():
    assert transliterate("Демиsezon") == "DEMISEZON"


def test_suggest_code_respects_length():
    assert suggest_code("Демисезон", 2) == "DE"
    assert suggest_code("Мани", 3) == "MAN"
    assert suggest_code("Ботфорты", 2) == "BO"


def test_suggest_code_empty_input_raises():
    with pytest.raises(ValueError):
        suggest_code("", 2)
    with pytest.raises(ValueError):
        suggest_code("   ", 2)


def test_suggest_code_invalid_length_raises():
    with pytest.raises(ValueError):
        suggest_code("Мани", 0)


def test_is_valid_ref_code():
    assert is_valid_ref_code("MAN") is True
    assert is_valid_ref_code("BT-1") is True
    assert is_valid_ref_code("") is False
    assert is_valid_ref_code("МАН") is False  # кириллица недопустима
    assert is_valid_ref_code("MA N") is False  # пробел недопустим
