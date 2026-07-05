# tests/ — テスト README（提出対象外・日本語）

このディレクトリは仕様 III.3 の「動作確認用テスト（提出・採点対象外）」です。
本体（リポジトリ直下の `*.py`）の振る舞いを検証するだけのもので、**提出物には
含めません**。このファイル自体も提出しません。

---

## 実行方法

```bash
# 依存ツール（flake8 / mypy / pytest）を入れる
make install

# 全テスト実行
make test           # = python3 -m pytest -q

# 個別ファイル / 個別関数だけ実行
python3 -m pytest tests/test_playable.py -q
python3 -m pytest tests/test_playable.py::test_at_least_two_independent_loops -q
```

> このリポジトリの開発環境では system の `python` が壊れていたため、venv を
> 使う。Windows の例:
> `uv venv .venv && uv pip install --python .venv flake8 mypy pytest` の後、
> `.venv/Scripts/python.exe -m pytest -q`。

**確認できればよいこと:** 最後に `N passed` と表示され、`failed` / `error` が
0 件であること。

---

## 提出フォルダ作成前の手作業チェックリスト

提出用フォルダ（または提出ブランチ）を作る前に、上から順に手で確認する。

1. **Python バージョン（仕様 III.1 = 3.10 以上）**

   ```bash
   python3 --version        # Python 3.10.x 以上であること
   ```

   提出・評価環境の Python が 3.10 未満だと `from __future__` 以外の新しい
   構文や型注釈で動かない可能性があるため、必ず確認する。

2. **依存ツール導入**： `make install`（pip/uv で flake8・mypy・pytest）。

3. **lint 通過（仕様 III.1 / III.2）**

   ```bash
   make lint          # flake8 . が 0 件、mypy . が 0 エラー
   make lint-strict   # 可能なら mypy --strict も 0 エラー
   ```

4. **テスト全通過**： `make test` で `failed` / `error` が 0。

5. **実行確認（PERFECT=True）**

   ```bash
   make run           # = python3 a_maze_ing.py config.txt
   ```

   `warning:` が出ず、`wrote output file: maze.txt` が出ること。ASCII 表示に
   「42」・入口・出口・最短経路が見えること。

6. **出力ファイル検証**： `python3 validator.py maze.txt` が `OK` を出す。

7. **実行確認（PERFECT=False / Pac-Man 盤面）**：`PERFECT=False` の config で
   実行し、`warning:` が出ないこと（四隅・中央の通路化、ループ2本以上、
   デッドエンド稀を内蔵検証が確認する）。

8. **再利用パッケージの再ビルド確認（仕様 VI）**

   ```bash
   python3 -m build   # mazegen-1.0.0-*.whl / .tar.gz がソースから再生成できる
   ```

9. **README / LICENSE の確認**
   - `README.md` 1 行目の login が正しい（`naarai, ksadayas`）。
   - `LICENSE.md` がリポジトリ直下にある。

10. **提出フォルダに入れる / 入れないの仕分け**
    - **入れる**：直下の `*.py`（`a_maze_ing.py` ほか）、`config.txt`、
      `Makefile`、`pyproject.toml`、`setup.cfg`、`README.md`、`LICENSE.md`、
      `mazegen-1.0.0-*.whl` / `.tar.gz`、パッケージ再ビルドに必要な一式。
    - **入れない**：`tests/`（このディレクトリ）、`examples/`、
      `a_maze_ing.pdf`、`ISSUES.md`、`TASKS.md`、`a_maze_ing.md`、`.venv/`、
      `__pycache__/`、`.mypy_cache/`、`.pytest_cache/`。

11. **後片付け**： `make clean` で一時ファイル・キャッシュを削除してから
    フォルダを作る。

---

## 各テストの使い方と確認観点

すべて pytest 関数。`make test` で一括実行されるが、該当機能をいじったときは
その関数だけを個別実行して確認するとよい。

### test_maze.py — コア（壁表現・BFS・最短経路）

