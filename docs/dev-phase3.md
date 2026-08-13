# Phase 3 — 会社マシン想定セットアップ

## 質問: Pybox を入れてボタンを押せば完了？

**ほぼ。ただし「リポをマシンに置く」だけは先に必要。**

| 手順 | 手作業？ | 誰がやる |
|------|----------|----------|
| 1. `git clone`（または zip 展開） | **必要** | IT / 初回担当 |
| 2. Flame で Handler に `handlers/embr_ml_worker.py` を指定 | **必要** | アーティスト or TD |
| 3. UI の **Repo Root** を clone 先にする | **必要**（初回） | 同上 |
| 4. **Run Setup** | ボタン | uv 導入・venv・`pip install -e .`・ウェイト DL |
| 5. 以降の **Ensure Models** / **Worker Status** | ボタン | 再取得・確認 |

Flame 同梱 Python やシステム `pip` は汚さない。Setup はユーザー領域の `uv` と `RepoRoot/worker/.venv`、データは `~/embr-ml`。

```text
[手作業] clone + Handler 指定 + Repo Root
        ↓
[Run Setup]  uv → venv → install → ensure-models
        ↓
完了（研究用ウェイト取得まで）
```

**Run Setup がやらないこと:** CUDA ドライバ、MatAnyone2 推論用 `[matte]`（torch）の導入、社内プロキシ証明書の特別設定。推論は Linux で別途 `uv pip install -e '.[matte]'`。

## 会社向け配置例

```text
/opt/embr/embr-pybox-handlers/     # 共有 clone（推奨）または ~/embr/...
  handlers/embr_ml_worker.py
  worker/
~/embr-ml/                         # ユーザーごとの jobs/models（または共有ディスク）
```

Repo Root = `/opt/embr/embr-pybox-handlers`  
EMBR_ML_ROOT = `/home/<user>/embr-ml` または `/mnt/ai/embr-ml/<user>`

## この Mac で会社手順を練習

### ターミナルで Setup と同じこと（Flame なしでも可）

```bash
# Flame 同梱 Python でも、普通の python3 でも可
"/opt/Autodesk/python/2025/bin/python3" \
  /Users/oue.isamu/Projects/embr-pybox-handlers/worker/embr_ml/bootstrap.py \
  --repo-root /Users/oue.isamu/Projects/embr-pybox-handlers \
  --ml-root "$HOME/embr-ml"
```

### Flame で練習

1. Handler: `…/handlers/embr_ml_worker.py`（Change Handler）  
2. **Repo Root** = このリポの絶対パス  
3. **EMBR_ML_ROOT** = `~/embr-ml`  
4. **Run Setup**（数分ブロックしうる・ネット必須）  
5. **Worker Status** → `matanyone2_pth_exists=True`

## 成功条件

- [x] `RepoRoot/worker/.venv/bin/python` が存在  
- [x] `~/embr-ml/models/matanyone2/matanyone2.pth` が存在  
- [x] Pybox Status が exists=True  
- [x] Mac MPS 通し: `~/embr-ml/jobs/mac_smoke/out/`（pha/fgr mp4 + png）

### Mac 通しメモ（2026-08-12）

- `device=mps` で公式 sample1（約30F、`--max-size 512`）が成功  
- 公式 `pip install git+…` は hatch `force-include` 重複で失敗 → clone して該当行削除後 `uv pip install -e`  
- 出力例: `test-sample1_pha.mp4` / `test-sample1_fgr.mp4` / `test-sample1/pha|fgr/*.png`

詳細 CLI: [../worker/README.md](../worker/README.md)
