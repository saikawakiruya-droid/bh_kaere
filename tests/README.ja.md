> **注記（提出対象外）:** これはリポジトリ直下の `README.md`（英語・提出物）の
> 日本語参考訳です。`tests/` 配下に置いており提出しません。内容が食い違った
> 場合は直下の `README.md` を正とします。

---

*This project has been created as part of the 42 curriculum by naarai, ksadayas.*

# A-Maze-ing — This is the way

自作の迷路ジェネレータです。設定ファイルを読み込み、（任意で完全な）迷路を
生成し、壁を16進表現したファイルとして書き出します。加えてターミナルへの
ASCII 描画と、生成結果が条件を満たすか確認する専用のバリデータを備えます。

---

## 概要（Description）

- 設定ファイル（`KEY=VALUE`）を読み込んで迷路を生成する。
- 迷路の中央に、いくつもの完全閉塞セルで描かれた **「42」** が浮かび上がる。
- `PERFECT=True` のとき、入口と出口の間の経路がちょうど1本（全域木）になる。
- `PERFECT=False` のとき、**プレイアブルな Pac-Man 盤面**を生成する
  （仕様 IV.4, v2.2）：四隅と中央が開いた通路、独立ループが2本以上、
  デッドエンドは稀。
- 生成後に条件を自動検証する（連結性、壁の整合、境界、3x3 開放なし、最短
  経路、そして `PERFECT=False` ではプレイアブル盤面の規則）。
- 出力ファイルは仕様の16進形式を用い、同梱のバリデータや Moulinette で
  チェックできる。
- コードフローの詳しい解説（図付き）を Notion にまとめている：
  https://app.notion.com/p/3987e1ed867f81a8ab6af4b874cec007

---

## ファイル構成（提出コード対テスト）

**提出・採点対象（リポジトリ直下）:**

| ファイル | 役割 |
|------|------|
| `a_maze_ing.py` | メインプログラム（エントリポイント） |
| `config.py` | 設定ファイル解析：必須キー + 任意キー（`Options`） |
| `mazegen.py` | 再利用モジュール（単一ファイル） |
| `mazegen-1.0.0-*.whl` / `.tar.gz` | ビルド済みパッケージ |
| `LICENSE.md` | `mazegen` モジュールの再利用を許可する MIT ライセンス（仕様 VI） |
| `config.txt` / `Makefile` / `pyproject.toml` / `setup.cfg` / `README.md` | 設定・ビルド・文書 |

迷路パイプライン本体は `engine/` パッケージ配下にあり、各モジュールは単体で
import できる（詳細は後述「再利用できるコード」参照）：

| モジュール | 役割 |
|------|------|
| `engine/maze.py` | コア（壁表現、開閉、BFS 距離、最短経路） |
| `engine/build.py` | 「42」サイン予約+初期マップ、生成アルゴリズム、braiding（`PERFECT=False`） |
| `engine/output.py` | 出力ファイル書き出し（16進形式）+ ASCII 描画 |
| `engine/validator.py` | 生成後の条件チェック（ライブラリ + CLI） |
| `engine/errors.py` | 例外階層 |

**テスト用（提出・採点対象外。仕様 III.3）:**

- `tests/` 配下の `test_*.py` … 動作確認用。`make test` で実行。
- `examples/` … 開発用に残しているサンプル出力。カバーする各シナリオは
  後述の「使用例」節で再現できるため、ディレクトリ自体は提出物に含めない。

> テストは `tests/` に分離してあるため、提出コード（直下の `*.py`）と明確に
> 区別される。テストはプロジェクトの動作検証のためだけのもの。

---

## 使い方（インストール / 実行）

### 依存関係

実行に外部ライブラリは不要（標準ライブラリのみ）。開発時は `flake8` /
`mypy` / `pytest` を使う。

### セットアップと実行

```bash
# 開発ツールを導入（採点環境）
make install

# 迷路を生成して表示（既定の config.txt を使用）
make run

# 別の設定ファイルを指定
make run CONFIG=my_config.txt

# デバッグ実行（pdb）
make debug

# テスト
make test

# 静的チェック（flake8 + mypy）
make lint
```

