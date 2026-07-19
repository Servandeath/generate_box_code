"""
Отрисовка этикетки короба: штрихкод Code128 (растянут на всю ширину
этикетки за вычетом отступов) + текст кода, где последние seq_digits
символов (порядковый номер) печатаются увеличенным шрифтом.

Шрифт текста кода АВТОМАТИЧЕСКИ подгоняется под доступную ширину
этикетки - код никогда не вылезает за край, независимо от длины.
"""

import json
import os
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import createBarcodeDrawing

PDF_FONT_NAME = "LabelFont"
SETTINGS_FILE = Path(__file__).with_name("label_settings.json")

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\verdana.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

DEFAULT_LABEL_SETTINGS = {
    "label_w_mm": 58,
    "label_h_mm": 40,
    "margin_mm": 3,

    "barcode_y": 16,
    "barcode_h": 18,

    "code_y": 4,
    "code_font_size": 9,      # стартовый размер, автоматически уменьшается, если код не влезает
    "seq_font_size": 18,      # стартовый размер номера, тоже подгоняется пропорционально
    "seq_digits": 3,
    "min_font_size": 4,       # ниже этого автоподгонка не опускается
}


def find_font_path() -> str | None:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    search_dirs = [
        r"C:\Windows\Fonts",
        "/usr/share/fonts",
        "/Library/Fonts",
        os.path.expanduser("~/.fonts"),
    ]
    for d in search_dirs:
        if os.path.isdir(d):
            for rootdir, _, files in os.walk(d):
                for fn in files:
                    if fn.lower().endswith(".ttf"):
                        return os.path.join(rootdir, fn)
    return None


FONT_PATH = find_font_path()


def register_pdf_font() -> str:
    if FONT_PATH:
        try:
            pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, FONT_PATH))
            return PDF_FONT_NAME
        except Exception:
            pass
    return "Helvetica"


def load_label_settings() -> dict:
    settings = DEFAULT_LABEL_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except Exception:
            pass
    return settings


def save_label_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def _fit_font_sizes(code: str, settings: dict, font_name: str) -> tuple[int, int, str, str]:
    """
    Подобрать размеры шрифта code_font_size/seq_font_size так, чтобы
    prefix+seq влезли в доступную ширину этикетки. Уменьшает оба размера
    пропорционально, пока не влезет, но не ниже min_font_size.
    """
    seq_digits = int(settings["seq_digits"])
    prefix = code[:-seq_digits] if seq_digits > 0 else code
    seq_part = code[-seq_digits:] if seq_digits > 0 else ""

    available_width = (float(settings["label_w_mm"]) - 2 * float(settings["margin_mm"])) * mm

    code_fs = int(settings["code_font_size"])
    seq_fs = int(settings["seq_font_size"])
    min_fs = int(settings["min_font_size"])

    while code_fs > min_fs and seq_fs > min_fs:
        total_width = (
            pdfmetrics.stringWidth(prefix, font_name, code_fs)
            + pdfmetrics.stringWidth(seq_part, font_name, seq_fs)
        )
        if total_width <= available_width:
            break
        code_fs -= 1
        seq_fs -= 1

    return code_fs, seq_fs, prefix, seq_part


def draw_barcode(c: canvas.Canvas, code: str, settings: dict):
    margin = float(settings["margin_mm"]) * mm
    w = (float(settings["label_w_mm"]) * mm) - 2 * margin
    h = float(settings["barcode_h"]) * mm
    y = float(settings["barcode_y"]) * mm

    drawing = createBarcodeDrawing(
        "Code128",
        value=code,
        width=w,
        height=h,
        humanReadable=False,
    )
    c.saveState()
    c.translate(margin, y)
    renderPDF.draw(drawing, c, 0, 0)
    c.restoreState()


def draw_code_text(c: canvas.Canvas, code: str, settings: dict, font_name: str):
    code_fs, seq_fs, prefix, seq_part = _fit_font_sizes(code, settings, font_name)

    x = float(settings["margin_mm"]) * mm
    y = float(settings["code_y"]) * mm

    c.setFont(font_name, code_fs)
    c.drawString(x, y, prefix)

    if seq_part:
        prefix_width = pdfmetrics.stringWidth(prefix, font_name, code_fs)
        c.setFont(font_name, seq_fs)
        c.drawString(x + prefix_width, y, seq_part)


def draw_label(c: canvas.Canvas, code: str, settings: dict, font_name: str):
    draw_barcode(c, code, settings)
    draw_code_text(c, code, settings, font_name)


def make_pdf_one_per_page(codes: list[str], out_path: str | Path, settings: dict, font_name: str):
    w = float(settings["label_w_mm"]) * mm
    h = float(settings["label_h_mm"]) * mm
    c = canvas.Canvas(str(out_path), pagesize=(w, h))
    for code in codes:
        draw_label(c, code, settings, font_name)
        c.showPage()
    c.save()
    return Path(out_path)
