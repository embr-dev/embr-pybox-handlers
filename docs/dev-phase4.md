# Phase 4 — MatAnyone 出力 → Batch キャッシュ再生

前提: Phase 2（cache playback）と Phase 3（Mac/Linux で run-matte）が通っていること。

## 流れ

```text
run-matte → …/out/<name>/pha/*.png
    ↓  embr-ml publish-cache
job/alpha/{frame}.exr
    ↓  handlers/embr_cache_playback.py
Batch OutMatte
```

## コマンド（Mac smoke 済み素材）

```bash
export EMBR_ML_ROOT="$HOME/embr-ml"
cd …/embr-pybox-handlers/worker

.venv/bin/python -m embr_ml.cli publish-cache \
  --pha-dir "$EMBR_ML_ROOT/jobs/mac_smoke/out/test-sample1/pha" \
  --job-dir "$EMBR_ML_ROOT/jobs/mac_smoke" \
  --start-frame 1 \
  --padding 4
```

- `00000.png` → `alpha/0001.exr`（`--start-frame 1`）
- 約 30 フレーム分

## Flame での確認

1. Handler: `handlers/embr_cache_playback.py`（**Change Handler**）  
2. **Job Folder** = `/Users/<you>/embr-ml/jobs/mac_smoke`（**`alpha` フォルダ自体は選ばない**）  
3. **Frame Padding** = 4、**Frame Offset** = 0  
4. Front はキャッシュと同じ解像度（この smoke は **1920×1080** で publish 済み）  
5. フレーム 1〜30 をスクラブ → OutMatte がマット  
6. **Log Status** → `exists=True`（path に `alpha/alpha` が二重で出ていないこと）

### 真っ黒だったときの典型原因

| 原因 | 対処 |
|------|------|
| Front と alpha の解像度不一致 | `publish-cache --width --height` で Front に合わせる |
| Job Folder が `…/alpha` | 親の job フォルダを選ぶ |
| EXR が Flame 非互換 | HALF・無圧縮で書き直し（現行 publish-cache） |

## 成功条件

- [ ] `~/embr-ml/jobs/mac_smoke/alpha/0001.exr` … `0030.exr` がある  
- [ ] Batch で 1F/30F の OutMatte がマットらしい絵になる  
- [ ] Log Status の path が上記 job を指す  
