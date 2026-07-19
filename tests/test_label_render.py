import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from label_render import make_pdf_one_per_page, DEFAULT_LABEL_SETTINGS, register_pdf_font


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
