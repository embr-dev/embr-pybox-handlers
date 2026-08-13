# embr-pybox-handlers

Pybox handlers and research notes for **Autodesk Flame** (Embr).

Part of **[Embr](https://github.com/embr-dev/Embr)**. Hooks / Script Manager は [embr-python-scripts](https://github.com/embr-dev/embr-python-scripts)。

## Status

**Embr Matte** — Record Front → Run → Result=`fgr` / OutMatte=`pha`（`dev` ブランチで開発中）。

## Handlers

| Handler | Notes |
|---------|-------|
| [handlers/embr_matte.py](./handlers/embr_matte.py) | 本番ノード（Init / Record / Guide / Run / HUD） |

ランタイム Install（uv / venv / models）は **embr-python-scripts** 側。  
Worker: [worker/README.md](./worker/README.md)  
Data root: `~/Embr/ml` — [docs/embr-home.md](./docs/embr-home.md)  
操作手順: [docs/dev-matte-run.md](./docs/dev-matte-run.md)

## Documentation

| Document | Contents |
|----------|----------|
| [docs/dev-matte-run.md](./docs/dev-matte-run.md) | Embr Matte 操作 |
| [docs/embr-home.md](./docs/embr-home.md) | `~/Embr` ランタイムレイアウト |
| [docs/handoff-embr-runtime-install.md](./docs/handoff-embr-runtime-install.md) | python-scripts 向け Install 引き継ぎ |
| [docs/dev-phase3.md](./docs/dev-phase3.md) | worker / Ensure Models |
| [docs/dev-phase3-env.md](./docs/dev-phase3-env.md) | 実行環境方針 |
| [docs/dev-own-media.md](./docs/dev-own-media.md) | 自前プレート＋マスク（CLI） |
| [docs/api/pybox.md](./docs/api/pybox.md) | Pybox API メモ |
| [docs/research/sam2-matanyone2-pybox.md](./docs/research/sam2-matanyone2-pybox.md) | SAM2 + MatAnyone2 調査 |

## Related

| Repository | Role |
|------------|------|
| [embr-python-scripts](https://github.com/embr-dev/embr-python-scripts) | Flame Python hooks / Script Manager Install |
| [embr-matchbox-shaders](https://github.com/embr-dev/embr-matchbox-shaders) | Matchbox shaders |
