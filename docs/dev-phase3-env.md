# Phase 3 — 実行環境方針（インストール前検討）

目的: MatAnyone2 /（後で）SAM2 を **システム Python・Flame 同梱 Python を汚さず** 動かす。  
対象: 社内研究（S-Lab License は非商用。研究利用は条文上の non-commercial に寄せて運用）。

**この文書は方針のみ。パッケージの実インストールは合意後。**

---

## 1. 結論（推奨）

| 用途 | 推奨 | 理由 |
|------|------|------|
| **開発 Mac（このマシン）で CLI 骨格・パス検証** | **uv + プロジェクトローカル `.venv`** | 公式が uv 対応。Miniforge より軽く、削除が `rm -rf` で完結 |
| **実際の GPU 推論（本番に近い）** | **Linux + NVIDIA + 同上（uv）または Miniforge** | MatAnyone2 API 例は `device="cuda:0"`。macOS では実用速度・対応が弱い |
| **社内共有・再現性を最優先** | Linux 上で **Docker/Podman（CUDA イメージ）** | OS をほぼ汚さない。マシン間で同じ lock |

**Miniforge は悪くない**（CorridorKey 先例・科学計算向け）が、MatAnyone2 単体なら **まず uv で足りる**。conda が必要になるのは「CUDA toolkit や ffmpeg を conda-forge で揃えたい」とき。

避けるもの:

- macOS / Homebrew のシステム `python3` への `pip install`
- Flame `/opt/Autodesk/python/2025` への追加パッケージ
- ユーザー全域の `~/.local` へ無計画に入れる運用

---

## 2. ツール比較

| 方式 | 分離の強さ | 重さ | MatAnyone2 との相性 | 向く場面 |
|------|------------|------|---------------------|----------|
| **uv + `.venv`** | 高（ディレクトリ単位） | 軽い | 公式 README に記載 | **第一候補** |
| **Miniforge / mamba** | 高（env 名単位） | 中〜大 | 公式 conda 手順あり | CUDA/ffmpeg を conda で揃えたい、既存 conda 文化 |
| **pixi** | 高 + lockfile | 中 | 良好 | チームで lock を Git 管理したい |
| **Docker + CUDA** | 最大 | 大 | 自前 Dockerfile | 共有 Linux サーバ、完全隔離 |
| **pyenv + venv** | 中 | 中 | 可 | 既に pyenv がある場合のみ |

---

## 3. マシン役割の分け方（重要）

現開発機は **macOS + Flame**。

| マシン | やること | やらないこと |
|--------|----------|--------------|
| **Flame Mac** | Pybox、ジョブフォルダ、短いパス試験、（任意）CPU/MPS の極小テスト | 長尺・本番品質の CUDA 推論を Flame と同時実行 |
| **Linux GPU（推奨）** | MatAnyone2 / SAM2 本推論、weights キャッシュ | Flame を載せない方が楽（VRAM 競合回避） |

公式 API は `cuda:0` 前提。Apple 向けは第三者の Core ML 移植（MatAnyone2Kit）があり、**研究の本線（元リポ）とは別物**として扱う。

社内研究の現実的パターン:

1. Mac で Pybox ジョブを切る → 素材を共有ストレージへ  
2. Linux GPU で worker CLI 実行 → `alpha/` を同じジョブに書き戻す  
3. Mac Flame でフェーズ 2 handler が再生  

同一 Linux に Flame があるなら、**時間帯をずらす**か解像度を抑える（CorridorKey も VRAM 警告あり）。

---

## 4. インストール先（案）

リポジトリ本体と **環境・ウェイトを分離**する。

**名前について:** 以前の `EmbrResearch` は仮置きであり、必須の正式名ではない。  
推奨の既定名は **`embr-ml`**（短く、製品コードとデータ領域の区別が付き、研究専用に縛らない）。  
環境変数でルートを差し替え可能にする。

```text
# コード（Git）
~/Projects/embr-pybox-handlers/   # または Linux 上の clone
  worker/                         # CLI・lock（後で追加）
  worker/.venv/                   # uv（gitignore）

# データ・モデル（Git に入れない）— マシンローカル既定
~/embr-ml/
  jobs/
  models/
    hf/                           # Hugging Face キャッシュ
    matanyone2/
    sam2/
```

