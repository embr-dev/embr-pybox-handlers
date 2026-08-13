# 引き継ぎ: Embr ランタイム install（`embr-python-scripts` 向け）

作成日: 2026-08-13  
対象リポ: **`embr-python-scripts`**（インストール UI / Script Manager 連携）  
関連リポ: **`embr-pybox-handlers`**（Pybox + ML worker）

目的: **システム（`~/.local` 等）を極力汚さず**、AI / Pybox ランタイムを **`~/Embr` 配下に閉じる**。  
特に **uv も `~/Embr/bin/uv` に置き、そこだけを使う**。

---

## 1. 背景（現状の問題）

| いま | 問題 |
|------|------|
| `bootstrap` が Astral 公式 install で **`~/.local/bin/uv`** に入れる | Embr 専用なのにユーザー全体のパスを汚す |
| データは `~/Embr/ml` に移行済み | ツール本体（uv）だけ外に残っている |
| 開発 clone は `Projects/embr-pybox-handlers`、venv は `worker/.venv` | アンインストールが「複数場所」になりやすい |

方針: **`$EMBR_HOME`（既定 `~/Embr`）が唯一のランタイム根**。  
`rm -rf ~/Embr`（＋互換リンク削除）でほぼ消える状態を目指す。

---

## 2. 目標レイアウト

```text
~/Embr/                          # $EMBR_HOME
  README.md
  bin/
    uv                           # ★ Embr 専用 uv（PATH に常駐させない）
  ml/                            # $EMBR_ML_ROOT
    jobs/
    models/
      matanyone2/
      hf/                        # HF_HOME 推奨先
    src/                         # 例: MatAnyone2 ローカル clone
  tools/                         # 今後の AI ツール用データ
  repos/
    embr-pybox-handlers/         # 推奨: handlers + worker の clone
  venvs/                         # 任意: 共有 venv（将来）
                                 # 当面は repos/.../worker/.venv でも可

~/embr-ml → ~/Embr/ml            # 旧パス互換（任意・移行済みマシンあり）
```

### 環境変数（契約）

| 変数 | 既定 | 意味 |
|------|------|------|
| `EMBR_HOME` | `~/Embr` | Embr ランタイム根 |
| `EMBR_ML_ROOT` | `$EMBR_HOME/ml` | jobs / models / src |
| `EMBR_UV` | `$EMBR_HOME/bin/uv` | 使う uv の絶対パス（推奨） |
| `HF_HOME` | `$EMBR_ML_ROOT/models/hf` | Hugging Face キャッシュ（Setup 時に設定） |

**グローバル PATH に `~/Embr/bin` を足さない**のが望ましい。  
常に `$EMBR_UV` または絶対パスで呼ぶ → シェル全体を汚さない。

---

## 3. 責務分担

| リポ | やること |
|------|----------|
| **`embr-python-scripts`** | ユーザー向け **Install / Repair / Uninstall**（メニュー or Script Manager）。`~/Embr` 作成、uv 配置、handlers リポ配置、bootstrap 起動、状態表示 |
| **`embr-pybox-handlers`** | `worker/embr_ml/bootstrap.py` が **Embr 配下の uv を優先**。Pybox handler（`embr_matte`）。推論 CLI |

Flame hooks のインストール先（`…/python/Embr/`）と **`~/Embr` ランタイムは別物**:

- `…/python/Embr/` … Script Manager が入れる **Python hooks パッケージ**
- `~/Embr/` … **AI / uv / jobs / weights**（本資料の対象）

名前が似ているので UI 文言では「Embr runtime (`~/Embr`)」と「Embr scripts (`python/Embr`)」を区別すること。

---

## 4. `embr-python-scripts` に作るもの（提案）

### 4.1 推奨エントリ

例（名前は任せる）:

- メニュー: `Embr → AI Runtime → Install / Update`
- または Script Manager の別チャネル／メタパッケージ `embr_ai_runtime`
- CLI（TD 用）: `tools/install_embr_runtime.py`（Flame 無しでも動く）

### 4.2 Install が行う手順（順序固定）

1. **`EMBR_HOME` 決定**（既定 `~/Embr`、上書き可）
2. ディレクトリ作成: `bin/`, `ml/`, `tools/`, `repos/`, `venvs/`
3. **uv を `$EMBR_HOME/bin` にインストール**（下記 §5）
4. **`embr-pybox-handlers` を配置**
   - 推奨: `git clone` → `$EMBR_HOME/repos/embr-pybox-handlers`
   - または社内 zip / 既存 path を指定
5. **bootstrap 実行**（Flame Python または system python3 で可）:

