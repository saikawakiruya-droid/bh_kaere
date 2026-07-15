# ISSUES — 課題PDF適合性ギャップ

課題 `en.subject.pdf`（**Version 2.2**、リポジトリ直下）とプロダクト・テストを
突き合わせた結果を記録する。解決したら `[x]` にしてクローズ理由を追記する。

> 課題ファイルの所在:
> - **v2.2（正典）** … リポジトリ直下の `en.subject.pdf`
> - v2.1（旧版）… `master` ブランチの `a_maze_ing.pdf` / `a_maze_ing.md`
>
> v2.1 には Pac-Man 盤面（IV.4）・LICENSE.md 必須（Ch.VI）・`maze_analyzer.py`
> （IV.5）・デッドエンド0ボーナス（Ch.VIII）が存在しない。**v2.1 を根拠に
> 判断しないこと。**

---

## 必須要件（未対応）

- [ ] **#3 課題付属の `maze_analyzer.py` による検証が未組込**（PDF IV.5, v2.2）
  - 課題が配布する解析スクリプト。出力ファイルの壁エンコード整合性を検査し、
    perfect / playable のどちらかを判定する。
  - 入手してテスト/Make ターゲットから実行し、両モードの出力が期待判定に
    なることを確認する。
  - 注意: IV.5 は playable を「**"42" 以外にデッドエンドが無い**」と記述する
    一方、IV.4 は「デッドエンドは稀（数個は許容）」とする。判定機は IV.5 側
    なので、実機で確認するまで合否は不明。
	確認済み大丈夫そう

## テスト・検証の緩さ

- [ ] **#13 (new) デッドエンド許容閾値が仕様より大幅に緩い**
  - `validator._check_playable` の閾値は `max(4, free_cells // 25)`。
    25x20 盤面では **19個まで許容**してしまう。
  - 課題 IV.4 は「a couple are tolerated（数個）」、IV.5 の解析スクリプトは
    「デッドエンド無し」を playable の条件として挙げる。
  - 実測では全 playable 例で **dead_ends = 2**。つまり現状の実装は十分に
    良いが、**閾値がザルで回帰を検出できない**。閾値を締めるべき。

## ドキュメント（README ほか）

- [ ] **#14 (new) `pyproject.toml` の著者がプレースホルダのまま**
  - `authors = [{ name = "42 student" }]`。`LICENSE.md` / `README.md` の
    `naarai, ksadayas` と不一致。
	これはクリアされてそう？

- [ ] **#15 (new) `SIGN` オプションの説明が実装より過大**
  - README / `options.py` の表は「String to embed（任意文字列）」と読めるが、
    `initializer.GLYPHS` には `'4'` と `'2'` しか定義がなく、`_parse_sign()`
    が他の文字を `ConfigValueError` で弾く。
  - 「使用可能文字は `2` と `4` のみ」と明記する。
  やったけどダブルチェックplz,READMEのこれが見つけられない

## 軽微 / ボーナス

- [ ] **#11 (minor) `mazegen.py` の `_braid()` は 3x3 開放禁止・「42」保護を
  考慮しない** — 単体モジュールの要件（Ch.VI）としては許容だが、本課題の
  盤面生成に再利用すると IV.4 違反の迷路を作り得る。docstring に制約を
  明記するか、本体 `braiding.py` と同等のガードを入れる。
  一応
　    def _braid(self, ratio: float = 1.0) -> None:
        """Reduce dead ends to create loops (imperfect-maze conversion).

        Note:
            This standalone braiding is intentionally minimal: it does NOT
            guard against fully-open 3x3 areas, and it does NOT protect the
            "42" sign cells. It is meant only for the reusable
            ``MazeGenerator`` module. Do not reuse it to build the spec IV.4
            board -- that path uses ``braiding.braiding.braid`` in the main
            project, which enforces the "passages at most 2 cells wide"
            (no open 3x3) and sign-protection rules.
        """
		いれといた

- [ ] **#12 (bonus) デッドエンド0の完全ブレイド盤面**（PDF Ch.VIII）
  - `maze_analyzer.py --max-dead-ends 0` で確認できる「デッドエンドなし」
    盤面はボーナス対象。現状は残デッドエンド 2 個。braid の残デッドエンド
    解消（2本目の壁開放許可など）が必要。
	これも大丈夫そう

