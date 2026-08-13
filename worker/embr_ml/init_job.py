"""Create a standard per-shot job folder for own plate + first-frame mask."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from embr_ml import paths

JOB_README = """# Embr ML job: {name}

## Layout

```text
{name}/
  input/     # Record Front (EXR/PNG) or exported plate
  mask.exr   # Capture Guide Matte (or mask.png)
  out/       # MatAnyone2 raw output
  alpha/     # OutMatte cache
  fgr/       # Result cache
  status.json
```

## Preferred: Pybox Embr Matte

Handler: `handlers/embr_matte.py`  
See repo `docs/dev-matte-run.md`.

## CLI

```bash
export EMBR_ML_ROOT="$HOME/Embr/ml"
cd /path/to/embr-pybox-handlers/worker
.venv/bin/python -m embr_ml.cli process-job --job {name} --device mps
```
"""


def _safe_name(name: str) -> str:
    name = name.strip().replace(" ", "_")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError(
            f"invalid job name {name!r}; use letters, digits, . _ - only"
        )
    return name


def init_job(name: str) -> Path:
    paths.ensure_layout()
    name = _safe_name(name)
    root = paths.jobs_dir() / name
    (root / "input").mkdir(parents=True, exist_ok=True)
    (root / "out").mkdir(parents=True, exist_ok=True)
    (root / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "fgr").mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    readme.write_text(JOB_README.format(name=name), encoding="utf-8")
    mask = root / "mask.png"
    if not mask.exists():
        # Placeholder note file so the folder is obvious in Finder.
        (root / "PUT_mask.png_HERE.txt").write_text(
            "Save your first-frame mask as mask.png in this folder "
            "(same resolution as the plate).\n",
            encoding="utf-8",
        )
    print(f"job={root}", flush=True)
    print(f"input={root / 'input'}", flush=True)
    print(f"mask={root / 'mask.png'}  (create this)", flush=True)
    return root


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml init-job")
    p.add_argument("name", help="Job name under $EMBR_ML_ROOT/jobs/")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    init_job(args.name)
    return 0
