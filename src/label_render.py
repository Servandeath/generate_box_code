"""
Отрисовка этикетки короба: штрихкод Code128 + текст кода, где
последние SEQ_DIGITS_DEFAULT символов (порядковый номер) печатаются
увеличенным шрифтом относительно остальной части кода - для чтения
издалека без сканера.

Логика поиска/регистрации кириллического TTF-шрифта позаимствована
из wb-barcode-gui (тот же паттерн: перебор системных путей Windows/
Linux/macOS, регистрация в reportlab).
"""

import os
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import createBarcodeDrawing

PDF_FONT_NAME = "LabelFont"

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

    "barcode_x": 5,
    "barcode_y": 18,
    "barcode_w": 48,
    "barcode_h": 14,

    "code_x": 5,
    "code_y": 6,
    "code_font_size": 8,
    "seq_font_size": 16,
    "seq_digits": 3,
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


def draw_barcode(c: canvas.Canvas, code: str, x_mm: float, y_mm: float, w_mm: float, h_mm: float):
    drawing = createBarcodeDrawing(
        "Code128",
        value=code,
        width=w_mm * mm,
        height=h_mm * mm,
        humanReadable=False,
    )
    c.saveState()
    c.translate(x_mm * mm, y_mm * mm)
    renderPDF.draw(drawing, c, 0, 0)
    c.restoreState()


def draw_code_text(c: canvas.Canvas, code: str, settings: dict, font_name: str):
    seq_digits = int(settings["seq_digits"])
    prefix = code[:-seq_digits] if seq_digits > 0 else code
    seq_part = code[-seq_digits:] if seq_digits > 0 else ""

    x = float(settings["code_x"]) * mm
    y = float(settings["code_y"]) * mm
    code_fs = int(settings["code_font_size"])
    seq_fs = int(settings["seq_font_size"])

    c.setFont(font_name, code_fs)
    c.drawString(x, y, prefix)

    if seq_part:
        prefix_width = pdfmetrics.stringWidth(prefix, font_name, code_fs)
        c.setFont(font_name, seq_fs)
        c.drawString(x + prefix_width, y, seq_part)


def draw_label(c: canvas.Canvas, code: str, settings: dict, font_name: str):
    draw_barcode(
        c, code,
        float(settings["barcode_x"]), float(settings["barcode_y"]),
        float(settings["barcode_w"]), float(settings["barcode_h"]),
    )
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