| マシン | データ root の置き方 |
|--------|----------------------|
| **Mac（サブ）** | `~/embr-ml`（ユーザー領域。sudo 不要、削除容易） |
| **Linux（メイン）** 個人検証 | 同様に `~/embr-ml` |
| **Linux** 複数人・Flame と共有ディスク | `/opt/embr/ml` またはスタジオの共有（例: `/mnt/ai/embr-ml`）。`/opt/Autodesk` 配下は使わない |

| パス | 内容 | Git |
|------|------|-----|
| `worker/.venv` | Python 環境 | **否** |
| `$EMBR_ML_ROOT/models` | ウェイト | **否** |
| `/opt/Autodesk/**` | — | 触らない |

```bash
export EMBR_ML_ROOT="${EMBR_ML_ROOT:-$HOME/embr-ml}"
export HF_HOME="$EMBR_ML_ROOT/models/hf"
export EMBR_MATANYONE2_WEIGHTS="$EMBR_ML_ROOT/models/matanyone2"
```
---

## 5. 推奨セットアップ手順（合意後に実行）

### A. uv（第一候補）

```bash
# 1) uv 本体のみ（ユーザー領域。システム Python は汚さない）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2) リポ内 worker
cd ~/Projects/embr-pybox-handlers
mkdir -p worker && cd worker
uv venv --python 3.10
uv pip install "matanyone2 @ git+https://github.com/pq-yang/MatAnyone2.git"
# Linux CUDA 時は先に公式 index で torch を入れることが多い

# 3) 実行は常に venv 経由
uv run matanyone2 --help
```

削除: `rm -rf worker/.venv` と `~/EmbrResearch/models`（必要なら）。

### B. Miniforge（conda が欲しい場合）

```bash
# Miniforge3 をホームに入れる（公式インストーラ）
conda create -n embr-matanyone2 python=3.10 -y
conda activate embr-matanyone2
pip install "matanyone2 @ git+https://github.com/pq-yang/MatAnyone2.git"
```

シェルの自動 `conda init` が嫌なら、`conda activate` を worker スクリプト内だけにする。

### C. Docker（共有 Linux）

- ベース: NVIDIA Container Toolkit 対応イメージ  
- マウント: `jobs/` と `models/` のみホストから  
- Flame ホストとは分離  

---

## 6. ライセンス・運用メモ（研究）

- MatAnyone2: **S-Lab 1.0 / 非商用**。社内研究は可でも、成果の外部商用利用・再配布は別途許諾。  
- ウェイトは GitHub Releases / Hugging Face から **利用者マシンの `EmbrResearch/models` に取得**（リポに同梱しない）。  
- SAM2 は Apache-2.0（後段で追加しやすい）。  
- README / 社内 Wiki に「研究用・非商用」を明記する。

---

## 7. 決めてから進むチェックリスト

インストール前に合意したいこと:

1. **推論マシン**は Mac か Linux GPU か  
2. ツールは **uv** でよいか（否なら Miniforge / Docker）  
3. データ root は **`~/embr-ml`**（共有なら `/opt/embr/ml` 等。`EMBR_ML_ROOT` で上書き）  
4. 研究利用の範囲（社内のみ / デモ公開の有無）

合意後の実装順:

1. `.gitignore` に `worker/.venv` を追加  
2. `worker/` に README + 薄い `run_matte.sh`  
3. 極短クリップで CLI 1 本通す（Linux メイン）  
4. 出力をフェーズ 2 の `alpha/` 規約に合わせる  
5. Mac は同じ `EMBR_ML_ROOT` レイアウトで経路試験のみ  

---

## 8. この Mac だけで始める場合の期待値

- 環境分離・CLI 引数・ジョブフォルダ連携の試験 → **十分意味がある**  
- 実用速度のマット品質検証 → **Linux CUDA をメインにする**  
- Flame 起動中に重い推論 → **非推奨**

## 9. フォルダ名メモ（EmbrResearch について）

`EmbrResearch` に特別な公式根拠はない（検討時の仮名）。  
採用しない理由になりうる点: CamelCase、`Research` が用途を狭く見せる、既存 Embr リポが kebab-case（`embr-pybox-handlers`）なこと。  
既定は **`embr-ml`** とする。