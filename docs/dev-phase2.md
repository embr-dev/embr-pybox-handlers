# Phase 2 — Cache Playback（動作確認手順）

前提: フェーズ 1（`embr_hello`）成功。

## 既知の落とし穴（修正済み）

| 症状 | 原因 | 対処 |
|------|------|------|
| Matte プレビューが回り続ける | OutMatte ファイル未出力で Flame がリトライ | 欠落時は Matte/Front にフォールバックして必ず書く |
| `missing /var/examples/...` | Flame は handler を `/var/tmp` で実行。`__file__` 相対が壊れる | Job 既定を `/tmp/embr_cache_job`（絶対パス）に固定 |
| Matte を外すとエラー | Pybox が Matte 入力を要求することがある | **外さない**。Capture も再生確認も Matte 接続のままでよい |

## 何を検証するか

| 項目 | 期待 |
|------|------|
| Handler ロード | `embr_cache_playback.py` が載る |
| Front | Result = 入力プレート |
| Capture | `/tmp/embr_cache_job/alpha/{frame}.exr` が作られる |
| 再生 | 同フレームの OutMatte が Capture 内容 |
| 欠落フレーム | warning + Matte/Front フォールバック（スピンしない） |

## ジョブ規約

```text
/tmp/embr_cache_job/alpha/0013.exr
```

- 既定 Job Folder: `/tmp/embr_cache_job`（UI で変更可。**絶対パス**にすること）
- ファイル名 = `get_frame()` + Frame Offset、桁 = Frame Padding（既定 4）

## 手順

1. Handler に  
   `/Users/oue.isamu/Projects/embr-pybox-handlers/handlers/embr_cache_playback.py`  
   → **Change Handler** で再読込  
2. Front + Matte を接続したまま（外さない）。  
3. Job Folder が `/tmp/embr_cache_job` であること（`/var/examples/...` なら直し、Change Handler）。  
4. Result を表示し、フレームを決める。  
5. **Log Status** → notice の `path=` が `/tmp/embr_cache_job/alpha/....exr` であること。  
6. **Capture Matte to Cache** → notice で保存パス。Finder/ターミナルでファイル存在確認可。  
7. 別のマットに差し替えてもよい（外さず差し替え）。同フレームで OutMatte が **Capture 時の絵**のままならキャッシュ再生成功。  
8. 未 Capture フレームへ移動 → warning（フォールバック表示、カーソルが回り続けない）。

## つまずいたら

- まだ `/var/examples` と出る → Change Handler、または Job Folder を手で `/tmp/embr_cache_job` に指定  
- Capture 失敗 → Matte 接続＋Result 表示で1フレーム処理させてから再トグル  
- ログ確認: `/opt/Autodesk/log/flame2025_*_app.log` で `Embr Cache:`

成功したらフェーズ 2 完了 → 次はフェーズ 3（Flame 外 CLI）。
