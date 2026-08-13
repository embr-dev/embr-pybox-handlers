# Handlers

Flame が読む Pybox handler（`.py`）。

| Handler | Role |
|---------|------|
| [embr_matte.py](./embr_matte.py) | 本番: Record / Guide / async Run + HUD / fgr·pha |

ランタイム Setup（uv / venv / models）は **embr-python-scripts** の Install。

## Flame での読み方

1. Batch に Pybox を置く  
2. Handler に絶対パスを指定  
   例: `…/embr-pybox-handlers/handlers/embr_matte.py`  
3. 編集後は **Change Handler**（再起動不要）

手順: [docs/dev-matte-run.md](../docs/dev-matte-run.md)
