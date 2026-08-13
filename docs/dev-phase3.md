# Phase 3 — 会社マシン想定セットアップ

## 質問: ボタン一つで完了？

**ほぼ。リポ配置と Install は embr-python-scripts。**

| 手順 | 手作業？ | 誰がやる |
|------|----------|----------|
| 1. `git clone`（または Install が配置） | **必要** | IT / Script Manager Install |
| 2. embr-python-scripts の **Embr runtime Install** | メニュー | uv・venv・weights |
| 3. Flame で Handler に `handlers/embr_matte.py` | **必要** | アーティスト or TD |
| 4. **Repo Root** = clone 先（初回） | **必要** | 同上 |

Flame 同梱 Python やシステム `pip` は汚さない。データは `~/Embr/ml`。

```text
[Install]  uv → venv → install → ensure-models
        ↓
[embr_matte] Record → Guide → Run
```

**Install がやらないこと:** CUDA ドライバ、社内プロキシ証明書の特別設定。推論用 `[matte]`（torch）は Linux で `uv pip install -e '.[matte]'`。

## 会社向け配置例

```text
~/Embr/repos/embr-pybox-handlers/   # Install が置く clone
  handlers/embr_matte.py
  worker/
~/Embr/ml/                          # jobs/models
```

Repo Root = `$EMBR_HOME/repos/embr-pybox-handlers`  
EMBR_ML_ROOT = `$EMBR_HOME/ml`

## ターミナルで Install 相当

```bash
"/opt/Autodesk/python/2025/bin/python3" \
  /path/to/embr-pybox-handlers/worker/embr_ml/bootstrap.py \
  --repo-root /path/to/embr-pybox-handlers \
  --ml-root "$HOME/Embr/ml"
```

## 成功条件

- [ ] `RepoRoot/worker/.venv/bin/python` が存在  
- [ ] `$EMBR_ML_ROOT/models/matanyone2/matanyone2.pth` が存在  
- [ ] `python -m embr_ml.cli status` が OK  
- [ ]（任意）短い `process-job` smoke  

詳細: [../worker/README.md](../worker/README.md) / [handoff-embr-runtime-install.md](./handoff-embr-runtime-install.md)
