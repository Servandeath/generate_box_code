"""
Отрисовка этикетки короба: штрихкод Code128 (растянут на всю ширину
этикетки за вычетом отступов) + текст кода, где последние seq_digits
символов (порядковый номер) печатаются увеличенным шрифтом.

PDF рисуется через reportlab (renderPDF) - надёжный, проверенный путь.
Превью рисуется через python-barcode (чистый Python, без хрупких
C-бэкендов вроде renderPM) - визуально то же самое, но не зависит
от специфики конкретной установки reportlab на машине.

Поддерживаются именованные шаблоны настроек (пресеты) - например
разные размеры этикеток под разные задачи.
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
PRESETS_FILE = Path(__file__).with_name("label_presets.json")

POINTS_PER_MM = 2.834645669291339  # 72 pt/inch / 25.4 mm/inch

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
    "code_font_size": 9,
    "seq_font_size": 18,
    "seq_digits": 3,
    "min_font_size": 4,

    "show_grid": 1,
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


# ---------------------------------------------------------------------------
# Пресеты (именованные шаблоны настроек)
# ---------------------------------------------------------------------------

def load_presets() -> dict:
    """Вернуть словарь {имя_пресета: settings}. Пусто, если файла ещё нет."""
    if PRESETS_FILE.exists():
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_preset(name: str, settings: dict) -> None:
    presets = load_presets()
    presets[name] = settings
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def delete_preset(name: str) -> None:
    presets = load_presets()
    presets.pop(name, None)
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)


def list_preset_names() -> list[str]:
    return sorted(load_presets().keys())


# ---------------------------------------------------------------------------
# Общая логика подгонки шрифта (используется и PDF, и превью)
# ---------------------------------------------------------------------------

def _fit_font_sizes(code: str, settings: dict, font_name: str) -> tuple[int, int, str, str]:
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


# ---------------------------------------------------------------------------
# PDF (reportlab, проверенный путь - не трогаем)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Превью (PIL, через python-barcode - не зависит от renderPM)
# ---------------------------------------------------------------------------

def _render_barcode_bars_pil(code: str, w_px: int, h_px: int):
    """
    Отрисовать штрихкод Code128 как PIL.Image заданного размера,
    используя python-barcode (чистый Python, без C-расширений).
    """
    import barcode
    from barcode.writer import ImageWriter
    from PIL import Image
    import io

    code128_cls = barcode.get_barcode_class("code128")
    writer = ImageWriter()
    writer.dpi = 300  # высокое разрешение, потом сжимаем resize()-ом до нужного размера

    bc = code128_cls(code, writer=writer)
    buf = io.BytesIO()
    bc.write(buf, options={"write_text": False, "quiet_zone": 0, "module_height": 15.0})
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    return img.resize((max(1, w_px), max(1, h_px)))


def render_preview_image(code: str, settings: dict, font_name: str, px_per_mm: int = 8):
    """
    Рендер этикетки в PIL.Image для живого превью в GUI. Текст кода
    использует ТУ ЖЕ _fit_font_sizes(), что и PDF - позиции/пропорции
    текста совпадают. Штрихкод рисуется через python-barcode - визуально
    эквивалентен PDF-версии (Code128), но не зависит от renderPM.
    Рисует миллиметровую сетку с подписями (шаг 5 мм), если show_grid=1.
    """
    from PIL import Image, ImageDraw, ImageFont

    W = int(float(settings["label_w_mm"]) * px_per_mm)
    H = int(float(settings["label_h_mm"]) * px_per_mm)

    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    label_w_mm = float(settings["label_w_mm"])
    label_h_mm = float(settings["label_h_mm"])

    if int(settings.get("show_grid", 1)):
        try:
            axis_font = ImageFont.truetype(FONT_PATH, 9) if FONT_PATH else ImageFont.load_default()
        except Exception:
            axis_font = ImageFont.load_default()

        gx = 0
        while gx <= label_w_mm:
            px = gx * px_per_mm
            draw.line([(px, 0), (px, H)], fill=(225, 225, 235), width=1)
            gx += 5
        gy = 0
        while gy <= label_h_mm:
            py = H - gy * px_per_mm
            draw.line([(0, py), (W, py)], fill=(225, 225, 235), width=1)
            gy += 5

        gx = 0
        while gx <= label_w_mm:
            draw.text((gx * px_per_mm + 1, 1), str(int(gx)), fill=(150, 150, 170), font=axis_font)
            gx += 10
        gy = 10
        while gy <= label_h_mm:
            draw.text((1, H - gy * px_per_mm + 1), str(int(gy)), fill=(150, 150, 170), font=axis_font)
            gy += 10

    draw.rectangle([(0, 0), (W - 1, H - 1)], outline=(0, 0, 0), width=2)

    # --- штрихкод ---
    margin_px = float(settings["margin_mm"]) * px_per_mm
    bw_px = W - 2 * margin_px
    bh_px = float(settings["barcode_h"]) * px_per_mm
    y_top_px = H - (float(settings["barcode_y"]) * px_per_mm) - bh_px

    if bw_px > 0 and bh_px > 0:
        try:
            bc_img = _render_barcode_bars_pil(code, int(bw_px), int(bh_px))
            img.paste(bc_img, (int(margin_px), int(y_top_px)))
        except Exception as e:
            draw.rectangle(
                [(margin_px, y_top_px), (margin_px + bw_px, y_top_px + bh_px)],
                outline=(200, 0, 0), width=2,
            )
            try:
                err_font = ImageFont.truetype(FONT_PATH, 9) if FONT_PATH else ImageFont.load_default()
            except Exception:
                err_font = ImageFont.load_default()
            draw.text((margin_px + 2, y_top_px + 2), f"Ошибка ШК: {e}", fill=(200, 0, 0), font=err_font)

    # --- текст кода ---
    code_fs_pt, seq_fs_pt, prefix, seq_part = _fit_font_sizes(code, settings, font_name)
    pt_to_px = px_per_mm / POINTS_PER_MM

    try:
        code_font = ImageFont.truetype(FONT_PATH, max(6, int(code_fs_pt * pt_to_px))) if FONT_PATH else ImageFont.load_default()
        seq_font = ImageFont.truetype(FONT_PATH, max(6, int(seq_fs_pt * pt_to_px))) if FONT_PATH else ImageFont.load_default()
    except Exception:
        code_font = ImageFont.load_default()
        seq_font = ImageFont.load_default()

    x_px = margin_px
    y_baseline_px = H - (float(settings["code_y"]) * px_per_mm)
    ascent, _ = code_font.getmetrics()
    draw.text((x_px, y_baseline_px - ascent), prefix, fill=(0, 0, 0), font=code_font)

    if seq_part:
        prefix_w_px = draw.textlength(prefix, font=code_font)
        ascent_seq, _ = seq_font.getmetrics()
        draw.text((x_px + prefix_w_px, y_baseline_px - ascent_seq), seq_part, fill=(0, 0, 0), font=seq_font)

    return img
