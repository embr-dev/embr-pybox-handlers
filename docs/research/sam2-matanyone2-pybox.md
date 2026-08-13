# SAM2 + MatAnyone 2 × Flame Pybox — 調査メモ

調査日: 2026-08-12  
目的: Flame 内映像からオブジェクトマスク（マット）を作るパイプラインを、Pybox にどう載せるか検討する。

---

## 1. 収集した一次情報

| 種別 | 場所 |
|------|------|
| Embr 整理 API | [docs/api/pybox.md](../api/pybox.md)（`embr-python-scripts` から移植） |
| 公式 Help HTML | [docs/reference/official-pybox-help/](../reference/official-pybox-help/) |
| 同梱サンプル | `/opt/Autodesk/presets/2025/pybox/`（`no_op`, `nuke_px`, `opencv_*` 等） |
| SAM 2 | https://github.com/facebookresearch/sam2 （Apache-2.0） |
| MatAnyone 2 | https://github.com/pq-yang/MatAnyone2 （NTU S-Lab License 1.0） |
| LOGIK 議論 | [Custom Nodes / Pybox 制約](https://forum.logik.tv/t/question-for-the-braintrust-custom-nodes/11587), [Pybox Nuke](https://forum.logik.tv/t/pybox-nuke/4091) |
| 現代 ML×Pybox 先例 | [corridorkey-flame](https://github.com/cnoellert/corridorkey-flame)（daemon + 別 conda） |
| 時間軸 AI×Flame 先例 | Comfy-Flame / BCE 等は **hooks + export/import** 寄りが多い |

---

## 2. Pybox の本質（この用途に効く制約）

### できること

- Batch / Timeline FX の **ノード**として外部 Python を呼ぶ
- Front / Matte 等のソケットで **1 フレーム分**の画像ファイルをやり取り
- 限定 UI（float / vector / popup / color / toggle / file browser）
- `get_frame()` 等のメタデータ取得
- 外部プロセス起動（Nuke サンプルは **フレームごとに** `nuke -ix -F <frame>`）

### できない／弱いところ（公式 + LOGIK + サンプルから）

| 制約 | 影響 |
|------|------|
| **フレーム単位・同期・ステートレス**（JSON payload 経由） | 動画メモリモデルを「そのまま」ノード内に置けない |
| I/O はディスク上の画像パス | ボトルネックは I/O。高速ディスク推奨 |
| UI に画像上クリックがない | SAM2 の点プロンプト UI を Flame 内に作れない |
| 入出力は同系フォーマット前提（コミュニティ報告: 解像度変更・時間軸処理が苦手） | アップスケールや「シーケンス全体を一度に」は設計で迂回が必要 |
| Flame 同梱 Python に torch / CUDA を載せない想定 | **別 conda / daemon** が事実上必須（CorridorKey と同型） |
| 古い・fussy（LOGIK 2024） | 本番は「薄い handler + 外の推論サービス」が現実解 |

Nuke Pybox の教訓: 毎フレーム CLI レンダは **かなり遅い**。ライブノードではなく pre-render 前提が推奨されている。

---

## 3. SAM 2 仕様（マスクガイド生成）

### 役割

プロンプト付きセグメンテーション。**画像**と**動画**の両方。動画は memory 付きストリーミングで masklet を伝播。

### 入力 / 出力

| モード | 入力 | 出力 |
|--------|------|------|
| Image (`SAM2ImagePredictor`) | 1 枚 + points / box / mask | バイナリマスク（複数候補可） |
| Video (`SAM2VideoPredictor`) | 動画（フレーム列）+ 任意フレームへのプロンプト | 各フレームの object mask |

典型 API:

```text
init_state(video)
add_new_points_or_box(state, prompts)  → 同フレームの mask
propagate_in_video(state)              → 全フレーム masklet
```

### 実行要件

- Python ≥ 3.10、`torch ≥ 2.5.1`、CUDA 推奨
- チェックポイント: SAM 2.1 hiera tiny〜large（large は ~224M params）
- ライセンス: **Apache-2.0**（商用利用しやすい）

### MatAnyone 2 との公式な接続

MatAnyone 2 README は、最初のフレームの **セグメンテーションマスク**を SAM2 デモ等で用意することを明示している。  
つまり製品パイプラインとしては:

1. **SAM2** … 対象指定（クリック / box）→ 第 1 フレーム（または全フレーム）ガイドマスク  
2. **MatAnyone 2** … 動画 + 第 1 フレームマスク → **alpha マット動画**（髪・境界の細かいマット）

SAM2 の出力は「セグメンテーション境界」、MatAnyone 2 はそれを **マット品質**に持ち上げる役割。

---

## 4. MatAnyone 2 仕様（ビデオマット）

### 役割

人間向けを主眼とした **video matting**。セグメンテーションっぽい硬い境界を避け、実世界条件での堅牢性を強調（CVPR 2026 Highlight）。

### 必須入力

毎ラン:

- **動画**（フレームフォルダ または `.mp4` / `.mov` / `.avi`）
- **第 1 フレームのセグメンテーションマスク**（PNG 等）

出力:

- foreground 動画
- **alpha** 動画  
- `--save-image` でフレーム連番可  
- `--max-size` で短辺リサイズ上限

### Python API 例

```python
from matanyone2 import MatAnyone2, InferenceCore
model = MatAnyone2.from_pretrained("PeiqingYang/MatAnyone2")
processor = InferenceCore(model, device="cuda:0")
processor.process_video(
    input_path="clip.mp4",
    mask_path="frame0_mask.png",
    output_path="results",
)
```

### 実行要件

- 公式: conda `python=3.10`、または `uv`
- GPU（CUDA）前提のデモ／HF Space
- モデル ~35M params（HF 表記）— 相対的に軽めだが **シーケンス一括推論**
- ライセンス: **NTU S-Lab License 1.0**（MatAnyone 1 と同系。条文上 **non-commercial** のみ許可。商用は権利者へ連絡必須）  
  → Embr での商用・再配布前に **許諾またはウェイト非同梱＋利用者自己取得** を決めること

### 対象ドメイン注意

論文・README は **human video matting** が中心。「任意オブジェクト」は SAM2 ガイド次第で試みられるが、髪以外の複雑形状・非人体は品質保証外。

---

## 5. ギャップ分析（やりたいこと vs Pybox）

| 工程 | 必要なもの | Pybox 単体 |
|------|------------|------------|
| 対象指定（クリック） | 画像上インタラクション | **不可**（UI 要素に無い） |
| 第 1 フレームマスク | SAM2 image / 既存 Matte | Matte ソケット or 外部 UI なら可 |
| 時間一貫マット | 動画全体を一度に処理 | **毎フレーム execute とは不整合** |
| Batch 内ライブ調整 | 速いフィードバック | Nuke 先例どおり **非現実的**（遅い） |
| 結果を OutMatte に戻す | 同解像度アルファ | キャッシュ済みなら可 |

**結論の核:**  
「SAM2+MatAnyone2 を、毎フレームライブな Pybox ノードとして動かす」のは **現実的ではない**。  
可能なのは **ジョブ型（シーケンス単位）** を薄い Pybox / hooks からキックし、結果をキャッシュして読む構成。

---

## 6. 実装オプション（現実性付き）

### A. 推奨: ジョブ型ワーカー + 薄い Pybox（CorridorKey 型）

```text
Flame Batch
  └─ Pybox (UI: job path / mode / max-size / Run)
        │  Front/Matte を staging に蓄積 or 既エクスポートパス参照
        ▼
  別 conda の daemon / CLI
        │  1) (optional) SAM2: frame0 + prompts → mask
        │  2) MatAnyone2: video + mask → alpha sequence
        ▼
  キャッシュ (frame.####.exr)
        ▲
  Pybox execute(): get_frame() に対応するキャッシュを OutMatte にコピー
```

| 項目 | 評価 |
|------|------|
| 現実性 | **高**（先例あり） |
| 品質 | モデル本来の時間一貫性を維持 |
| UX | 「Render / Cache」ボタン後に再生。ライブではない |
| 難所 | シーケンス蓄積、スクラブ時の未キャッシュ、VRAM（Flame と共有） |

ガイド指定の現実解:

- **Matte 入力に粗いマスク／キー**を渡す（Flame 内で描く）  
- または **file browser で frame0 マスク PNG**  
- クリック UI は **別 Gradio**（MatAnyone2 公式デモと同型）を起動するだけ

### B. hooks 主導（Comfy-Flame / Media Panel 型）

Media Panel → 書き出し → SAM2+MatAnyone2 → 結果を再 import。  
Pybox は使わないか、結果確認用のパススルーのみ。

| 項目 | 評価 |
|------|------|
| 現実性 | **高** |
| Batch 内コンポ感 | 弱い |
| Embr 分担 | 本体は `embr-python-scripts`、推論は本リポの CLI |

### C. 毎フレーム素朴推論（非推奨）

各 `execute()` で MatAnyone を「そのフレームだけ」走らせる、または SAM2 image のみ。

| 項目 | 評価 |
|------|------|
| 現実性 | 動く可能性はあるが **品質・速度とも失格寄り** |
| 理由 | 時間メモリを捨てる／毎フレームモデルロードは論外 |

### D. 純ライブ「クリックで SAM2」Pybox

| 項目 | 評価 |
|------|------|
| 現実性 | **低〜不可** |
| 理由 | Pybox UI にビューアクリックが無い。別ウィンドウ Gradio 必須 |

---

## 7. Embr としての推奨アーキテクチャ

1. **本リポ (`embr-pybox-handlers`)**  
   - `handlers/` … Flame が読む薄い Pybox  
   - `worker/` … conda 環境用 CLI（`sam2_guide`, `matanyone2_matte`）  
   - `docs/` … 本メモ・配置手順  

2. **フェーズ分け**  
   - P0: CLI のみで動画フォルダ → alpha（Flame 外検証）  
   - P1: Pybox「キャッシュ再生」+ Matte ソケットを第 1 フレームガイドに  
   - P2: Gradio / 外部で SAM2 クリック → マスク自動投入  
   - P3（任意）: hooks からワンクリックジョブ（scripts リポ連携）  

3. **ライセンス**  
   - SAM2: Apache-2.0 → Embr 配布しやすい  
   - MatAnyone2: S-Lab → **商用・再配布ポリシーを先に確定**（ウェイト同梱可否）

4. **ハードウェア**  
   - Linux: 別 GPU マシン or Flame と時間帯分離（CorridorKey も VRAM 警告）  
   - macOS: MatAnyone2 公式は CUDA 寄り。Apple は非公式／別移植（MatAnyone2Kit）検討 — **当面 Linux CUDA を主戦場にするのが無難**

---

## 8. 現実的ではないこと（明示）

1. **Batch 上でリアルタイムに SAM2 クリック → 即座に全長マット**（UI・時間・VRAM すべて不一致）  
2. **Flame 同梱 Python に torch を入れて handler 内で直接推論**  
3. **Nuke Pybox のように毎フレームフル推論をライブ運用**（遅すぎて使えない）  
4. **解像度変更付きアップスケールマットを Pybox ソケットだけで完結**（コミュニティ制約）  
5. **ライセンス確認なしの MatAnyone2 商用同梱**

---

## 9. 次の一手（合意が取れたら）

1. P0 CLI スケルトン（入力: フレーム列 + mask.png → alpha 列）  
2. 最小 Pybox: `no_op` 派生で「キャッシュ済み alpha をフレーム番号で返す」  
3. ライセンス条文の確定と README への利用条件記載  
