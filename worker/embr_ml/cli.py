"""embr-ml CLI — intended to be invoked from shell or a thin Pybox handler."""

from __future__ import annotations

import argparse
import sys

from embr_ml import ensure_models, paths


def cmd_status(_: argparse.Namespace) -> int:
    paths.ensure_layout()
    for line in ensure_models.status_lines():
        print(line)
    return 0


def cmd_ensure_models(args: argparse.Namespace) -> int:
    paths.ensure_layout()
    ensure_models.ensure_matanyone2(force=args.force)
    for line in ensure_models.status_lines():
        print(line)
    return 0


def cmd_run_matte(args: argparse.Namespace) -> int:
    from embr_ml import run_matte

    return run_matte.main(
        [
            "-i",
            str(args.input),
            "-m",
            str(args.mask),
            "-o",
            str(args.output),
            "--device",
            args.device,
            *(["--max-size", str(args.max_size)] if args.max_size else []),
            *(["--no-save-image"] if args.no_save_image else []),
        ]
    )


def cmd_publish_cache(args: argparse.Namespace) -> int:
    from embr_ml import publish_cache

    argv = [
        "--pha-dir",
        str(args.pha_dir),
        "--job-dir",
        str(args.job_dir),
        "--start-frame",
        str(args.start_frame),
        "--padding",
        str(args.padding),
    ]
    if args.fgr_dir is not None:
        argv.extend(["--fgr-dir", str(args.fgr_dir)])
    if args.ignore_names:
        argv.append("--ignore-names")
    if args.width is not None:
        argv.extend(["--width", str(args.width)])
    if args.height is not None:
        argv.extend(["--height", str(args.height)])
    return publish_cache.main(argv)


def cmd_init_job(args: argparse.Namespace) -> int:
    from embr_ml import init_job

    return init_job.main([args.name])


def cmd_hud_overlay(args: argparse.Namespace) -> int:
    from embr_ml import hud_overlay

    return hud_overlay.main(
        [
            "--base",
            str(args.base),
            "--out",
            str(args.out),
            "--info-json",
            str(args.info_json),
            "--title",
            args.title,
        ]
    )


def cmd_process_job(args: argparse.Namespace) -> int:
    from embr_ml import process_job

    argv = ["--device", args.device]
    if args.job_dir:
        argv.extend(["--job-dir", args.job_dir])
    elif args.job:
        argv.extend(["--job", args.job])
    if args.max_size is not None:
        argv.extend(["--max-size", str(args.max_size)])
    argv.extend(
        [
            "--start-frame",
            str(args.start_frame),
            "--padding",
            str(args.padding),
        ]
    )
    if args.width is not None:
        argv.extend(["--width", str(args.width)])
    if args.height is not None:
        argv.extend(["--height", str(args.height)])
    return process_job.main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embr-ml",
        description="Embr ML worker (uv venv). Safe to call from Pybox via subprocess.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Print EMBR_ML_ROOT and weight presence")
    p_status.set_defaults(func=cmd_status)

    p_ensure = sub.add_parser(
        "ensure-models",
        help="Download MatAnyone2 weights into $EMBR_ML_ROOT/models (stdlib)",
    )
    p_ensure.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the weight file already exists",
    )
    p_ensure.set_defaults(func=cmd_ensure_models)

    p_run = sub.add_parser("run-matte", help="Run MatAnyone2 (requires matanyone2 installed)")
    p_run.add_argument("-i", "--input", required=True)
    p_run.add_argument("-m", "--mask", required=True)
    p_run.add_argument("-o", "--output", required=True)
    p_run.add_argument(
        "--device",
        default="mps" if sys.platform == "darwin" else "cuda:0",
    )
    p_run.add_argument("--max-size", type=int, default=None)
    p_run.add_argument("--no-save-image", action="store_true")
    p_run.set_defaults(func=cmd_run_matte)

    p_pub = sub.add_parser(
        "publish-cache",
        help="Convert pha PNGs → job/alpha/{frame}.exr for Phase-2 Pybox playback",
    )
    p_pub.add_argument("--pha-dir", required=True)
    p_pub.add_argument("--job-dir", required=True)
    p_pub.add_argument("--fgr-dir", default=None)
    p_pub.add_argument("--start-frame", type=int, default=1)
    p_pub.add_argument("--padding", type=int, default=4)
    p_pub.add_argument("--ignore-names", action="store_true")
    p_pub.add_argument("--width", type=int, default=None)
    p_pub.add_argument("--height", type=int, default=None)
    p_pub.set_defaults(func=cmd_publish_cache)

    p_init = sub.add_parser("init-job", help="Create jobs/<name>/{input,out,alpha}")
    p_init.add_argument("name")
    p_init.set_defaults(func=cmd_init_job)

    p_proc = sub.add_parser(
        "process-job",
        help="prepare frames + run-matte + publish alpha/fgr for a job folder",
    )
    p_proc.add_argument("--job", default=None, help="Name under $EMBR_ML_ROOT/jobs/")
    p_proc.add_argument(
        "--job-dir",
        default=None,
        help="Absolute job directory (overrides --job)",
    )
    p_proc.add_argument(
        "--device",
        default="mps" if sys.platform == "darwin" else "cuda:0",
    )
    p_proc.add_argument("--max-size", type=int, default=None)
    p_proc.add_argument("--start-frame", type=int, default=1)
    p_proc.add_argument("--padding", type=int, default=4)
    p_proc.add_argument("--width", type=int, default=None)
    p_proc.add_argument("--height", type=int, default=None)
    p_proc.set_defaults(func=cmd_process_job)

    p_hud = sub.add_parser(
        "hud-overlay",
        help="Burn status lines into an EXR for Pybox Result HUD",
    )
    p_hud.add_argument("--base", required=True)
    p_hud.add_argument("--out", required=True)
    p_hud.add_argument("--info-json", required=True)
    p_hud.add_argument("--title", default="Embr Matte")
    p_hud.set_defaults(func=cmd_hud_overlay)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
