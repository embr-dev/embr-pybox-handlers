# 自分のプレート + 第1フレームマスク（SAM2 なし）

SAM2 は今回スキップ。マスクは Flame で用意する。

## 全体フロー

```text
Flame: プレート書き出し → job/input/
Flame: 第1Fマスク書き出し → job/mask.png
        ↓
embr-ml process-job  （run-matte + publish-cache）
        ↓
job/alpha/{frame}.exr
        ↓
Pybox embr_cache_playback（Job Folder = job）
```

## 1. ジョブフォルダを作る

```bash
export EMBR_ML_ROOT="$HOME/embr-ml"
cd /Users/oue.isamu/Projects/embr-pybox-handlers/worker

.venv/bin/python -m embr_ml.cli init-job myshot
```

できる場所:

```text
~/embr-ml/jobs/myshot/
  input/          ← ここにプレート
  mask.png        ← 第1フレームマスク（自分で置く）
  out/
  alpha/
  README.md
```

ジョブ名 `myshot` は任意（英数字・`._-`）。

## 2. Flame から素材を入れる

### プレート → `input/`

どちらか:

- **連番画像**（推奨）: `input/0001.jpg` … または png  
- **短い動画**: `input/clip.mp4` / `.mov` を1本  

解像度・長さは本番プレートに合わせる。まずは短く（2〜5秒）でよい。

### 第1フレームマスク → `mask.png`

1. Batch / Timeline で **先頭フレーム**の被写体を塗る／キーする（白＝残す、黒＝抜く）  
2. その1枚を **PNG** で書き出し  
3. `~/embr-ml/jobs/myshot/mask.png` に置く（ファイル名固定）  
4. **プレートと同じ解像度**であること  

粗いシルエットで十分（髪の細部は MatAnyone 側）。

## 3. 推論 + キャッシュ化

Front が 1920×1080、Batch 先頭が 1 の例:

```bash
.venv/bin/python -m embr_ml.cli process-job \
  --job myshot \
  --device mps \
  --start-frame 1 \
  --padding 4 \
  --width 1920 \
  --height 1080
```

- Mac: `--device mps`  
- Linux CUDA: `--device cuda:0`  
- Batch の開始フレームが 1001 なら `--start-frame 1001`  
- **`--width/--height` は Front と必ず一致**（不一致だと真っ黒）

## 4. Batch 再生

1. Handler: `handlers/embr_cache_playback.py`  
2. Job Folder: `/Users/<you>/embr-ml/jobs/myshot`（`alpha` は選ばない）  
3. Front = 同じプレート  
4. スクラブして OutMatte を確認  
5. Log Status で `exists=True`

## チェックリスト

- [ ] `input/` にプレートがある  
- [ ] `mask.png` がある（第1F・同解像度）  
- [ ] `process-job` が完了し `alpha/*.exr` がある  
- [ ] publish の width/height = Front  
- [ ] Batch でマットが見える  

問題が出たら Log Status の path と、Front の解像度・開始フレームを共有してください。