| 関数 | 確認できること |
|------|------|
| `test_entry_equals_exit_returns_empty` | 入口=出口のとき経路が空文字列 |
| `test_straight_corridor` | 一直線通路で正しい方向列を返す |
| `test_shortest_path_on_open_grid` | 開放グリッドで最短長の経路を返す |
| `test_unreachable_returns_none` | 到達不能なら `None` |
| `test_wall_consistency_blocks_move` | 壁があると移動不可 |
| `test_out_of_bounds_raises` | 範囲外座標で例外 |
| `test_bfs_distances_open_grid` | BFS 距離が正しい |
| `test_bfs_distances_excludes_unreachable` | 到達不能セルは距離辞書に含めない |
| `test_solution_cells_*` | 最短経路上セル集合が正しい／到達不能で空 |
| `test_solved_path_is_walkable` | 返した経路が実際に壁を通らず歩ける |

### test_generator.py — 生成（recursive backtracker）

| 関数 | 確認できること |
|------|------|
| `test_all_free_cells_connected` | 予約以外の全セルが連結 |
| `test_reserved_cells_stay_fully_walled` | 予約セル（42）は 0xF のまま |
| `test_perfect_maze_is_spanning_tree` | 辺数=セル数-1 の全域木（完全迷路） |
| `test_seed_reproducibility` | 同 seed で同一結果 |
| `test_different_seeds_differ` | 別 seed で別結果 |
| `test_no_reserved_connects_all` | 予約なしでも全連結 |
| `test_registry_has_backtracker` | アルゴリズム登録に backtracker がある |
| `test_unknown_algorithm_raises` | 未知アルゴリズム名で例外 |
| `test_wall_consistency_after_generation` | 生成後も隣接壁が整合 |

### test_initializer.py — 初期化と「42」配置

| 関数 | 確認できること |
|------|------|
| `test_bitmap_*` / `test_*gap*` | サインのビットマップ寸法・桁間隔・範囲外拒否 |
| `test_unknown_glyph_raises` | 未定義文字で例外 |
| `test_reserved_cells_centered_and_in_bounds` | 予約が中央寄せかつ範囲内 |
| `test_reserved_cell_count_matches_ones` | 予約数がビットの '1' 数と一致 |
| `test_too_small_raises` / `test_frame_too_small_raises_toobig` | 枠が小さいと SignTooBig |
| `test_overlap_relocates_when_room` | 入口/出口と重なるとき再配置 |
| `test_cannot_place_when_not_generatable` | 生成不能配置は SignOverlap |
| `test_smallest_generatable_is_8x6` | 生成可能な最小サイズの境界 |
| `test_endpoints_decide_sign_at_same_size` ほか | 端点位置で配置/省略が決まる |
| `test_too_small_and_overlap_are_distinct` | 2 種のエラーが区別される |
| `test_initialize_maze_*` | 全閉+予約の初期化、省略/再配置時の挙動 |

### test_config.py / test_options 相当 — 設定ファイル検証

| 関数 | 確認できること |
|------|------|
| `test_valid_config` | 正常な config を読める |
| `test_defaults_for_optional` | 省略時に SEED/ALGORITHM/DISPLAY/SIGN が既定値 |
| `test_missing_required_key` | 必須キー欠落でエラー |
| `test_syntax_error` | `KEY=VALUE` でない行でエラー |
| `test_file_not_found` | ファイル無しでエラー |
| `test_non_integer_width` / `test_non_positive_width` | 幅の型/範囲検証 |
| `test_entry_out_of_bounds` / `test_entry_equals_exit` | 端点の範囲・同一検証 |
| `test_bad_coord_format` / `test_bad_perfect_value` / `test_bad_seed` | 値の書式検証 |
| `test_unknown_algorithm` / `test_unknown_display` | 未知の選択肢でエラー |
| `test_bom_config_is_read` | BOM 付きでも読める |
| `test_unknown_key_warns_but_continues` | 未知キーは警告のみで継続 |
| `test_duplicate_key_warns_and_last_wins` | 重複キーは警告し後勝ち |
| `test_errors_are_distinct` | 原因別に例外型が分かれている |

### test_writer.py — 出力ファイル（仕様 IV.5）

| 関数 | 確認できること |
|------|------|
| `test_hex_encoding_matches_wall_bits` | 壁ビット→16進の対応が正しい |
| `test_structure_and_trailing_newlines` | グリッド+空行+3行、各行 `\n` 終端 |
| `test_all_walls_closed_is_F` | 全閉セルが `F` |
| `test_none_solution_writes_blank_line` | 経路 None は空行 |
| `test_write_maze_uses_lf_newlines` | 改行が常に LF |
| `test_write_then_read_roundtrip` | 書き出し→読み戻しで一致 |

