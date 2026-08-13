# Embr ML worker (`uv`)

Isolated CLI for model download and (later) MatAnyone2 inference.  
Flame / system Python are never modified.

## Layout

| Path | Role |
|------|------|
| `worker/.venv` | uv virtualenv (gitignored) |
| `$EMBR_ML_ROOT` | Data root — default `~/embr-ml` |
| `$EMBR_ML_ROOT/models/matanyone2/` | Weight files |
| `$EMBR_ML_ROOT/jobs/` | Shot jobs |

## Setup

ランタイム Install は **embr-python-scripts**（Script Manager）。  
CLI でも同じ bootstrap を呼べます。 See [docs/dev-phase3.md](../docs/dev-phase3.md)。

## One-time setup (terminal)

```bash
# Any python3 is fine (Flame's python also works to launch bootstrap)
python3 worker/embr_ml/bootstrap.py \
  --repo-root /path/to/embr-pybox-handlers \
  --ml-root "$HOME/embr-ml"
```

Or step by step:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd /path/to/embr-pybox-handlers/worker
uv venv --python 3.10
uv pip install -e .
export EMBR_ML_ROOT="${EMBR_ML_ROOT:-$HOME/embr-ml}"
uv run embr-ml ensure-models
```

MatAnyone2 **inference** (Linux + NVIDIA recommended):

```bash
uv pip install "matanyone2 @ git+https://github.com/pq-yang/MatAnyone2.git"
uv run embr-ml run-matte -i VIDEO_OR_FRAMES -m MASK.png -o OUTDIR --device cuda:0
```

## License

MatAnyone2 weights/code: NTU S-Lab License 1.0 (**non-commercial**). Research OK; do not commit weights to git.
