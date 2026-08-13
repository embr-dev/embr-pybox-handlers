"""Run MatAnyone2 + publish-cache for a standard job folder."""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

from embr_ml import job_status, paths, prepare_frames, publish_cache, run_matte


def _resolve_job(name: str | None, job_dir: str | None) -> Path:
    if job_dir:
        job = Path(job_dir).expanduser().resolve()
        if job.name.lower() in {"alpha", "fgr", "input", "out"}:
            job = job.parent
        return job
    if not name:
        raise ValueError("specify --job or --job-dir")
    return (paths.jobs_dir() / name).resolve()


def _find_pha_dir(out_dir: Path) -> Path:
    direct = out_dir / "pha"
    if direct.is_dir() and any(direct.glob("*.png")):
        return direct
    matches = sorted(out_dir.glob("*/pha"))
    for pha in matches:
        if any(pha.glob("*.png")):
            return pha
    raise FileNotFoundError(f"no pha PNG folder under {out_dir} after run-matte")


def _find_fgr_dir(out_dir: Path) -> Path | None:
    direct = out_dir / "fgr"
    if direct.is_dir() and any(direct.glob("*.png")):
        return direct
    matches = sorted(out_dir.glob("*/fgr"))
    for fgr in matches:
        if any(fgr.glob("*.png")):
            return fgr
    return None


def _count_pha_pngs(out_dir: Path) -> int:
    n = 0
    for folder in [out_dir / "pha", *out_dir.glob("*/pha")]:
        if folder.is_dir():
            n = max(n, len(list(folder.glob("*.png"))))
    return n


def process_job(
    name: str | None = None,
    *,
    job_dir: str | None = None,
    device: str | None = None,
    max_size: int | None = None,
    start_frame: int = 1,
    padding: int = 4,
    width: int | None = None,
    height: int | None = None,
) -> int:
    paths.ensure_layout()
    try:
        job = _resolve_job(name, job_dir)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not job.is_dir():
        print(
            f"job not found: {job}\n"
            f"Create it with:  python -m embr_ml.cli init-job <name>\n"
            f"Or point Pybox Job Folder at an existing job directory.",
            file=sys.stderr,
        )
        return 2

    job_status.write_pid(job)
    job_status.write_status(
        job,
        state="running",
        phase="prepare",
        current=0,
        total=0,
        message="preparing RGB frames + mask",
        job_path=str(job),
    )

    stop = threading.Event()
    watcher: threading.Thread | None = None

    try:
        rgb_dir, mask_png, n_frames, detected_size = prepare_frames.prepare_rgb_and_mask(
            job
        )
        size = (width, height) if width and height else detected_size
        out_dir = job / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"input_rgb={rgb_dir} ({n_frames} frames)", flush=True)
        print(f"mask={mask_png}", flush=True)
        print(f"out={out_dir}", flush=True)
        print(f"size={size[0]}x{size[1]}", flush=True)

        job_status.write_status(
            job,
            state="running",
            phase="matte",
            current=0,
            total=n_frames,
            message="MatAnyone2 inference",
            width=size[0],
            height=size[1],
        )

        def _watch() -> None:
            while not stop.wait(0.75):
                cur = _count_pha_pngs(out_dir)
                job_status.write_status(
                    job,
                    state="running",
                    phase="matte",
                    current=cur,
                    total=n_frames,
                    message="MatAnyone2 inference",
                )

        watcher = threading.Thread(target=_watch, name="pha-watch", daemon=True)
        watcher.start()

        rc = run_matte.run_matte(
            rgb_dir,
            mask_png,
            out_dir,
            device=device,
            max_size=max_size,
            save_image=True,
        )
        stop.set()
        if watcher is not None:
            watcher.join(timeout=2.0)
        if rc != 0:
            job_status.write_status(
                job,
                state="error",
                phase="matte",
                message=f"run-matte exit {rc}",
            )
            return rc

        job_status.write_status(
            job,
            state="running",
            phase="publish",
            current=n_frames,
            total=n_frames,
            message="publishing alpha + fgr EXR",
        )

        pha = _find_pha_dir(out_dir)
        publish_cache.publish_pha_to_alpha(
            pha,
            job,
            start_frame=start_frame,
            padding=padding,
            size=size,
        )
        fgr = _find_fgr_dir(out_dir)
        if fgr is not None:
            publish_cache.publish_fgr_to_cache(
                fgr,
                job,
                start_frame=start_frame,
                padding=padding,
                size=size,
            )
        else:
            print("WARNING: no fgr PNGs; Result will stay Front passthrough", flush=True)

        job_status.write_status(
            job,
            state="done",
            phase="done",
            current=n_frames,
            total=n_frames,
            message="ready for Pybox scrub",
            alpha=str(job / "alpha"),
            fgr=str(job / "fgr"),
        )
        print(f"DONE job={job}", flush=True)
        print(f"Pybox Job Folder → {job}", flush=True)
        return 0
    except Exception as exc:
        stop.set()
        job_status.write_status(
            job,
            state="error",
            phase="error",
            message=str(exc),
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        job_status.clear_pid(job)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml process-job")
    p.add_argument("--job", default=None, help="Name under $EMBR_ML_ROOT/jobs/")
    p.add_argument(
        "--job-dir",
        default=None,
        help="Absolute job folder (Pybox Job Folder). Overrides --job.",
    )
    p.add_argument(
        "--device",
        default="mps" if sys.platform == "darwin" else "cuda:0",
    )
    p.add_argument("--max-size", type=int, default=None)
    p.add_argument("--start-frame", type=int, default=1)
    p.add_argument("--padding", type=int, default=4)
    p.add_argument("--width", type=int, default=None, help="Must match Batch Front")
    p.add_argument("--height", type=int, default=None, help="Must match Batch Front")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.job and not args.job_dir:
        print("error: need --job or --job-dir", file=sys.stderr)
        return 2
    return process_job(
        args.job,
        job_dir=args.job_dir,
        device=args.device,
        max_size=args.max_size,
        start_frame=args.start_frame,
        padding=args.padding,
        width=args.width,
        height=args.height,
    )