### test_validator.py — 検証（仕様 IV.4）

| 関数 | 確認できること |
|------|------|
| `test_generated_maze_is_valid` | 生成直後の迷路が全条件を満たす |
| `test_detects_missing_border` | 境界壁欠落を検出 |
| `test_detects_wall_inconsistency` | 隣接壁の不整合を検出 |
| `test_detects_isolated_cell` | 孤立セルを検出 |
| `test_detects_open_3x3` | 3x3 開放を検出 |
| `test_detects_bad_solution` | 壁を突き抜ける不正経路を検出 |
| `test_detects_non_perfect_when_cycle` | ループありを「完全でない」と検出 |
| `test_cli_roundtrip_ok` | 出力ファイルを CLI で検証して OK |

### test_braiding.py — 不完全迷路化（ループ付与）

| 関数 | 確認できること |
|------|------|
| `test_braiding_adds_loops` | 壁を開いてループ（辺）が増える |
| `test_braiding_reduces_dead_ends` | デッドエンドが減る |
| `test_braiding_keeps_connectivity_and_no_3x3` | 連結維持・3x3 なし等を満たす |
| `test_braiding_never_creates_open_3x3` | 3x3 開放を作らない |
| `test_braiding_keeps_reserved_closed` | 予約セルは閉じたまま |
| `test_braiding_reproducible` | 同 seed で再現 |
| `test_braided_maze_not_perfect` | braid 後は完全迷路でなくなる（連結は維持） |

### test_playable.py — Pac-Man 盤面（仕様 IV.4 v2.2 / PERFECT=False）

| 関数 | 確認できること |
|------|------|
| `test_build_playable_passes_validation` | 複数 seed で playable 検証を通る |
| `test_corners_and_centre_are_open_corridors` | 四隅・中央が 2 開口以上の通路 |
| `test_at_least_two_independent_loops` | 独立ループが 2 本以上 |
| `test_dead_ends_stay_rare` | デッドエンドが閾値以下 |
| `test_small_board_still_playable` | サイン省略の小盤面でも妥当 |
| `test_perfect_maze_flagged_as_not_playable` | 完全迷路は not-playable と判定 |
| `test_playable_is_reproducible` | 同 seed で再現 |
| `test_braid_min_loops_guarantee` | braid の `min_loops` が保証される |

### test_display.py — ASCII 表示と操作

| 関数 | 確認できること |
|------|------|
| `test_render_dimensions` | 描画サイズが妥当 |
| `test_render_marks_entry_exit_and_sign` | 入口・出口・サインが表示される |
| `test_show_path_toggle` | 最短経路の表示 ON/OFF が切り替わる |
| `test_wall_color_adds_ansi` | 壁色指定で ANSI 色が付く |
| `test_registry_has_ascii` | 表示モード登録に ascii がある |
| `test_unknown_display_raises` | 未知の表示モードで例外 |

### test_main.py — エンドツーエンド / CLI

| 関数 | 確認できること |
|------|------|
| `test_end_to_end_produces_valid_output` | config→生成→出力が妥当 |
| `test_reproducible_with_seed` | 同 seed で出力ファイルが一致 |
| `test_missing_config_returns_error` | config 無しでエラー終了 |
| `test_no_args_usage` | 引数無しで usage を表示 |
| `test_interact_*` | 対話（seed 入力・EOF・終了）の挙動 |

### test_mazegen.py — 再利用モジュール（`mazegen.MazeGenerator`）

| 関数 | 確認できること |
|------|------|
| `test_generate_fills_grid_connected` | 生成後グリッドが全連結 |
| `test_perfect_is_spanning_tree` | perfect が全域木 |
| `test_seed_reproducible` / `test_different_seed_differs` | seed 再現性 |
| `test_solution_walks_entry_to_exit` | 解が入口→出口を歩ける |
| `test_solution_is_shortest` | 解が最短 |
| `test_solution_cells_count` | 最短経路セル数が経路長+1 |
| `test_imperfect_has_loops` | perfect=False でループができる |
| `test_entry_equals_exit_empty` | 入口=出口で空 |
| `test_wall_code_access` | 壁コード取得 API |
