"""Path helpers for Embr home + ML data root (jobs + model weights).

Layout (uninstall-friendly):

  ~/Embr/                 $EMBR_HOME
    bin/uv                $EMBR_UV (do not install to ~/.local)
    ml/                   $EMBR_ML_ROOT  (jobs, models, src)
    tools/                future AI tool data
    repos/                preferred: embr-pybox-handlers clone
    venvs/                optional shared venvs

Override with env: EMBR_HOME, EMBR_ML_ROOT, EMBR_UV.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_EMBR_HOME_NAME = "Embr"
DEFAULT_ML_DIRNAME = "ml"
DEFAULT_HANDLERS_REPO_NAME = "embr-pybox-handlers"


def embr_home() -> Path:
    """Product home: $EMBR_HOME or ~/Embr."""
    override = os.environ.get("EMBR_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / DEFAULT_EMBR_HOME_NAME).resolve()


def ml_root() -> Path:
    """ML data root: $EMBR_ML_ROOT or $EMBR_HOME/ml."""
    override = os.environ.get("EMBR_ML_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (embr_home() / DEFAULT_ML_DIRNAME).resolve()


def bin_dir() -> Path:
    return embr_home() / "bin"


def uv_path() -> Path:
    """Preferred uv binary: $EMBR_UV or $EMBR_HOME/bin/uv."""
    override = os.environ.get("EMBR_UV", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (bin_dir() / "uv").resolve()


def models_dir() -> Path:
    return ml_root() / "models"


def jobs_dir() -> Path:
    return ml_root() / "jobs"


def matanyone2_dir() -> Path:
    return models_dir() / "matanyone2"


def sam2_dir() -> Path:
    return models_dir() / "sam2"


def hf_home() -> Path:
    return models_dir() / "hf"


def tools_dir() -> Path:
    return embr_home() / "tools"


def repos_dir() -> Path:
    return embr_home() / "repos"


def venvs_dir() -> Path:
    return embr_home() / "venvs"


def default_handlers_repo() -> Path:
    """Preferred clone path under $EMBR_HOME/repos/."""
    return (repos_dir() / DEFAULT_HANDLERS_REPO_NAME).resolve()


def ensure_layout() -> Path:
    """Create standard directories; return ml root."""
    home = embr_home()
    root = ml_root()
    for path in (
        home,
        bin_dir(),
        root,
        jobs_dir(),
        models_dir(),
        matanyone2_dir(),
        sam2_dir(),
        hf_home(),
        tools_dir(),
        repos_dir(),
        venvs_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)
    readme = home / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# Embr\n\n"
            "All Embr AI runtime data lives under this folder.\n\n"
            "## Uninstall\n\n"
            "```bash\nrm -rf ~/Embr\n"
            "rm -f ~/embr-ml\n"
            "```\n\n"
            "Does **not** remove Autodesk Flame or hooks under "
            "`…/python/Embr/`.\n\n"
            "## Layout\n\n"
            "- `bin/uv` — Embr-only uv (`EMBR_UV`)\n"
            "- `ml/` — jobs, model weights (`EMBR_ML_ROOT`)\n"
            "- `tools/` — future AI tool data\n"
            "- `repos/` — preferred clones (e.g. embr-pybox-handlers)\n"
            "- `venvs/` — optional shared virtualenvs\n",
            encoding="utf-8",
        )
    return root
