# Pybox

公式 Help「Pybox」の整理。Batch / Timeline からサードパーティ処理をパイプラインに載せる仕組み。

| 項目 | 内容 |
|------|------|
| 一次情報 | `docs/API Documentation/Pybox/` |
| モジュール | `/opt/Autodesk/shared/presets/pybox/pybox_v1.py`（環境によりパス差あり） |
| サンプル | `/opt/Autodesk/presets/<version>/pybox/`（例: `2025/pybox/`） |
| 関連 | [recipes.md](./recipes.md) · [looping-by-node-type.md](./looping-by-node-type.md) |

---

## Embr Pybox Handlers 向け注意（2025）

- Help 本文は歴史的に **「handlers are written in Python 2.7」** と書いているが、Flame **2025 の実行環境は Python 3.11**。同梱サンプル（`no_op.py` 等）は `pybox_v1` を使う通常の 3 系構文。
- Pybox は **`import flame` の一般 API とは別系統**。通信は JSON payload 経由で、Flame が handler を「駆動」するのではなく、handler が `set_state_id` で状態を進める。
- 本リポジトリは **Pybox handlers** 専用。hooks / Script Manager は [embr-python-scripts](https://github.com/embr-dev/embr-python-scripts) 側。
- 出典コピー元: `embr-python-scripts/docs/api/pybox.md`（公式 Help HTML は `docs/reference/official-pybox-help/`）。

---

## 何か／何かではない

### 何か

- Matchbox（GLSL）に近い発想で、**Batch / Timeline のノードとして外部アプリを操作**できる。
- 画像を返す用途が典型だが、**画像以外の任意処理**も可能（ソケットなし handler も可）。

### 何かではない

| 制約 | 意味 |
|------|------|
| リアルタイム再生向けではない | 外部処理待ちが前提。パイプライン全体の RT 再生は保証されない |
| キャッシュ機構ではない | Batch 既存のキャッシュをノード単位で利用 |
| レンダパイプライン直アクセス API ではない | 情報をパイプラインへ **戻す** 仕組み。内部レンダラへの直接 API ではない |

---

## 開発要件

```python
import pybox_v1 as pybox
```

- Flame 起動時に `pybox_v1` がパスへ載る想定。追加の自作モジュールは **`pybox_v1.py` と同じディレクトリ**に置く（通常 `/opt/Autodesk/shared/presets/pybox`）。
- 標準ライブラリ（`os`, `sys`, `tempfile` 等）はそのまま import 可。
- 配布は基本 **`.py` ファイルを渡すだけ**。カスタムモジュールがある場合のみ上記共有ディレクトリ配置が必須。

### ロード／アンロード（アーティスト操作）

| タイミング | 挙動 |
|------------|------|
| Load / Change Handler | ディスクから **毎回再読込**（開発中の再起動不要） |
| ノード複製 | handler もロードされる |
| ノード削除 / 別 handler へ切替 | unload |

---

## Handler の骨格

最低限: `main` で `BaseClass` を作り `dispatch()` → `write_to_disk()`。

```python
import sys
import pybox_v1 as pybox


class HelloWorld(pybox.BaseClass):
    def initialize(self):
        self.set_state_id("setup_ui")
        self.setup_ui()

    def setup_ui(self):
        self.set_state_id("execute")
        self.execute()

    def execute(self):
        self.set_state_id("teardown")
        self.teardown()

    def teardown(self):
        pass


def _main(argv):
    p = HelloWorld(argv[0])
    p.dispatch()
    p.write_to_disk(argv[0])


if __name__ == "__main__":
    _main(sys.argv[1:])
```

- `dispatch()` — 現在の `state_id` に応じて `initialize` / `setup_ui` / `execute` / `teardown` を実行
- `write_to_disk()` — Flame が読む JSON payload を書き出す
- 出力ソケット未定義だとログにエラーが出るが、ロード自体はできる（Help 記載）

### `initialize` — 入出力ソケット

```python
def initialize(self):
    self.set_img_format("exr")
    self.set_in_socket(0, "Front", "/tmp/in_front.exr")
    self.set_in_socket(1, "Matte", "/tmp/in_matte.exr")
    self.set_out_socket(0, "Result", "/tmp/in_front.exr")
    self.set_out_socket(1, "OutMatte", "/tmp/in_matte.exr")
    self.set_state_id("setup_ui")
    self.setup_ui()
```

| メソッド | 役割 |
|----------|------|
| `set_img_format` | Flame が書き出す画像形式（必須） |
| `set_in_socket(index, name, path)` | 入力。Flame が **書き込み可能な** パスへ upstream 画像を出す |
| `set_out_socket(index, name, path)` | 出力。Flame が **読み取り可能な** パスから結果を取る |
| `set_state_id` | 次状態を JSON 経由で Flame に伝える |

Flame はスクリプトを直接「次へ」進めない。**handler が次のメソッドを呼ぶ／state をセットする**。

### `setup_ui` — ノード UI

```python
def setup_ui(self):
    blur_amount = pybox.create_float_numeric(
        "Blur Amount", value=0.0, min=0.0, max=100.0
    )
    self.add_render_elements(blur_amount)

    page = pybox.create_page("Main Page", "Blur Settings")
    self.set_ui_pages(page)

    self.set_state_id("execute")
    self.execute()
```

| プール | 意味 |
|--------|------|
| render elements（`add_render_elements`） | Result 表示や下流がフレーム要求したときだけ問い合わせ。見た目／レンダ結果に効く値向け |
| global elements | 常に Python 呼び出しを起こしうる。セットアップ選択などノード自体の操作向け |

#### 対応 UI 要素

| UI | `pybox_v1` |
|----|------------|
| float 1 欄 | `create_float_numeric()` |
| float 2 / 3 欄 | `create_vector_numeric(size=2\|3)` |
| ドロップダウン | `create_popup()` |
| カラー | `create_color()` |
| トグル | `create_toggle_button()` |
| ファイルブラウザ | `create_file_browser()` |

---

## 処理モデル

- **ステートレスかつ同期**。状態は自分で `set_state_id` 管理。
- Flame ↔ handler の接点は次の 3 つだけ:
  1. Flame が書いた入力画像ファイル
  2. 外部処理が書いた出力画像ファイル
  3. JSON payload
- ボトルネックは多くの場合 **ディスク I/O**。高速ストレージや RAM ディスクを推奨（Help）。

---

## フレーム／プロジェクト metadata

`pybox_v1.BaseClass` から取得できる主なもの:

| 内容 | メソッド |
|------|----------|
| bit depth | `get_bit_depth()` |
| colour space | `get_colour_space()` |
| date / day / month / year | `get_date()` 他 |
| 現在 Batch フレーム | `get_frame()` |
| frame ratio / rate | `get_frame_ratio()` / `get_framerate()` |
| width / height / resolution | `get_width()` / `get_height()` / `get_resolution()` |
| img format | `get_img_format()` |
| user / nickname | `get_user()` / `get_nickname()` |
| node / project 名 | `get_node_name()` / `get_project()` / `get_project_nickname()` |
| source / record TC | `get_source_time_code()` / `get_record_time_code()` |
| workstation | `get_workstation()` |

---

## エラーとデバッグ

- Flame 側で **Esc** により中断可。
- Result 以外のビューを開いているとフレーム処理が走らないことがある（トラブルシュート時に有用）。
- `Change Handler` でキャッシュなし再読込。

| 重要度高 → 低 | get | set |
|----------------|-----|-----|
| error | `get_error_msg()` | `set_error_msg()` |
| warning | `get_warning_msg()` | `set_warning_msg()` |
| notice | `get_notice_msg()` | `set_notice_msg()` |
| debug | `get_debug_msg()` | `set_debug_msg()` |

メッセージは Flame の message console / shell / log に出る。handler 内は `try`/`except` 推奨。

---

## 同梱サンプル（`<version>/pybox/`）

| ファイル | 内容 |
|----------|------|
| `no_op.py` | Front/Matte パススルー（最小に近い） |
| `event_handling.py` | UI 変更イベントと動的ページ |
| `random_ui.py` | UI をランダム生成（クラス外関数利用例） |
| `image_magick*.py` | ImageMagick blur / polaroid（macOS は別途インストール） |
| `print_process_infos.py` | 処理情報を shell へ |
| `sendmail.py` | 入出力ソケットなしの任意処理例 |
| `nuke_px.py` 他 | Nuke 連携（要パス編集・カスタマイズ前提） |
| `opencv_*.py` / `maya_render.py` 等 | 2025 プリセットに存在する追加例 |

### Nuke 連携の要点（Help 要約）

- handler: `nuke_px.py`、共有側に `nuke_parse_io.py` / `nuke_parse_ui.py` / `nuke_parse_exec.py`
- `NUKE_PATH`（と macOS では `PAYLOAD_PATH`）を環境に合わせて編集
- 遅い場合は tempfile ではなく高速ディスクへ `filename` を変更
- Nuke 側: 公開したい knob は `adsk_` 接頭。Write は `adsk_1_result` / `adsk_2_matte`、Shuffle 経由の **8/16-bit RGB**（RGBA 非対応）

---

## 用語

| 語 | 意味 |
|----|------|
| Pybox（機能） | 外部アプリを Batch/Timeline パイプラインに載せる仕組み |
| Pybox（ノード） | アーティストが載せる Batch ノード / Timeline FX |
| Handler | 開発者が書く `.py`。UI・JSON・外部プロセスを担当 |
| JSON payload | Flame ↔ handler の一時通信ファイル |

---

## 一次情報

- Help HTML: [`../API Documentation/Pybox/`](../API%20Documentation/Pybox/)
- API 詳細は同梱 `pybox_v1.py` の docstring / 配布ドキュメントを優先
