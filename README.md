*This project has been created as part of the 42 curriculum by naarai, ksadayas.*

# A-Maze-ing — This is the way

カスタム迷路ジェネレーターです。設定ファイルを読み込み、（必要に応じて完全迷路を）生成し、壁情報を 16 進数で表したファイルへ書き出します。ターミナルでの ASCII 表示機能と、生成結果が各条件を満たすか検査する専用バリデーターも備えています。

---

## 概要

- 設定ファイル（`KEY=VALUE` 形式）を読み込み、迷路を生成します。
- 迷路の中央には、完全に閉じた複数のセルで描かれた **「42」** が現れます。
- `PERFECT=True` の場合、入口と出口の間には経路がちょうど 1 つだけ存在します（全域木）。
- `PERFECT=False` の場合は、四隅と中央を通路として開き、独立ループを 2 本以上持つプレイアブルな盤面（仕様 IV.4, v2.2）に変換します。
- 生成後に、各条件（連結性、壁の整合性、外周、3×3 の開放領域がないこと、最短経路など）を自動検証します。
- 出力ファイルは課題仕様の 16 進形式で、同梱バリデーターで検査できます。

---

## ファイル構成（提出コードとテスト）

**提出・採点対象（リポジトリ直下）:**

迷路パイプラインは役割ごとの小さなパッケージに分割されており、各モジュールは単独でインポートできます。**入力検証**（迷路を組む前に設定ファイルの入力を検査＝`validation/`）と、**構造検証**（組み上がった迷路の構造を検査＝`verification/`）は別プロセスである点に注意してください。

| パス | 役割 |
|------|------|
| `a_maze_ing.py` | メインプログラム（エントリーポイント） |
| `core/maze.py` | コア機能（壁の表現、開閉、BFS 距離、最短経路） |
| `core/metrics.py` | ループ数・行き止まり数の計数（`braiding/` と `verification/` が共有） |
| `core/errors.py` | 例外クラスの階層 |
| `validation/config.py` / `validation/options.py` | 必須キーの検証／任意キーの処理 |
| `generation/initializer.py` | 初期マップの生成と「42」記号の配置 |
| `generation/backtracker.py` | 再帰的バックトラッカー本体 |
| `generation/generator.py` | 生成アルゴリズムの選択用レジストリ |
| `braiding/braiding.py` | 不完全迷路（プレイアブル盤面）への変換（`PERFECT=False`） |
| `verification/verifier.py` | 生成後の条件検証（ライブラリ `validate()`） |
| `verification/cli.py` | 出力ファイル検証の単体 CLI |
| `output/writer.py` | 出力ファイルへの書き込み（16 進形式） |
| `output/ascii_display.py` / `output/display.py` | ASCII 描画と表示モード用レジストリ |
| `mazegen.py` | 再利用可能な単一ファイルモジュール |
| `mazegen-1.0.0-*.whl` / `.tar.gz` | ビルド済みパッケージ |
| `config.txt` / `Makefile` / `pyproject.toml` / `setup.cfg` / `README.md` | 設定、ビルド、ドキュメント |

**テスト用（提出・採点対象外。仕様 III.3）:**

- `tests/` 配下の `test_*.py`：動作確認用です。`make test` で実行します。

> テストは `tests/` に分離しているため、提出コード（リポジトリ直下の `*.py` とパッケージ）と明確に区別されています。テストはプロジェクトの動作確認だけを目的としています。

---

## 使い方（インストール／実行）

### 依存関係

実行に外部ライブラリは不要です（標準ライブラリのみ使用）。開発時には `flake8`、`mypy`、`pytest` を使用します。

### セットアップと実行

```bash
# 開発ツールのインストール
make install

# デフォルトの config.txt を使って迷路を生成・表示
make run

# 別の設定ファイルを指定
make run CONFIG=my_config.txt

# デバッグ実行（pdb）
make debug

# テスト
make test

# 静的検査（flake8 + mypy）
make lint
```

直接実行する場合:

```bash
python3 a_maze_ing.py config.txt
```

> 注記：`make install` は `./.venv` に隔離した仮想環境を構築し（`uv` を優先し、無ければ標準ライブラリの `venv` にフォールバック）、`run`／`debug`／`test`／`lint` はその環境を自動で使用します。Python のバージョンは `PY_VERSION`（既定 `3.12`）で指定できますが、あくまで優先指定であり、無い環境では利用可能な `python3` にフォールバックします。

> 注記：`setup.cfg` では `flake8` の `max-line-length = 100` を設定しています。これは、docstring と型ヒントの可読性を保つために、標準の 79 文字を意図的に緩和したものです。`make lint` は課題指定のフラグで `flake8 .` と `mypy .` を実行します。