直接実行する場合：

```bash
python3 a_maze_ing.py config.txt
```

> 注記：`make install` は隔離した仮想環境 `./.venv` を作成し（`uv` があれば
> 優先、なければ標準の `venv`）、`make run` / `make test` / `make lint` はその
> 環境の Python を自動で使う。Python バージョンは `PY_VERSION`（既定 `3.12`）で
> 指定でき、無い環境では利用可能な `python3` に自動フォールバックするため、
> どんな環境でも動く。`.venv` は `make distclean` で削除できる。

> 注記：`flake8` は `setup.cfg` で `max-line-length = 100` に設定している
> （docstring と型ヒントの可読性のため、既定の 79 を意図的に緩めている）。
> `make lint` は課題指定のフラグで `flake8 .` と `mypy .` を実行する。

### 出力ファイルの検証

```bash
python3 -m engine.validator maze.txt
```

---

## 使用例（確認チェックリスト）

`examples/` ディレクトリは提出物ではないため、各シナリオは以下のコマンドで
再現できる。各例に**確認すべき点**を挙げてあり、評価時のチェックリストとして
も使える。

### 1. 標準的な完全迷路（既定の `config.txt`）

```bash
python3 a_maze_ing.py config.txt
```

- [ ] ASCII 描画で、中央付近に完全閉塞セルによる **「42」** が見える。
- [ ] 入口・出口・最短経路が描画に現れている。
- [ ] `maze.txt` が書き出される：16進グリッド（1行1列）、空行1つ、その後
      3行（入口 `x,y` / 出口 `x,y` / `N`/`E`/`S`/`W` の経路）、各行が `\n`
      終端。
- [ ] `warning:` 行が出ない（内蔵の生成後検証が通過：連結性、壁の整合、
      境界壁、3x3 開放なし、`PERFECT=True` で経路がちょうど1本）。
- [ ] `python3 -m engine.validator maze.txt` が `OK` を表示。

### 2. seed による再現性

```bash
python3 a_maze_ing.py config.txt   # config.txt の SEED=42
mv maze.txt run1.txt
python3 a_maze_ing.py config.txt
diff maze.txt run1.txt             # 出力なし = 同一
```

- [ ] 同じ `SEED` なら2回の実行でバイト単位に同一の出力ファイルになる。
- [ ] `SEED` 行を消すと毎回異なる迷路になる。

### 3. プレイアブル盤面（`PERFECT=False`）

```bash
printf 'WIDTH=25\nHEIGHT=20\nENTRY=0,0\nEXIT=24,19\nOUTPUT_FILE=maze.txt\nPERFECT=False\nSEED=42\n' > imperfect.txt
python3 a_maze_ing.py imperfect.txt
```

- [ ] `warning:` 行が出ない：内蔵のプレイアブル盤面検証が通過（四隅と中央が
      開通、独立ループ2本以上、デッドエンドは稀 — 仕様 IV.4, v2.2）。
- [ ] 迷路にループがある（`engine/build.py` の braiding セクション）。経路表示
      をトグルすると別ルートが見え、`python3 -m engine.validator maze.txt` が
      `OK` を返す。
- [ ] 完全連結：「42」以外に孤立セルがない。

### 4. 入口/出口が中央にあるときのサイン再配置

```bash
printf 'WIDTH=20\nHEIGHT=15\nENTRY=10,7\nEXIT=19,14\nOUTPUT_FILE=maze.txt\nPERFECT=True\nSEED=1\n' > center.txt
python3 a_maze_ing.py center.txt
```

- [ ] 「42」が入口と重ならない位置へ再配置される；省略の警告は出ない。

### 5. サインに対して迷路が小さすぎる場合（仕様 IV.4 のフォールバック）

```bash
printf 'WIDTH=5\nHEIGHT=5\nENTRY=0,0\nEXIT=4,4\nOUTPUT_FILE=maze.txt\nPERFECT=True\nSEED=1\n' > tiny.txt
python3 a_maze_ing.py tiny.txt
```

