# embr-pybox-handlers

Pybox handlers and research notes for **Autodesk Flame** (Embr).

Part of **[Embr](https://github.com/embr-dev/Embr)**. Hooks / Script Manager は [embr-python-scripts](https://github.com/embr-dev/embr-python-scripts)。

## Status

Phase 5: async **Embr Matte** (Record Front → Run → Result=fgr / OutMatte=pha).

## Handlers

| Handler | Phase | Notes |
|---------|-------|-------|
| [handlers/embr_hello.py](./handlers/embr_hello.py) | 1 | Passthrough + Log Frame Info |
| [handlers/embr_cache_playback.py](./handlers/embr_cache_playback.py) | 2 | OutMatte from `job/alpha/{frame}.exr` |
| [handlers/embr_ml_worker.py](./handlers/embr_ml_worker.py) | 3 | Ensure Models / Status via worker |
| [handlers/embr_matte.py](./handlers/embr_matte.py) | 5 | Record / Guide / async Run + progress notice |

Worker: [worker/README.md](./worker/README.md)  
Data root: `~/Embr/ml` (`EMBR_ML_ROOT`, under `~/Embr`) — see [docs/embr-home.md](./docs/embr-home.md)  
Checklists: [docs/dev-phase1.md](./docs/dev-phase1.md) · [docs/dev-phase2.md](./docs/dev-phase2.md) · [docs/dev-phase3.md](./docs/dev-phase3.md) · [docs/dev-phase3-env.md](./docs/dev-phase3-env.md) · [docs/dev-phase4.md](./docs/dev-phase4.md) · [docs/dev-own-media.md](./docs/dev-own-media.md) · [docs/dev-matte-run.md](./docs/dev-matte-run.md)  
Example job: [examples/phase2_job/](./examples/phase2_job/)

## Documentation

| Document | Contents |
|----------|----------|
| [docs/api/pybox.md](./docs/api/pybox.md) | Pybox API（embr-python-scripts から移植） |
| [docs/reference/official-pybox-help/](./docs/reference/official-pybox-help/) | Flame 2025 公式 Help HTML |
| [docs/research/sam2-matanyone2-pybox.md](./docs/research/sam2-matanyone2-pybox.md) | SAM2 + MatAnyone 2 調査と実装検討 |
| [docs/dev-phase1.md](./docs/dev-phase1.md) | Phase 1 動作確認手順 |
| [docs/dev-phase2.md](./docs/dev-phase2.md) | Phase 2 キャッシュ再生手順 |
| [docs/dev-phase3.md](./docs/dev-phase3.md) | Phase 3 worker / Pybox Ensure Models |
| [docs/dev-phase4.md](./docs/dev-phase4.md) | Phase 4 publish-cache → Batch 再生 |
| [docs/embr-home.md](./docs/embr-home.md) | `~/Embr` ランタイムレイアウト |
| [docs/handoff-embr-runtime-install.md](./docs/handoff-embr-runtime-install.md) | python-scripts 向け Install 引き継ぎ（uv を Embr 下へ） |
| [docs/dev-matte-run.md](./docs/dev-matte-run.md) | Embr Matte 非同期 Run / status.json |
| [docs/dev-phase3-env.md](./docs/dev-phase3-env.md) | Phase 3 実行環境方針（インストール前） |

## Related

| Repository | Role |
|------------|------|
| [embr-python-scripts](https://github.com/embr-dev/embr-python-scripts) | Flame Python hooks |
| [embr-matchbox-shaders](https://github.com/embr-dev/embr-matchbox-shaders) | Matchbox shaders |

## License

MIT for Embr-authored code in this repository. Third-party models (SAM 2, MatAnyone 2, etc.) keep their own licenses — see research notes.