### 出力ファイルの検証

```bash
python3 -m verification.cli maze.txt
```

---

## 設定ファイルの構造と形式

1 行につき 1 つの `KEY=VALUE` を記述します。`#` で始まる行と空行は無視されます。

### 必須キー（`validation/config.py` で処理）

| キー | 説明 | 例 |
|------|------|-----|
| `WIDTH` | 迷路の幅（セル数、1 以上） | `WIDTH=25` |
| `HEIGHT` | 迷路の高さ（セル数、1 以上） | `HEIGHT=20` |
| `ENTRY` | 入口座標 `x,y` | `ENTRY=0,0` |
| `EXIT` | 出口座標 `x,y`（入口とは異なること） | `EXIT=24,19` |
| `OUTPUT_FILE` | 出力ファイル名 | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | 完全迷路にするか（`True`／`False`） | `PERFECT=True` |

### 任意キー（`validation/options.py` で処理）

| キー | 説明 | デフォルト |
|------|------|--------|
| `SEED` | 乱数シード（再現性の確保） | なし（実行ごとにランダム） |
| `ALGORITHM` | 生成アルゴリズム名 | `backtracker` |
| `DISPLAY` | 表示モード名 | `ascii` |
| `SIGN` | 埋め込む記号（使用可能な文字は `2` と `4` のみ） | `42` |

不正な値は原因ごとに区別されたエラー（`ConfigParseError`／`ConfigKeyError`／`ConfigValueError`）となり、分かりやすいメッセージを表示して終了します。

---

## 出力ファイル形式（仕様 IV.5）

- 各セルは大文字の 16 進数 1 桁で表します。閉じた壁はビットで符号化されます：`bit0=北、bit1=東、bit2=南、bit3=西`（閉じている場合は 1）。
- 1 行が迷路の 1 行分のセルに対応します。
- 空行を 1 行挟んだ後、入口 `x,y`、出口 `x,y`、最短経路（`N`／`E`／`S`／`W` を連結した文字列）の計 3 行を記述します。
- すべての行は `\n` で終わります。

---

## 使用アルゴリズムと採用理由

### 生成：再帰的バックトラッカー（反復実装）

すべてのセルが壁で閉じた状態から始め、深さ優先でランダムに通路を掘り進め、行き止まりではスタックを戻ります。全セルを 1 本の木として接続するため（**全域木**）、`PERFECT=True` の条件、すなわち任意の 2 点間に経路がちょうど 1 つ存在することを自然に満たします。

**採用理由:**

- 完全迷路を保証できます（DFS 木＝全域木）。
- 実装がシンプルで、乱数源を `random.Random(seed)` の 1 か所に集約できるため、再現性が高くなります。
- 明示的なスタックを使う反復実装のため、大きな迷路でも Python の再帰上限に達しません。
- 「42」用に予約したセルは掘らないだけで、記号を通路の中に保てます。

アルゴリズムは `ALGORITHM` キーで選択できます（現在は `backtracker` のみ）。`generation/generator.py` の `ALGORITHMS` に、たとえば Prim 法や Kruskal 法を登録すれば直接選択できる設計です。

### プレイアブル盤面（`PERFECT=False`、仕様 IV.4, v2.2）

バックトラッカーが全域木を作った後、`braiding/braiding.py` が 3 フェーズで盤面を整形します：(1) 行き止まりの削減、(2) 四隅と中央の通路化（開口 2 つ以上）、(3) 独立ループ 2 本以上の保証。いずれの壁開放も 3×3 の開放領域を作らず、「42」予約セルには触れません。

### 求解：BFS（幅優先探索）

入口および出口から各セルまでの最短距離を計算し、最短経路とその経路上の全セルを取得します。BFS を用いるため、不完全迷路でも最短経路が保証されます。

---

## 生成後の検証（`verification/verifier.py` + `verification/cli.py`)

専用バリデーターは、生成した迷路が仕様 IV.4 の条件を満たすことを確認します。これは設定ファイルの**入力検証**（`validation/`）とは別の、組み上がった迷路の**構造検証**です。

- 入口と出口が範囲内にあり、互いに異なること
- 外周セルの外向きの壁が閉じていること
- 隣接セル間で共有する壁に矛盾がないこと
- 「42」（完全に閉じた `0xF` セル）を除くすべてのセルが連結していること
- 完全に開いた 3×3 領域がないこと（通路幅は最大 2 セル）
- `PERFECT` の場合、経路がちょうど 1 つであること（閉路がないこと）
- `PERFECT=False` の場合、四隅と中央が開いた通路であり、独立ループが 2 本以上、行き止まりが僅少であること
- 付記された最短経路が実際に通行可能で、かつ最短であること

