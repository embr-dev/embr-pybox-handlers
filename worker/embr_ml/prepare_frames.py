"""Prepare MatAnyone-friendly RGB PNG frames + mask from a job folder."""

from __future__ import annotations

from pathlib import Path

import numpy as np


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff"}


def list_input_frames(input_dir: Path) -> list[Path]:
    files = [
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and not p.name.startswith(".")
    ]
    return sorted(files, key=lambda p: p.name)


def _exr_to_float_rgb(path: Path) -> np.ndarray:
    """Read EXR as HxWx3 float32 in ~0..1 (OpenEXR 3 may expose 'RGB' or R/G/B)."""
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
    if "R" in names:
        r = np.asarray(chans["R"].pixels, dtype=np.float32)
        return np.clip(np.stack([r, r, r], axis=-1), 0.0, 1.0)
    raise ValueError(f"unsupported EXR channels in {path}: {sorted(names)}")


def _load_rgb_u8(path: Path) -> np.ndarray:
    """Return HxWx3 uint8 RGB."""
    if path.suffix.lower() == ".exr":
        rgb = _exr_to_float_rgb(path)
        return (rgb * 255.0 + 0.5).astype(np.uint8)

    from PIL import Image

    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


def _load_mask_u8(path: Path) -> np.ndarray:
    """Return HxW uint8 mask (0/255-ish)."""
    if path.suffix.lower() == ".exr":
        rgb = _exr_to_float_rgb(path)
        gray = rgb[..., 0]
        return (np.clip(gray, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)

    from PIL import Image

    return np.array(Image.open(path).convert("L"), dtype=np.uint8)


def find_mask_source(job: Path) -> Path:
    for candidate in (
        job / "mask.png",
        job / "mask.exr",
        job / "guide" / "mask.png",
        job / "guide" / "mask.exr",
        job / "guide.png",
        job / "guide.exr",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"missing mask under {job} (mask.png / mask.exr from Capture Guide)"
    )


def prepare_rgb_and_mask(job: Path) -> tuple[Path, Path, int, tuple[int, int]]:
    """
    Build job/_work/rgb/*.png and job/_work/mask.png for MatAnyone.

    Returns (rgb_dir, mask_png, n_frames, (width, height)).
    """
    from PIL import Image

    job = job.expanduser().resolve()
    input_dir = job / "input"
    if not input_dir.is_dir():
        raise FileNotFoundError(f"missing {input_dir}")

    frames = list_input_frames(input_dir)
    if not frames:
        videos = sorted(
            p
            for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}
        )
        if videos:
            raise FileNotFoundError(
                f"video-only input not supported for prepare ({videos[0].name}); "
                "Record Front in Pybox or place a PNG/EXR sequence in input/"
            )
        raise FileNotFoundError(f"no frames in {input_dir}")

    work = job / "_work"
    rgb_dir = work / "rgb"
    if rgb_dir.exists():
        for old in rgb_dir.glob("*"):
            if old.is_file():
                old.unlink()
    rgb_dir.mkdir(parents=True, exist_ok=True)

    size: tuple[int, int] | None = None
    for i, src in enumerate(frames):
        arr = _load_rgb_u8(src)
        h, w = arr.shape[:2]
        if size is None:
            size = (w, h)
        elif (w, h) != size:
            # Resize to first frame size for MatAnyone consistency.
            im = Image.fromarray(arr).resize(size, Image.Resampling.LANCZOS)
            arr = np.array(im, dtype=np.uint8)
        dest = rgb_dir / f"{i:05d}.png"
        Image.fromarray(arr).save(dest)

    assert size is not None
    mask_src = find_mask_source(job)
    mask = _load_mask_u8(mask_src)
    if (mask.shape[1], mask.shape[0]) != size:
        mask = np.array(
            Image.fromarray(mask).resize(size, Image.Resampling.NEAREST),
            dtype=np.uint8,
        )
    mask_png = work / "mask.png"
    Image.fromarray(mask).save(mask_png)
    return rgb_dir, mask_png, len(frames), size
