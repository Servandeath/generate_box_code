import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from label_render import (
    make_pdf_one_per_page,
    DEFAULT_LABEL_SETTINGS,
    register_pdf_font,
    _fit_font_sizes,
)


def test_make_pdf_creates_file_with_pages(tmp_path):
    font_name = register_pdf_font()
    codes = ["MAN_16_07_2026_DE_BT_R4N001", "MAN_16_07_2026_DE_BT_X9Z002"]
    out_path = tmp_path / "labels.pdf"

    result = make_pdf_one_per_page(codes, out_path, DEFAULT_LABEL_SETTINGS, font_name)

    assert result.exists()
    assert result.stat().st_size > 0


def test_make_pdf_empty_list_still_creates_valid_file(tmp_path):
    font_name = register_pdf_font()
    out_path = tmp_path / "empty.pdf"

    result = make_pdf_one_per_page([], out_path, DEFAULT_LABEL_SETTINGS, font_name)

    assert result.exists()


def test_fit_font_sizes_shrinks_for_long_code():
    font_name = register_pdf_font()
    long_code = "MIR_16_07_2026_DE_BT_ABCDEFGHIJ1234"  # длиннее реального формата, специально для теста подгонки
    settings = DEFAULT_LABEL_SETTINGS.copy()

    code_fs, seq_fs, prefix, seq_part = _fit_font_sizes(long_code, settings, font_name)

    assert code_fs <= DEFAULT_LABEL_SETTINGS["code_font_size"]
    assert seq_fs <= DEFAULT_LABEL_SETTINGS["seq_font_size"]
    assert code_fs >= DEFAULT_LABEL_SETTINGS["min_font_size"]


def test_fit_font_sizes_keeps_default_for_short_code():
    font_name = register_pdf_font()
    short_code = "MAN_16_07_2026_DE_BT_R4N001"
    settings = DEFAULT_LABEL_SETTINGS.copy()
    # увеличим этикетку, чтобы точно хватило места без уменьшения
    settings["label_w_mm"] = 100

    code_fs, seq_fs, prefix, seq_part = _fit_font_sizes(short_code, settings, font_name)

    assert code_fs == DEFAULT_LABEL_SETTINGS["code_font_size"]
    assert seq_fs == DEFAULT_LABEL_SETTINGS["seq_font_size"]


def test_fit_font_sizes_splits_prefix_and_seq_correctly():
    font_name = register_pdf_font()
    code = "MAN_16_07_2026_DE_BT_R4N001"
    settings = DEFAULT_LABEL_SETTINGS.copy()

    _, _, prefix, seq_part = _fit_font_sizes(code, settings, font_name)

    assert prefix == "MAN_16_07_2026_DE_BT_R4N"
    assert seq_part == "001"
