# Embr home layout（`~/Embr`）

アンインストールしやすいよう、AI / Pybox ランタイムは **`~/Embr`** に集約する。

```text
~/Embr/                 # $EMBR_HOME
  README.md
  bin/
    uv                  # Embr 専用（~/.local に入れない）
  ml/                   # $EMBR_ML_ROOT（jobs / models / src）
  tools/                # 今後の AI ツール用データ
  repos/                # 推奨: embr-pybox-handlers clone
  venvs/                # 任意: 共有 venv

~/embr-ml → ~/Embr/ml   # 旧パス互換シンボリックリンク（移行後）
```

インストール実装の詳細・責務分担:  
**[handoff-embr-runtime-install.md](./handoff-embr-runtime-install.md)**（`embr-python-scripts` 向け引き継ぎ）

## 環境変数

| 変数 | 既定 |
|------|------|
| `EMBR_HOME` | `~/Embr` |
| `EMBR_ML_ROOT` | `$EMBR_HOME/ml` |
| `EMBR_UV` | `$EMBR_HOME/bin/uv` |

`~/Embr/bin` は **シェルの PATH に常駐させない**。絶対パスまたは一時 PATH で呼ぶ。

## アンインストール

```bash
rm -rf ~/Embr
rm -f ~/embr-ml
# 旧汚染の掃除（Embr 以外で uv 未使用なら）:
# rm -f ~/.local/bin/uv
# rm -rf ~/.local/share/uv
```

残るもの:

- Autodesk Flame 本体
- Script Manager が入れた `…/python/Embr/` hooks（別 Uninstall）
- `Projects/` など Embr 外に置いた開発 clone（`repos/` に移せば `~/Embr` 削除で消える）

## 移行（データ）

```bash
mkdir -p ~/Embr
mv ~/embr-ml ~/Embr/ml
ln -s ~/Embr/ml ~/embr-ml
```

## 移行（uv → Embr 配下）※ scripts 側 Install 実装後

```bash
mkdir -p ~/Embr/bin
curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="$HOME/Embr/bin" sh
```
