"""Publish MatAnyone2 outputs into Pybox cache layout.

  pha/*.png → job/alpha/{frame}.exr  (OutMatte)
  fgr/*.png → job/fgr/{frame}.exr    (Result)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np


def _natural_pngs(folder: Path) -> list[Path]:
    files = sorted(folder.glob("*.png"))
    if not files:
        raise FileNotFoundError(f"no PNG files in {folder}")
    return files


def _frame_index_from_name(path: Path) -> int | None:
    m = re.search(r"(\d+)\.png$", path.name, flags=re.I)
    return int(m.group(1)) if m else None


def write_gray_exr(path: Path, gray01: np.ndarray) -> None:
    """Write RGB EXR matching Flame Capture style: HALF + no compression."""
    import OpenEXR

    gray = np.asarray(gray01, dtype=np.float32)
    half = gray.astype(np.float16)
    channels = {
        "R": OpenEXR.Channel(half),
        "G": OpenEXR.Channel(half),
        "B": OpenEXR.Channel(half),
    }
    header = {
        "compression": OpenEXR.NO_COMPRESSION,
        "type": OpenEXR.scanlineimage,
    }
    OpenEXR.File(header, channels).write(path.as_posix())


def write_rgb_exr(path: Path, rgb01: np.ndarray) -> None:
    """Write RGB float01 HWC as HALF EXR (Flame-friendly)."""
    import OpenEXR

    rgb = np.asarray(rgb01, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError(f"expected HxWx3 array, got {rgb.shape}")
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


def _normalize_job_dir(job_dir: Path) -> Path:
    job_dir = job_dir.expanduser().resolve()
    if job_dir.name.lower() in {"alpha", "fgr"}:
        job_dir = job_dir.parent
    return job_dir


def _iter_frame_targets(
    pngs: list[Path],
    *,
    start_frame: int,
    use_filename_index: bool,
) -> list[tuple[Path, int]]:
    out: list[tuple[Path, int]] = []
    for i, png in enumerate(pngs):
        if use_filename_index:
            idx = _frame_index_from_name(png)
            frame = start_frame + (idx if idx is not None else i)
        else:
            frame = start_frame + i
        out.append((png, frame))
    return out


def publish_pha_to_alpha(
    pha_dir: Path,
    job_dir: Path,
    *,
    start_frame: int = 1,
    padding: int = 4,
    use_filename_index: bool = True,
    size: tuple[int, int] | None = None,
) -> list[Path]:
    """Convert pha/*.png → job/alpha/{frame}.exr"""
    from PIL import Image

    pha_dir = pha_dir.expanduser().resolve()
    job_dir = _normalize_job_dir(job_dir)
    alpha_dir = job_dir / "alpha"
    alpha_dir.mkdir(parents=True, exist_ok=True)

    pngs = _natural_pngs(pha_dir)
    written: list[Path] = []
    for png, frame in _iter_frame_targets(
        pngs, start_frame=start_frame, use_filename_index=use_filename_index
    ):
        dest = alpha_dir / f"{frame:0{padding}d}.exr"
        im = Image.open(png).convert("L")
        if size is not None:
            im = im.resize(size, Image.Resampling.LANCZOS)
        arr = np.array(im, dtype=np.float32) / 255.0
        write_gray_exr(dest, arr)
        written.append(dest)
        print(f"{png.name} → {dest} ({im.size[0]}x{im.size[1]})", flush=True)
    print(f"published {len(written)} frames → {alpha_dir}", flush=True)
    return written


def publish_fgr_to_cache(
    fgr_dir: Path,
    job_dir: Path,
    *,
    start_frame: int = 1,
    padding: int = 4,
    use_filename_index: bool = True,
    size: tuple[int, int] | None = None,
) -> list[Path]:
    """Convert fgr/*.png → job/fgr/{frame}.exr for Result playback."""
    from PIL import Image

    fgr_dir = fgr_dir.expanduser().resolve()
    job_dir = _normalize_job_dir(job_dir)
    out_dir = job_dir / "fgr"
    out_dir.mkdir(parents=True, exist_ok=True)

    pngs = _natural_pngs(fgr_dir)
    written: list[Path] = []
    for png, frame in _iter_frame_targets(
        pngs, start_frame=start_frame, use_filename_index=use_filename_index
    ):
        dest = out_dir / f"{frame:0{padding}d}.exr"
        im = Image.open(png).convert("RGB")
        if size is not None:
            im = im.resize(size, Image.Resampling.LANCZOS)
        arr = np.array(im, dtype=np.float32) / 255.0
        write_rgb_exr(dest, arr)
        written.append(dest)
        print(f"{png.name} → {dest} ({im.size[0]}x{im.size[1]})", flush=True)
    print(f"published {len(written)} frames → {out_dir}", flush=True)
    return written


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml publish-cache")
    p.add_argument(
        "--pha-dir",
        type=Path,
        required=True,
        help="Directory of MatAnyone2 pha PNGs (…/out/<name>/pha)",
    )
    p.add_argument(
        "--job-dir",
        type=Path,
        required=True,
        help="Job folder (will create alpha/ inside)",
    )
    p.add_argument(
        "--fgr-dir",
        type=Path,
        default=None,
        help="Optional fgr PNG dir → job/fgr/{frame}.exr",
    )
    p.add_argument(
        "--start-frame",
        type=int,
        default=1,
        help="Batch frame number for first pha index (default 1)",
    )
    p.add_argument("--padding", type=int, default=4)
    p.add_argument(
        "--ignore-names",
        action="store_true",
        help="Ignore PNG numeric names; use sorted order only",
    )
    p.add_argument(
        "--width",
        type=int,
        default=None,
        help="Resize width to match Batch Front (required for Pybox)",
    )
    p.add_argument(
        "--height",
        type=int,
        default=None,
        help="Resize height to match Batch Front",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    size = None
    if args.width and args.height:
        size = (args.width, args.height)
    elif args.width or args.height:
        raise SystemExit("Specify both --width and --height, or neither.")
    publish_pha_to_alpha(
        args.pha_dir,
        args.job_dir,
        start_frame=args.start_frame,
        padding=args.padding,
        use_filename_index=not args.ignore_names,
        size=size,
    )
    if args.fgr_dir is not None:
        publish_fgr_to_cache(
            args.fgr_dir,
            args.job_dir,
            start_frame=args.start_frame,
            padding=args.padding,
            use_filename_index=not args.ignore_names,
            size=size,
        )
    return 0
