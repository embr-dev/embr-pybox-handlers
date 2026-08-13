"""Download / verify model weights without touching system Python."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import urllib.request
from pathlib import Path

from embr_ml import paths

# Official release asset (MatAnyone2 README).
MATANYONE2_PTH_URL = (
    "https://github.com/pq-yang/MatAnyone2/releases/download/v1.0.0/matanyone2.pth"
)
MATANYONE2_PTH_NAME = "matanyone2.pth"


def matanyone2_weight_path() -> Path:
    return paths.matanyone2_dir() / MATANYONE2_PTH_NAME


def status_lines() -> list[str]:
    root = paths.ml_root()
    weight = matanyone2_weight_path()
    lines = [
        f"EMBR_ML_ROOT={root}",
        f"matanyone2_pth={weight}",
        f"matanyone2_pth_exists={weight.is_file()}",
    ]
    if weight.is_file():
        lines.append(f"matanyone2_pth_bytes={weight.stat().st_size}")
    return lines


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    if partial.exists():
        partial.unlink()

    print(f"fetch {url}", flush=True)
    print(f"dest  {dest}", flush=True)

    curl = shutil.which("curl")
    if curl:
        # curl uses the OS trust store — more reliable than Flame's urllib SSL.
        subprocess.run(
            [
                curl,
                "-fL",
                "--retry",
                "3",
                "--retry-delay",
                "2",
                "-o",
                partial.as_posix(),
                url,
            ],
            check=True,
        )
    else:
        def _reporthook(block_num: int, block_size: int, total_size: int) -> None:
            if total_size <= 0 or block_num % 64 != 0:
                return
            got = min(block_num * block_size, total_size)
            pct = 100.0 * got / total_size
            print(f"download {pct:5.1f}% ({got}/{total_size})", flush=True)

        urllib.request.urlretrieve(url, partial.as_posix(), reporthook=_reporthook)

    partial.replace(dest)
    print(f"ok    {dest} ({dest.stat().st_size} bytes)", flush=True)


def ensure_matanyone2(*, force: bool = False) -> Path:
    """
    Ensure matanyone2.pth under $EMBR_ML_ROOT/models/matanyone2/.

    Uses stdlib only (no torch). Safe to call from a thin Pybox → subprocess.
    License: NTU S-Lab 1.0 (non-commercial) — research use; do not redistribute weights in git.
    """
    paths.ensure_layout()
    dest = matanyone2_weight_path()
    if dest.is_file() and not force:
        print(f"already present: {dest} ({dest.stat().st_size} bytes)", flush=True)
        return dest
    _download(MATANYONE2_PTH_URL, dest)
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
