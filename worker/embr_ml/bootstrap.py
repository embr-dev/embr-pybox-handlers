"""
Bootstrap uv venv + package install for company / offline-Flame setups.

Callable from:
  - CLI:  python3 -m embr_ml.bootstrap --repo-root /path/to/embr-pybox-handlers
  - Pybox: subprocess to this module using *any* python3 (Flame's is fine)

Does not import torch. Network required for uv install + weight download.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _which(name: str) -> str | None:
    return shutil.which(name)


def find_uv() -> Path | None:
    """Prefer Embr-local uv; never require ~/.local on PATH."""
    from embr_ml import paths as embr_paths

    candidates: list[Path] = []
    env_uv = os.environ.get("EMBR_UV", "").strip()
    if env_uv:
        candidates.append(Path(env_uv).expanduser())
    candidates.append(embr_paths.uv_path())
    # Compat only — do not install here anymore.
    which = _which("uv")
    if which:
        candidates.append(Path(which))
    home = Path.home()
    candidates.extend(
        [
            home / ".local" / "bin" / "uv",
            home / ".cargo" / "bin" / "uv",
            Path("/usr/local/bin/uv"),
            Path("/opt/homebrew/bin/uv"),
        ]
    )
    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except Exception:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    return None


def install_uv() -> Path:
    """Install uv into $EMBR_HOME/bin (not ~/.local)."""
    from embr_ml import paths as embr_paths

    embr_paths.ensure_layout()
    preferred = embr_paths.uv_path()
    if preferred.is_file() and os.access(preferred, os.X_OK):
        print(f"uv already present: {preferred}", flush=True)
        return preferred

    existing = find_uv()
    # If only a system/user uv exists, still install a copy under Embr when missing.
    if existing and existing == preferred:
        print(f"uv already present: {existing}", flush=True)
        return existing

    curl = _which("curl")
    if not curl:
        raise RuntimeError(
            "curl not found. Install curl or place uv at "
            f"{preferred} manually, then re-run Setup."
        )

    install_dir = str(embr_paths.bin_dir())
    Path(install_dir).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["UV_INSTALL_DIR"] = install_dir
    env["PATH"] = install_dir + os.pathsep + env.get("PATH", "")

    print(f"installing uv into {install_dir} (Embr-local)", flush=True)
    proc = subprocess.run(
        [curl, "-LsSf", "https://astral.sh/uv/install.sh"],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
    )
    subprocess.run(["/bin/sh"], input=proc.stdout, check=True, env=env)

    if preferred.is_file() and os.access(preferred, os.X_OK):
        print(f"uv installed: {preferred}", flush=True)
        return preferred.resolve()

    uv = find_uv()
    if not uv:
        raise RuntimeError(
            f"uv install finished but binary not found at {preferred}."
        )
    print(f"uv installed: {uv}", flush=True)
    return uv


def _uv_env() -> dict:
    from embr_ml import paths as embr_paths

    env = os.environ.copy()
    embr_bin = str(embr_paths.bin_dir())
    env["PATH"] = embr_bin + os.pathsep + env.get("PATH", "")
    env["EMBR_HOME"] = str(embr_paths.embr_home())
    env["EMBR_ML_ROOT"] = str(embr_paths.ml_root())
    env["EMBR_UV"] = str(embr_paths.uv_path())
    env.setdefault("HF_HOME", str(embr_paths.hf_home()))
    return env


def worker_dir(repo_root: Path) -> Path:
    return (repo_root / "worker").resolve()


def venv_python(repo_root: Path) -> Path:
    w = worker_dir(repo_root)
    if sys.platform == "win32":
        return w / ".venv" / "Scripts" / "python.exe"
    return w / ".venv" / "bin" / "python"


def ensure_venv(repo_root: Path, *, python_version: str = "3.10") -> Path:
    uv = install_uv()
    w = worker_dir(repo_root)
    if not w.is_dir():
        raise FileNotFoundError(f"worker/ not found under repo: {w}")

    py = venv_python(repo_root)
    env = _uv_env()
    if not py.is_file():
        print(f"creating venv ({python_version}) in {w / '.venv'}", flush=True)
        subprocess.run(
            [str(uv), "venv", "--python", python_version],
            cwd=str(w),
            check=True,
            env=env,
        )
    else:
        print(f"venv exists: {py}", flush=True)

    print("uv pip install -e .  (numpy / Pillow / OpenEXR)", flush=True)
    subprocess.run(
        [str(uv), "pip", "install", "-e", "."],
        cwd=str(w),
        check=True,
        env=env,
    )
    # Re-assert media deps even if an older empty editable was already linked.
    print("uv pip install numpy Pillow OpenEXR", flush=True)
    subprocess.run(
        [str(uv), "pip", "install", "numpy", "Pillow", "OpenEXR"],
        cwd=str(w),
        check=True,
        env=env,
    )
    if not py.is_file():
        raise RuntimeError(f"venv python missing after install: {py}")
    _verify_media_imports(py)
    return py


def _verify_media_imports(py: Path) -> None:
    print("verify: import numpy, PIL, OpenEXR", flush=True)
    subprocess.run(
        [
            str(py),
            "-c",
            "import numpy, PIL, OpenEXR; print('media_imports_ok')",
        ],
        check=True,
    )


def ensure_models(repo_root: Path, ml_root: Path, *, force: bool = False) -> None:
    py = venv_python(repo_root)
    if not py.is_file():
        raise RuntimeError("venv missing; run ensure_venv first")
    env = os.environ.copy()
    env["EMBR_ML_ROOT"] = str(ml_root)
    env.setdefault("HF_HOME", str(ml_root / "models" / "hf"))
    cmd = [str(py), "-m", "embr_ml.cli", "ensure-models"]
    if force:
        cmd.append("--force")
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def run_setup(
    repo_root: Path,
    ml_root: Path,
    *,
    force_models: bool = False,
    python_version: str = "3.10",
) -> Path:
    """
    Full company-style setup:
      uv (if needed) → venv → pip install -e . → ensure-models
    Returns path to worker venv python.
    """
    repo_root = repo_root.expanduser().resolve()
    ml_root = ml_root.expanduser().resolve()
    ml_root.mkdir(parents=True, exist_ok=True)
    print(f"repo_root={repo_root}", flush=True)
    print(f"ml_root={ml_root}", flush=True)
    py = ensure_venv(repo_root, python_version=python_version)
    ensure_models(repo_root, ml_root, force=force_models)
    print(f"SETUP_OK worker_python={py}", flush=True)
    return py


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="embr-ml-bootstrap")
    p.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="Path to embr-pybox-handlers clone",
    )
    p.add_argument(
        "--ml-root",
        type=Path,
        default=None,
        help="Data root (default: $EMBR_ML_ROOT or ~/Embr/ml)",
    )
    p.add_argument("--force-models", action="store_true")
    p.add_argument("--python-version", default="3.10")
    return p


def main(argv: list[str] | None = None) -> None:
    from embr_ml import paths as embr_paths

    args = build_parser().parse_args(argv)
    ml = args.ml_root if args.ml_root is not None else embr_paths.ml_root()
    run_setup(
        args.repo_root,
        ml,
        force_models=args.force_models,
        python_version=args.python_version,
    )


if __name__ == "__main__":
    main()