```bash
"$EMBR_HOME/bin/uv"  # 存在確認

python3 \
  "$EMBR_HOME/repos/embr-pybox-handlers/worker/embr_ml/bootstrap.py" \
  --repo-root "$EMBR_HOME/repos/embr-pybox-handlers" \
  --ml-root "$EMBR_HOME/ml"
```

※ bootstrap 改修後は、内部でも `$EMBR_HOME/bin/uv` を使うこと（§6）。

6. **MatAnyone2 推論依存**（現状の既知ギャップ）
   - Mac: 公式 `pip install git+…` が hatch で失敗することがある  
   - いまの検証機では `~/Embr/ml/src/MatAnyone2` を clone → patch →  
     `worker/.venv` に `uv pip install -e`  
   - Install スクリプトに「matte extra / local editable」ステップを明示的に入れること  
   - 詳細: `embr-pybox-handlers/docs/dev-phase3.md`

7. **スモーク**
   - `$EMBR_HOME/repos/.../worker/.venv/bin/python -m embr_ml.cli status`
   - `matanyone2.pth` の存在
8. **ユーザー向けメモ**
   - Flame Pybox: Handler = `…/handlers/embr_matte.py`  
   - Repo Root = handlers の clone 絶対パス  
   - Device: Mac `mps` / Linux `cuda:0`

### 4.3 Repair

- uv 欠落 → 再 install（§5）
- venv 壊れ → `worker/.venv` 削除後 bootstrap
- ウェイト欠落 → `python -m embr_ml.cli ensure-models`

### 4.4 Uninstall（ランタイム）

```bash
rm -rf "$EMBR_HOME"          # 既定 ~/Embr
rm -f "$HOME/embr-ml"        # 互換 symlink
```

**消さないもの（明示）:**

- Flame / `…/python/Embr/` hooks（Script Manager の Uninstall に任せる）
- ユーザーが `Projects/` に残した開発 clone（Install が `repos/` に置いたものだけ消す、と文書化）

**任意クリーン（旧汚染）:**

```bash
# Embr Setup で入れた可能性が高い場合のみ案内。他用途の uv かも確認。
rm -f ~/.local/bin/uv
# uv のキャッシュ（70MB 級）。Embr 専用運用なら削除可。
rm -rf ~/.local/share/uv
```

Install 時に「以前の `~/.local/bin/uv` を検出したら移行／削除を提案」すると親切。

---

## 5. uv を `~/Embr/bin` に入れる方法

Astral 公式インストーラは **`UV_INSTALL_DIR`** で配置先を変えられる（現行 bootstrap もこの変数を使っているが、値が `~/.local/bin`）。

```bash
export EMBR_HOME="${EMBR_HOME:-$HOME/Embr}"
mkdir -p "$EMBR_HOME/bin"

# 公式 install.sh を Embr 配下へ
curl -LsSf https://astral.sh/uv/install.sh | \
  UV_INSTALL_DIR="$EMBR_HOME/bin" sh

test -x "$EMBR_HOME/bin/uv"
"$EMBR_HOME/bin/uv" --version
```

注意:

- **`PATH` に `$EMBR_HOME/bin` を永続追加しない**（`.zshrc` を触らない）
- 子プロセスだけ `PATH="$EMBR_HOME/bin:$PATH"` または `"$EMBR_HOME/bin/uv"` 直呼び
- オフライン現場: 事前に uv バイナリを `bin/uv` に配布し、curl をスキップするモードを用意

既存 `~/.local/bin/uv` がある場合の推奨ロジック:

1. `$EMBR_HOME/bin/uv` が無ければ install（または `cp` / 再 download）
2. Embr のツールは **常に `$EMBR_HOME/bin/uv` を優先**
3. UI で「~/.local の uv を削除しますか？」は任意（既定 No）

---

## 6. `embr-pybox-handlers` 側の追従（必須フォロー）

`worker/embr_ml/bootstrap.py` の現状:

- `find_uv()` が `PATH` → `~/.local/bin/uv` → cargo / brew
- `install_uv()` の `UV_INSTALL_DIR` が `~/.local/bin`

**変更すべき契約:**

1. `find_uv()` の最優先: `$EMBR_UV` → `$EMBR_HOME/bin/uv` →（互換）その他  
2. `install_uv()` の配置先: **`$EMBR_HOME/bin` のみ**（`~/.local` に新規 install しない）  
3. `_uv_env()["PATH"]` の先頭に `$EMBR_HOME/bin`  
4. `paths.ensure_layout()` で `bin/` も作成（済みの `tools/repos/venvs` に加え）

Pybox:

- `embr_matte` の Repo Root 既定を  
  `$EMBR_HOME/repos/embr-pybox-handlers` に寄せると Install 後の導線が短い  
- `EMBR_ML_ROOT` 既定は既に `~/Embr/ml`

---

