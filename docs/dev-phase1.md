# Phase 1 — Embr Hello（動作確認手順）

前提: フェーズ 0 で公式 `no_op` が動いていること。

## 何を検証するか

| 項目 | 期待 |
|------|------|
| 自作 `.py` のロード | Pybox が落ちずに載る |
| パススルー | Front→Result、Matte→OutMatte |
| UI | 「Log Frame Info」トグルが表示される |
| メッセージ | トグル ON で Message Console に `Embr Hello: frame=…` |
| 再読込 | 保存 → Change Handler で反映 |

## 手順

1. Handler に `handlers/embr_hello.py` のパスを指定（[handlers/README.md](../handlers/README.md)）。  
2. Front / Matte を接続（Matte は無くてもロード確認は可）。  
3. Result ビューを開く（フレーム処理が走る条件になることがある）。  
4. **Log Frame Info** をオンにする。  
5. Message Console で `Embr Hello: frame=… size=…` を確認。  
6. ファイルを1行だけ変え（例: メッセージ先頭を `Embr Hello*`）、Change Handler → 再トグルで反映を確認。

## つまずいたら

- メッセージが出ない → Result を表示した状態でトグル、または1フレーム進める  
- import エラー → Flame 同梱環境以外で実行していないか（handler は Flame 経由のみ）  
- ソケットが空 → `no_op` と同じく Matte は index 2。接続し直す  

成功したらフェーズ 1 完了 → 次はフェーズ 2（キャッシュ再生）。