- [ ] サインを省略した旨のメッセージが出る（`warning (does not fit)`）。
- [ ] それでも迷路は通常どおり生成・検証・書き出しされる。

### 6. エラー処理（決してクラッシュしない。仕様 IV.2）

```bash
python3 a_maze_ing.py no_such_file.txt   # ファイルなし
python3 a_maze_ing.py                    # 引数なし -> usage
printf 'WIDTH=20\n' > broken.txt
python3 a_maze_ing.py broken.txt         # 必須キー欠落
printf 'WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=0,0\nOUTPUT_FILE=m.txt\nPERFECT=True\n' > same.txt
python3 a_maze_ing.py same.txt           # ENTRY == EXIT
```

- [ ] いずれも原因別の明確なエラーメッセージ（トレースバックなし）を表示し、
      非ゼロの終了コードで終わる。

### 7. ユーザー操作（仕様 V）

```bash
python3 a_maze_ing.py config.txt   # 対話ターミナルで実行
```

迷路を描画した後、対話メニューが表示される（stdin/stdout が実端末のときだけ。
パイプ実行では自動処理が止まらないようスキップされる）：

```text
=== A-Maze-ing ===
1. Regenerate a new maze (next seed: 43)   ← 新しい迷路を再生成（seed 自動+1）
2. Regenerate with a specified seed         ← seed を指定して再生成
3. Toggle the shortest-path display         ← 最短経路の表示 ON/OFF
4. Change the wall color (current: none)    ← 壁の色を順に変更
5. Quit (current seed: 42)                  ← 終了
choice (1-5):
```

- [ ] メニュー `1`/`2`：新しい迷路を再生成（自動加算 or 指定 seed）。
- [ ] メニュー `3`：最短経路表示の ON/OFF 切り替え。
- [ ] メニュー `4`：壁の色を順に変更。
- [ ] メニュー `5`（または EOF）：きれいに終了。

---

## 設定ファイルの構造と形式

1行1つの `KEY=VALUE`。`#` で始まる行と空行は無視される。

### 必須キー

| キー | 説明 | 例 |
|------|------|-----|
| `WIDTH` | 迷路の幅（セル数、1以上） | `WIDTH=25` |
| `HEIGHT` | 迷路の高さ（セル数、1以上） | `HEIGHT=20` |
| `ENTRY` | 入口座標 `x,y` | `ENTRY=0,0` |
| `EXIT` | 出口座標 `x,y`（入口と異なる） | `EXIT=24,19` |
| `OUTPUT_FILE` | 出力ファイル名 | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | 完全迷路にするか（`True`/`False`） | `PERFECT=True` |

### 任意キー（`config.py` が処理）

| キー | 説明 | 既定値 |
|------|------|--------|
| `SEED` | 乱数シード（再現性） | なし（毎回ランダム） |
| `ALGORITHM` | 生成アルゴリズム名 | `backtracker` |
| `DISPLAY` | 表示モード名 | `ascii` |
| `SIGN` | 埋め込む文字列 | `42` |

不正な値は原因別（`ConfigParseError` / `ConfigKeyError` /
`ConfigValueError`）のエラーとなり、明確なメッセージを出して終了する。

---

## 出力ファイル形式（仕様 IV.5）

- 各セルは1桁の大文字16進数。閉じた壁をビットで符号化：
  `bit0=北, bit1=東, bit2=南, bit3=西`（閉なら1）。
- 1行に1列分のセル。
- 空行を1つ挟み、3行：入口 `x,y` / 出口 `x,y` / 最短経路
  （`N`/`E`/`S`/`W` の連結）。
- すべての行が `\n` で終わる。

---

## 採用アルゴリズムと理由

### 生成：recursive backtracker（反復版）

全セルが壁で閉じた状態から、深さ優先でランダムに掘り進み、行き止まりでは
スタックを戻る。全セルを1本の木（**全域木**）に接続するため、`PERFECT=True`
（任意の2点間の経路がちょうど1本）を自然に満たす。

**理由：**

