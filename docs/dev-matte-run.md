# Embr Matte（Pybox 非同期 Run）

Front + ガイド Matte → 裏で `process-job` → Result=`fgr` / OutMatte=`pha(alpha)`。  
進捗は `job/status.json` → Pybox notice。

## Handler

`handlers/embr_matte.py`

前提: embr-python-scripts の **Install** 済み（`~/Embr` + `worker/.venv` + **numpy/Pillow/OpenEXR**）。

`run.log` に `No module named 'numpy'` が出る場合は venv が空です:

```bash
cd ~/Embr/repos/embr-pybox-handlers/worker
~/Embr/bin/uv pip install -e .
```

## Batch 手順

1. Handler に `…/handlers/embr_matte.py`  
2. **Repo Root** = このリポ（初回のみ）  
3. Front / Matte を接続  
4. （任意）**Job Name** を入れて **Init Job**  
   - 空なら `job_YYYYMMDD_HHMMSS`（ショット名があれば接頭）  
   - ジョブは `~/Embr/ml/jobs/<name>`（旧 `~/embr-ml` は互換リンク）  
   - **Job Path はこのノードの UI に保持**（グローバル固定ファイルは使わない）  
5. notice の **next:** に従う  
   - `Record Front ON → Play/scrub`  
   - `Capture Guide Matte`（先頭 Record フレーム）  
   - `Run Matte`  
6. 実行中はスクラブ / **Refresh Status** で進捗  
7. `done` 後、Result=fgr / OutMatte=alpha  

## 論理ゲート（見た目は押せても無効）

| 状態 | 有効な操作 |
|------|------------|
| ジョブなし | Init のみ |
| input なし | Record（+ Init） |
| mask なし | Record / Capture Guide |
| 準備完了 | Record / Guide / **Run** |
| running | Status のみ（Run/Guide/Record 拒否） |

押してもダメなときは warning で理由を出します（Pybox に disable API が無いため）。

## ジョブ（クリップごと）

- **Job Path はこの Pybox ノード専用**（Flame がノード設定として保持）
- データ根は **`~/Embr/ml`**（`$EMBR_ML_ROOT`）。全体は [embr-home.md](./embr-home.md)
- クリップを変えたらそのノードで **Init Job**（空 Name → `ショット_日時` で新規）
- 既存ジョブを付けるときだけ Job Name を明示
- Change Handler 直後は `(press Init Job)` になり得る

## ジョブレイアウト

```text
job/
  input/0001.exr …     # Record Front
  mask.exr             # Capture Guide
  status.json
  run.pid / run.log
  alpha/  fgr/
```

## Result HUD

**Show HUD**（Actions 列）を ON にすると、Result ビュー左上にステータスパネルを焼き込みます（初期は OFF。ON 時は worker の PIL で合成）。

表示例:
- Job 名 / 現在 Batch フレーム
- Record Front: `N` または `N/Expected`（Frames 列の **Expected Frames**）
- Record 範囲 / このフレーム取得済みか
- Guide matte のフレーム番号
- Prep READY かどうか
- Run 進捗（status.json）

OFF にするとクリーンな fgr / Front のみ。  
ビューは **Result** を見てください（HUD は Result のみ）。

## トラブルシュート

| 症状 | 確認 |
|------|------|
| Run が無反応 | Message Console / `job/handler_actions.log` / `job/run.log` |
| HUD が出ない | Show HUD ON・Result 表示・`worker/.venv` の有無・warning |
| worker python missing | Repo Root = clone ルート（`…/embr-pybox-handlers`） |