## 7. MatAnyone / embr_matte 動作に必要な成果物チェックリスト

Install 完了の定義:

- [ ] `$EMBR_HOME/bin/uv` が実行可能
- [ ] `$EMBR_HOME/repos/embr-pybox-handlers`（または指定 Repo Root）が存在
- [ ] `…/worker/.venv/bin/python` が存在
- [ ] venv 内で `import matanyone2` 相当が使える（editable 含む）
- [ ] `$EMBR_ML_ROOT/models/matanyone2/matanyone2.pth` が存在
- [ ] `python -m embr_ml.cli status` が OK
- [ ]（任意）短い `process-job` または既存 smoke job

アーティストが触る Handler:

| Handler | 用途 |
|---------|------|
| `handlers/embr_matte.py` | 本番作業（Init / Record / Run / HUD） |

Setup UI は **embr-python-scripts** の Install（本リポの Setup handler は廃止）。

作業ドキュメント: `embr-pybox-handlers/docs/dev-matte-run.md`  
ホームレイアウト: `embr-pybox-handlers/docs/embr-home.md`

---

## 8. Flame / Script Manager との関係（設計メモ）

- Script Manager は **hooks を `python/Embr/` に入れる**既存フローを維持
- AI Runtime Install は **別アクション**が安全（巨大 download・venv・ライセンス）
- 将来カタログに載せるなら:
  - パッケージは「ランチャ／設定のみ hooks 側」
  - 実体 download は常に `$EMBR_HOME`
- MatAnyone2 は **S-Lab non-commercial** 系ライセンス → Install UI に同意／社内ポリシー注記を入れること

---

## 9. この検証マシンの現状スナップショット（2026-08-13）

| 項目 | 場所 |
|------|------|
| データ | `~/Embr/ml`（`~/embr-ml` は symlink） |
| 開発 clone | `/Users/oue.isamu/Projects/embr-pybox-handlers` |
| worker venv | 上記 `worker/.venv`（約 2.3GB） |
| **いまの uv** | **`~/.local/bin/uv`** ← 移行対象 |
| MatAnyone2 src | `~/Embr/ml/src/MatAnyone2` |
| ウェイト | `~/Embr/ml/models/matanyone2/matanyone2.pth` |

Install スクリプト実装後の手動移行例:

```bash
mkdir -p ~/Embr/bin
curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$HOME/Embr/bin" sh
# 動作確認後、Embr 以外で uv を使っていなければ:
# rm -f ~/.local/bin/uv
```

---

## 10. 実装タスク分割（提案）

### A. `embr-python-scripts`（本引き継ぎの主作業）

1. `EMBR_HOME` / path ヘルパ（hooks の `embr_paths` と混同しない名前に）
2. `install_embr_runtime.py`（CLI）: §4.2
3. Flame メニュー or Script Manager 導線 + 進捗／ログ表示
4. Uninstall / Repair
5. 旧 `~/.local/bin/uv` 検出と案内
6. ドキュメント（scripts 側 README or `docs/ai-runtime.md`）

### B. `embr-pybox-handlers`（短い追従 PR）

1. `bootstrap.find_uv` / `install_uv` を Embr-bin 優先に変更
2. `paths.ensure_layout` で `bin/` 作成
3. `docs/embr-home.md` を本資料と整合（uv は Embr 下）
4. Repo Root 既定パスの更新（任意）

### C. 後回しでよい

- venv を `~/Embr/venvs/` へ完全移設
- SAM2
- 任意フレームガイド

---

## 11. 受け入れ条件（Done）

1. クリーンなユーザーで Install 一発（またはメニュー）後、**新規に `~/.local/bin/uv` が増えない**
2. `$EMBR_HOME/bin/uv` だけで `worker/.venv` が作れる
3. `rm -rf ~/Embr && rm -f ~/embr-ml` でランタイムが消える（hooks は別）
4. `embr_matte` が Repo Root = `~/Embr/repos/embr-pybox-handlers` で Run できる（既存検証機では clone 移設後）

---

## 12. 参照ファイル（handlers リポ）

| パス | 内容 |
|------|------|
| `docs/embr-home.md` | `~/Embr` レイアウト |
| `docs/dev-phase3.md` | Setup / uv / weights |
| `docs/dev-phase3-env.md` | 環境方針 |
| `docs/dev-matte-run.md` | embr_matte 操作 |
| `worker/embr_ml/bootstrap.py` | **要改修**（uv 配置） |
| `worker/embr_ml/paths.py` | `EMBR_HOME` / `EMBR_ML_ROOT` |
| `handlers/embr_matte.py` | 作業用 Pybox |

質問・齟齬があれば `embr-pybox-handlers` 側の上記ドキュメントを正とし、本資料を更新すること。