- 完全迷路を保証する（DFS 木 = 全域木）。
- 実装が単純で、単一の乱数源（`random.Random(seed)`）に集約でき再現性が高い。
- 明示スタックで反復的に実装しており、大きな迷路でも Python の再帰上限に
  当たらない。
- 「42」の予約セルを掘らないだけで、サインが通路の中に残る。

生成アルゴリズムは `ALGORITHM` キーで選択できる（現状は `backtracker`
のみ）。設計上は `engine/build.py` の `ALGORITHMS` に Prim 法や Kruskal 法など
を登録して直接選べるようにしてある。

### `PERFECT=False` のプレイアブル盤面（仕様 IV.4, v2.2）

`PERFECT=False` モードは、単にループが数本ある迷路ではなく、Pac-Man 的ゲームで
使える盤面でなければならない。backtracker で全域木を作った後、`engine/build.py`
の braiding セクションが3フェーズで整形する：

1. **デッドエンド削減** — 各行き止まりが壁を1枚開けて他とつながり、追われる
   プレイヤーが罠にかかりにくくなる。
2. **通路化の強制** — 四隅と中央（`engine/build.py` のサイン予約セクションが
   「42」から除外して確保）を2開口以上にし、ゴーストの四隅とプレイヤーの
   中央スタートを本物の通路にする。
3. **ループ保証** — 独立ループが**2本以上**になるまで壁を追加で開ける
   （完全迷路や、壁を1枚だけ抜いたもの＝単一ループは不合格）。

いずれの壁開放も3x3の完全開放を作らないよう検査し、予約「42」セルには一切
触れない。壁は開けるだけなので連結は保たれる。デッドエンド**0**は課題の
ボーナスで、本生成器は稀（通常は2個程度）に抑える。

### 求解：BFS（幅優先探索）

入口・出口それぞれから各セルへの最短距離を計算し、最短経路（および経路上の
全セル）を得る。BFS なので、不完全迷路でも最短経路を保証する。

---

## 生成後の検証（`engine/validator.py`）

専用バリデータは、生成された迷路が仕様 IV.4 の条件を満たすことを確認する：

- 入口と出口が範囲内で互いに異なる
- 境界セルの外向き壁が閉じている
- 隣接セルが壁を整合的に共有する
- 「42」（`0xF` の完全閉塞セル）以外の全セルが連結
- 3x3 の完全開放がない（通路幅は最大2セル）
- `PERFECT` のとき経路がちょうど1本（サイクルなし）
- `PERFECT=False`（オプトインの `playable` チェック）のとき：四隅と中央が
  開いた通路、独立ループが2本以上、デッドエンドが稀
- 添付の最短経路が実際に歩けて最短である

メインプログラムは生成直後にこの検証を実行し、問題があれば警告する。
ライブラリ（`playable` フラグ付きの `validate()`）としても CLI
（`python3 -m engine.validator <file>`）としても使える。CLI は出力ファイルが意図した
モードを記録しないため構造チェックのみを行う。課題付属の `maze_analyzer.py`
（本リポジトリには同梱していない）は、ファイルが perfect か playable かを
追加で判定できる。

---

## 再利用できるコードとその使い方

パイプライン全体（初期マップ・生成・braiding・検証・出力・表示）は `engine/`
パッケージ配下にある。各モジュールは `config.py` や `a_maze_ing.py` に依存
しないため、**単体のモジュールだけを import して使える** — その処理だけ
必要なら、そのファイル1つ（と唯一の依存先である `engine/maze.py` /
`engine/errors.py`）を別プロジェクトにコピーすればよい。各モジュール自身の
docstring に "Standalone usage" の例があり、`engine/` パッケージ自体の
docstring にはフルパイプラインをつなげた例がある。

必要な処理だけ使う例：

