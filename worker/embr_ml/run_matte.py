"""MatAnyone2 inference entry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _default_device() -> str:
    return "mps" if sys.platform == "darwin" else "cuda:0"


def run_matte(
    input_path: Path,
    mask_path: Path,
    output_path: Path,
    *,
    device: str | None = None,
    max_size: int | None = None,
    save_image: bool = True,
) -> int:
    if device is None:
        device = _default_device()
    try:
        from matanyone2 import InferenceCore, MatAnyone2
    except ImportError:
        print(
            "matanyone2 is not installed in this venv.\n"
            "Install (after packaging patch if needed):\n"
            "  uv pip install -e /path/to/MatAnyone2\n"
            "Weights only:\n"
            "  uv run embr-ml ensure-models",
            file=sys.stderr,
        )
        return 2

    output_path.mkdir(parents=True, exist_ok=True)
    model = MatAnyone2.from_pretrained("PeiqingYang/MatAnyone2")
    processor = InferenceCore(model, device=device)
    kwargs: dict = {
        "input_path": str(input_path),
        "mask_path": str(mask_path),
        "output_path": str(output_path),
        "save_image": save_image,
    }
    # MatAnyone2 does int(max_size); omit when unset.
    if max_size is not None:
        kwargs["max_size"] = max_size
    process = processor.process_video
    try:
        process(**kwargs)
    except TypeError:
        kwargs.pop("save_image", None)
        kwargs.pop("max_size", None)
        process(**kwargs)
    print(f"done → {output_path}", flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml run-matte")
    p.add_argument("-i", "--input", required=True, type=Path, help="Video file or frame folder")
    p.add_argument("-m", "--mask", required=True, type=Path, help="First-frame mask PNG")
    p.add_argument("-o", "--output", required=True, type=Path, help="Output directory")
    p.add_argument("--device", default=_default_device())
    p.add_argument("--max-size", type=int, default=None)
    p.add_argument("--no-save-image", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run_matte(
        args.input,
        args.mask,
        args.output,
        device=args.device,
        max_size=args.max_size,
        save_image=not args.no_save_image,
    )