メインプログラムは生成直後にこの検証を実行し、問題があれば警告します。ライブラリ（`verification.verifier.validate()`）としても CLI（`python3 -m verification.cli <file>`）としても利用できます。

---

## 再利用可能なコードと使用例

パイプラインは役割ごとのパッケージに分割されており、各モジュールは `a_maze_ing.py` に依存しないため単独でインポートできます。

```python
import random
from core.maze import Maze, solve, solution_cells
from generation.backtracker import generate_backtracker
from generation.initializer import reserved_cells

# 「42」用セルを予約して迷路を生成
reserved = reserved_cells(25, 20)
maze = generate_backtracker(25, 20, reserved, random.Random(42), start=(0, 0))

# 解（最短経路）を取得
path = solve(maze, (0, 0), (24, 19))           # 例: "EESS..."
cells = solution_cells(maze, (0, 0), (24, 19)) # 経路上にあるセルの集合

# 壁コードにアクセス（bit0=N、bit1=E、bit2=S、bit3=W、閉じている場合は 1）
code = maze.cells[0][0]
```

主なパッケージ:

- `core/maze.py`：壁の表現（`Maze`）、`bfs_distances`、`solve`、`solution_cells`
- `core/metrics.py`：`count_loops`、`count_dead_ends`（braiding と verification が共有）
- `generation/initializer.py`：初期マップの生成と「42」記号の配置
- `generation/backtracker.py` / `generation/generator.py`：生成アルゴリズムと選択用レジストリ
- `braiding/braiding.py`：不完全迷路（プレイアブル盤面）への変換
- `output/writer.py` / `output/ascii_display.py` / `output/display.py`：出力と表示
- `verification/verifier.py` / `verification/cli.py`：条件検証（ライブラリ／CLI）

ジェネレーターは、自己完結した単一ファイルの `pip` パッケージ（`mazegen.py`）としても配布されています。ビルド済み成果物（`mazegen-1.0.0-py3-none-any.whl` と `mazegen-1.0.0.tar.gz`）はリポジトリ直下にあります。MIT ライセンス（`LICENSE.md`）で公開しており、後続の 42 プロジェクトでの再利用が明示的に許可されています。

```python
from mazegen import MazeGenerator

gen = MazeGenerator(20, 15, seed=1, perfect=False).generate()
grid = gen.grid                       # 4 ビットの壁コードからなる 2 次元配列
path = gen.solution((0, 0), (19, 14)) # 最短経路 "N/E/S/W"
```

---

## チームとプロジェクト管理

- **メンバーと担当:**
  - **naarai**：コア機能と生成。`core/maze.py`（壁モデル、BFS／求解）、`generation/backtracker.py`／`braiding/braiding.py`（不完全迷路用ボード）、および再利用可能な `mazegen` パッケージを担当。
  - **ksadayas**：I/O と検証。`validation/config.py`／`validation/options.py`／`core/errors.py`（設定解析）、`output/writer.py`／`output/ascii_display.py`、`verification/verifier.py`（ASCII 表示と対話）、テスト、ドキュメントを担当。
- **計画と発展:** 「求解 → 初期化（42）→ 生成 → 出力 → 表示 → 検証」の順で段階的に構築し、各機能を小さな単位でコミットしました。
- **うまくいった点:** 壁の表現を 1 か所（`core/maze.py`）に集約したことで、生成・表示・出力・検証の不整合を防げました。例外を致命的／非致命的に分けたことで、エラーの判別も容易になりました。`PERFECT=False` のボードは仕様 v2.2 のプレイアブル要件（四隅・中央の通路化、独立ループ 2 本以上、行き止まり僅少）を満たしています。
- **改善できる点:** 行き止まりは僅少に抑えていますが 0 にはしておらず、「行き止まりなし」ボーナスは未達です。実装済みの生成アルゴリズムは再帰的バックトラッカーのみです（`ALGORITHMS` レジストリはボーナスとして Prim 法／Kruskal 法を追加できるよう準備済み）。また、表示は ASCII のみで、MLX による表示は今後の課題です。

---

## 参考資料（参照先／AI 利用）

- 迷路生成アルゴリズム（再帰的バックトラッカー／Prim 法／Kruskal 法）の一般的な解説
- グラフ理論における全域木と完全迷路の対応関係
- 「42」記号の正確な形状は、課題 PDF（`a_maze_ing.pdf`）の図から取得

**AI の利用:** 設計のブレインストーミング、各モジュールの docstring・型注釈付き実装、テスト作成、PDF からの「42」形状の抽出（画像解析）、README の推敲に AI を利用しました。
