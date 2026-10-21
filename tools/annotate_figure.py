# -*- coding: utf-8 -*-
"""Render text-box overlays onto a pipeline figure PNG.

The editable source of truth is <run>/decision_logs/figure_annotations.json.
The original figure is never modified; output is *.annotated.png / *.annotated.pdf.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap_pixels(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in (text or "").splitlines() or [""]:
        current = ""
        for char in paragraph:
            probe = current + char
            width = draw.textbbox((0, 0), probe, font=font)[2]
            if width <= max_width or not current:
                current = probe
            else:
                lines.append(current)
                current = char
        lines.append(current)
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--figure", required=True)
    parser.add_argument("--annotations", default=None)
    args = parser.parse_args()

    root = Path(args.run_root).resolve()
    figure = Path(args.figure).as_posix()
    source = (root / figure).resolve()
    if not source.exists():
        raise SystemExit(f"figure not found: {source}")

    annotations_path = Path(args.annotations) if args.annotations else root / "decision_logs" / "figure_annotations.json"
    payload = json.loads(annotations_path.read_text(encoding="utf-8")) if annotations_path.exists() else {}
    record = (payload.get("figures") or {}).get(figure) or {}
    elements = record.get("elements") or []

    image = Image.open(source).convert("RGBA")
    width, height = image.size
    draw = ImageDraw.Draw(image)
    for element in elements:
        if not isinstance(element, dict) or element.get("text", "").strip() == "":
            continue
        x = float(element.get("x", 0)) * width
        y = float(element.get("y", 0)) * height
        w = max(8.0, float(element.get("w", 0.2)) * width)
        h = max(8.0, float(element.get("h", 0.08)) * height)
        font_size = max(8, int(float(element.get("fontSize", 20))))
        font = load_font(font_size)
        background = element.get("background")
        if background:
            draw.rounded_rectangle(
                [x, y, x + w, y + h],
                radius=4,
                fill=background,
                outline=element.get("border") or None,
                width=1 if element.get("border") else 0,
            )
        lines = wrap_pixels(draw, str(element.get("text", "")), font, max(8, int(w - 8)))
        line_height = int(font_size * 1.25)
        for index, line in enumerate(lines):
            draw.text(
                (x + 4, y + 4 + index * line_height),
                line,
                font=font,
                fill=element.get("color") or "#222222",
            )

    stem = source.stem
    out_png = source.with_name(f"{stem}.annotated.png")
    out_pdf = source.with_name(f"{stem}.annotated.pdf")
    image.convert("RGB").save(out_png, "PNG")
    image.convert("RGB").save(out_pdf, "PDF", resolution=300)
    print(json.dumps({
        "ok": True,
        "source": figure,
        "elements": len(elements),
        "png": out_png.relative_to(root).as_posix(),
        "pdf": out_pdf.relative_to(root).as_posix(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