```python
# コアのデータ構造 + BFS 求解だけ
from engine.maze import Maze, solve, solution_cells

# 生成（サイン予約 + recursive backtracker）だけ
import random
from engine.build import reserved_cells, generate_backtracker

reserved = reserved_cells(25, 20)
maze = generate_backtracker(25, 20, reserved, random.Random(42), start=(0, 0))
path = solve(maze, (0, 0), (24, 19))          # 例 "EESS..."
cells = solution_cells(maze, (0, 0), (24, 19)) # 経路上のセル集合

# 検証だけ
from engine.validator import validate
problems = validate(maze, (0, 0), (24, 19))

# ファイル出力/ターミナル表示だけ
from engine.output import write_maze, render_ascii
```

あるいはパッケージ直下からまとめて import：

```python
from engine import Maze, generate_backtracker, braid, validate, write_maze, render_ascii
```

モジュール：

- `engine/maze.py` — 壁表現（`Maze`）、`open_wall`、`bfs_distances`、`solve`、`solution_cells`
- `engine/build.py` — 「42」サイン予約+初期マップ、生成アルゴリズムとレジストリ、braiding
- `engine/validator.py` — 条件チェック（ライブラリ + CLI）
- `engine/output.py` — 出力ファイル書き出し（16進形式）+ ASCII 描画と表示レジストリ
- `engine/errors.py` — 上記が共有する例外階層

生成器は、自己完結した単一ファイルの `pip` パッケージ（`mazegen.py`）
としても配布している。ビルド済み成果物（`mazegen-1.0.0-py3-none-any.whl`
と `mazegen-1.0.0.tar.gz`）がリポジトリ直下にあり、`python -m build` で
ソースから再ビルドできる（`pyproject.toml` 参照）。MIT ライセンス
（`LICENSE.md`）で公開しており、後続の 42 プロジェクトによる再利用を明示的に
許可する。

```python
from mazegen import MazeGenerator

gen = MazeGenerator(20, 15, seed=1, perfect=False).generate()
grid = gen.grid                       # 4ビット壁コードの2次元配列
path = gen.solution((0, 0), (19, 14)) # 最短経路 "N/E/S/W"
```

---

## チームとプロジェクト管理

- **メンバーと役割：**
  - **naarai** — コア & 生成：`engine/maze.py`（壁モデル、BFS/求解）、
    `engine/build.py` の生成・braiding セクション（recursive backtracker、
    不完全盤面）、および `mazegen` 再利用パッケージ。
  - **ksadayas** — 入出力 & 検証：`config.py` / `engine/errors.py`
    （設定解析）、`engine/output.py`、`engine/validator.py`（ASCII + 対話）、
    テスト、ドキュメント。
  - _(上の分担は実際の作業分担に合わせて調整すること。)_
- **計画と変遷：** 「求解 → 初期化(42) → 生成 → 出力 → 表示 → 検証」の順に
  段階的に構築し、機能ごとに小さくコミットした。
- **うまくいった点：** 壁表現を1か所（`engine/maze.py`）に集約したことで、
  生成・表示・出力・検証の間の食い違いを防げた。例外を致命/非致命に階層化
  したことでエラーを区別しやすくなった。`PERFECT=False` モードは仕様 v2.2 の
  プレイアブル盤面規則（四隅と中央の開通、独立ループ2本以上、デッドエンド
  稀）を満たし、`engine/build.py` の braiding セクションで強制し
  `engine/validator.py` で確認している。
- **改善できる点：** デッドエンドは稀に抑えているが0にはしていないため、
  「デッドエンド皆無」ボーナスには未到達。課題付属の `maze_analyzer.py` を
  同梱していないため、それとの突き合わせは手作業。生成アルゴリズムは
  recursive backtracker のみ（`ALGORITHMS` レジストリは Prim/Kruskal を
  ボーナスとして追加できる状態）。表示は ASCII のみで、MLX 表示は今後の課題。

---

## 参考資料（references / AI 利用）

- 迷路生成アルゴリズムの一般的な解説（recursive backtracker / Prim / Kruskal）
- グラフ理論の全域木と完全迷路の対応
- 「42」サインの正確な形は課題 PDF（`a_maze_ing.pdf`）の図から採った

**AI 利用：** 設計のブレインストーミング、docstring と型注釈付きの各モジュール
実装、テスト作成、PDF からの「42」形状抽出（画像解析）、README の推敲に AI を
用いた。
