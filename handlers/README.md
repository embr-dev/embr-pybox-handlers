# Handlers

Flame が読む Pybox handler（`.py`）。

| Handler | Phase | Role |
|---------|-------|------|
| [embr_hello.py](./embr_hello.py) | 1 | パススルー + フレーム情報ログ |
| [embr_cache_playback.py](./embr_cache_playback.py) | 2 | Job/`alpha/{frame}.exr` を OutMatte に配信 |
| [embr_ml_worker.py](./embr_ml_worker.py) | 3 | Ensure Models / Status → uv worker subprocess |
| [embr_matte.py](./embr_matte.py) | 5 | Record Front / Capture Guide / 非同期 Run + fgr·pha 再生 |

## Flame での読み方

どちらか一方:

**A. フルパス指定（開発向き）**

1. Batch に Pybox を置く  
2. Handler にリポ内の絶対パスを指定  
   例: `/Users/<you>/Projects/embr-pybox-handlers/handlers/embr_hello.py`

**B. shared presets へリンク（運用に近い）**

```bash
ln -sf /Users/oue.isamu/Projects/embr-pybox-handlers/handlers/embr_hello.py \
  /opt/Autodesk/shared/presets/pybox/embr_hello.py
```

編集後は Flame で **Change Handler**（再起動不要）。

補助モジュールを `import` する場合は、Help どおり `pybox_v1.py` と同じディレクトリ規則に合わせること。Phase 1 の hello は単一ファイルのみ。