---

## 解決済み

- [x] **#1 LICENSE.md がリポジトリ直下にない**（PDF Ch.VI, v2.2）
  → `LICENSE.md`（MIT、再利用・再配布を明示的に許可）を追加。

- [x] **#2 PERFECT=False の Pac-Man 盤面要件が未実装・未検証**（PDF IV.4, v2.2）
  → `braiding.braid()` を3フェーズ化（デッドエンド削減 / 四隅・中央の通路化 /
    独立ループ2本以上の保証）。`a_maze_ing.build_maze()` から結線し、
    `validator.validate(playable=True)` で自動検証。

- [x] **#2b 中央セルがデッドエンドになる不具合**（IV.4「四隅と中央は open corridor」違反）
  → `initializer` はサインが中央セル**自体**に重ならないことしか保証して
    おらず、"42" が中央を三方から囲むと braid が開口2本を作れなかった
    （30x12 seed=7 で再現、`examples/03` に誤った `validation: OK` が
    コミットされていた）。さらに `validator._check_playable` は「0xF でない」
    「到達可能」しか見ておらず、開口数を検証していなかったため見逃していた。
  → `initializer._corridors_openable()` を追加し、通路セルが常に自由な隣接を
    2つ以上持つ配置のみ採用。`validator` に開口数 >= 2 の検査を追加。
    回帰テスト `test_corners_and_centre_are_open_corridors`（6ジオメトリ）と
    `test_validator_rejects_a_dead_end_centre` を追加。

- [x] **#4 Pac-Man 盤面要件のテストがない**
  → `tests/test_playable.py` にループ数・デッドエンド数・四隅/中央の開口・
    小盤面・再現性のテストを追加。

- [x] **#5 README の再利用モジュール文書が Ch.VI 要件と不一致**
  → `mazegen.MazeGenerator` のインスタンス化・パラメータ・構造アクセス・
    解の取得を README に記載。「パッケージ化は future work」の記述も削除。

- [x] **#6 README 1行目の `<login>` プレースホルダが未置換**（Ch.VII）
  → `naarai, ksadayas` に置換。

- [x] **#7 README の Members and roles が `(fill in)` のまま**（Ch.VII）
  → 各メンバーの担当モジュールを記載。

- [x] **#8 README の「What could improve」が実装状況と乖離**
  → 現状（デッドエンド0未達 / maze_analyzer 未同梱 / 単一アルゴリズム /
    ASCII のみ）に更新。

- [x] **#9 README に PERFECT=False（Pac-Man 盤面）モードの仕様説明がない**
  → 「Playable board when `PERFECT=False`」節を追加。

- [x] **#10 `a_maze_ing.md`（要約）が v2.1 のまま**
  → 要約は v2.1 時点の資料と割り切り、正典を `en.subject.pdf`（v2.2）と
    明示（本ファイル冒頭）。判断は常に v2.2 を参照する。

---

## 適合確認済み（参考）

- 実行形態 `python3 a_maze_ing.py config.txt` / 主ファイル名（IV.2）
- 必須キー6種の検証・`#` コメント・エラー時の原因別メッセージ（IV.3）
- seed 再現性・壁の整合性・境界壁・連結性・3x3 開放禁止・
  PERFECT=True の完全迷路判定（IV.4、`validator.py` で自動検証）
- PERFECT=False の playable 盤面（四隅・中央の open corridor、独立ループ
  2本以上、デッドエンド僅少）— 66構成（11サイズ x 6シード）で検証済み
- 出力ファイル形式（16進・空行・ENTRY/EXIT/PATH・`\n` 終端）（IV.5）
- ASCII 表示と対話（再生成・経路トグル・壁色変更）（Ch.V）
- `mazegen-1.0.0` の whl/tar.gz がルートに存在し、`pyproject.toml` から
  再ビルド可能（Ch.VI 前半）
- `LICENSE.md` がルートに存在し、再利用・再配布を明示的に許可（Ch.VI 後半）
- Makefile の install/run/debug/clean/lint/lint-strict（III.2）
