"""Burn a status HUD into an EXR for Pybox Result display.

Flame's bundled Python has no PIL/OpenEXR — call this from the worker venv.
Keep imports light (no torch / matanyone).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _exr_to_float_rgb(path: Path) -> np.ndarray:
    import OpenEXR

    f = OpenEXR.File(path.as_posix())
    chans = f.channels()
    names = set(chans.keys())
    if "RGB" in names:
        rgb = np.asarray(chans["RGB"].pixels, dtype=np.float32)
        if rgb.ndim == 2:
            rgb = np.stack([rgb, rgb, rgb], axis=-1)
        elif rgb.shape[-1] > 3:
            rgb = rgb[..., :3]
        return np.clip(rgb, 0.0, 1.0)
    if {"R", "G", "B"} <= names:
        r = np.asarray(chans["R"].pixels, dtype=np.float32)
        g = np.asarray(chans["G"].pixels, dtype=np.float32)
        b = np.asarray(chans["B"].pixels, dtype=np.float32)
        return np.clip(np.stack([r, g, b], axis=-1), 0.0, 1.0)
    if "Y" in names:
        y = np.asarray(chans["Y"].pixels, dtype=np.float32)
        return np.clip(np.stack([y, y, y], axis=-1), 0.0, 1.0)
    raise ValueError(f"unsupported EXR channels in {path}: {sorted(names)}")


def _load_rgb_u8(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".exr":
        return (_exr_to_float_rgb(path) * 255.0 + 0.5).astype(np.uint8)
    from PIL import Image

    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


def _write_rgb_exr(path: Path, rgb01: np.ndarray) -> None:
    import OpenEXR

    rgb = np.asarray(rgb01, dtype=np.float32)
    half = rgb[:, :, :3].astype(np.float16)
    channels = {
        "R": OpenEXR.Channel(np.ascontiguousarray(half[:, :, 0])),
        "G": OpenEXR.Channel(np.ascontiguousarray(half[:, :, 1])),
        "B": OpenEXR.Channel(np.ascontiguousarray(half[:, :, 2])),
    }
    header = {
        "compression": OpenEXR.NO_COMPRESSION,
        "type": OpenEXR.scanlineimage,
    }
    OpenEXR.File(header, channels).write(path.as_posix())


def _font(size: int):
    from PIL import ImageFont

    for name in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_hud(
    base: Path,
    out: Path,
    *,
    title: str,
    lines: list[str],
) -> None:
    from PIL import Image, ImageDraw

    rgb = _load_rgb_u8(base)
    h, w = rgb.shape[:2]
    im = Image.fromarray(rgb, mode="RGB")
    draw = ImageDraw.Draw(im, "RGBA")

    title_font = _font(max(18, h // 40))
    body_font = _font(max(14, h // 48))
    pad = max(12, h // 60)
    line_h = max(20, h // 36)
    panel_w = min(w - 2 * pad, max(320, w // 2))
    panel_h = pad * 2 + line_h + len(lines) * line_h + pad

    # Top-left panel
    x0, y0 = pad, pad
    x1, y1 = x0 + panel_w, y0 + panel_h
    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 170))
    draw.rectangle([x0, y0, x1, y1], outline=(220, 220, 220, 220), width=2)

    y = y0 + pad
    draw.text((x0 + pad, y), title, font=title_font, fill=(255, 220, 80, 255))
    y += line_h
    for line in lines:
        draw.text((x0 + pad, y), line, font=body_font, fill=(240, 240, 240, 255))
        y += line_h

    out.parent.mkdir(parents=True, exist_ok=True)
    arr = np.array(im.convert("RGB"), dtype=np.float32) / 255.0
    _write_rgb_exr(out, arr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml hud-overlay")
    p.add_argument("--base", type=Path, required=True, help="Source EXR/PNG")
    p.add_argument("--out", type=Path, required=True, help="Output EXR")
    p.add_argument("--title", default="Embr Matte")
    p.add_argument(
        "--info-json",
        type=Path,
        required=True,
        help='JSON {"lines": ["…", …]}',
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data = json.loads(args.info_json.read_text(encoding="utf-8"))
    lines = [str(x) for x in data.get("lines", [])]
    if not lines:
        lines = ["(no status)"]
    render_hud(args.base, args.out, title=str(data.get("title") or args.title), lines=lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
