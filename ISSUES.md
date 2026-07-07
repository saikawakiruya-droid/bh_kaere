# ISSUES — 課題PDF適合性ギャップ

`a_maze_ing.pdf`（**Version 2.2**）とプロダクト・テストを突き合わせた結果、
未対応の項目を記録する。解決したら `[x]` にしてクローズ理由を追記する。

> 重要: リポジトリ内の要約 `a_maze_ing.md` は **v2.1** 時点のもので、
> PDF v2.2 で追加された要件（Pac-Man 盤面・LICENSE.md・maze_analyzer.py）が
> 反映されていない。以下の #1〜#3 はすべて v2.2 で追加/明文化された要件。

---

## 必須要件（未対応）

- [ ] **#1 LICENSE.md がリポジトリ直下にない**（PDF Ch.VI, v2.2 で必須化）
  - 再利用モジュールを後続プロジェクトが再利用・再配布できることを明示する
    ライセンスファイルをルートに置く必要がある。
  - `pyproject.toml` は `license = MIT` を宣言しているが、ファイル本体が無い。

- [ ] **#2 PERFECT=False（デフォルト）の Pac-Man 盤面要件が未実装・未検証**（PDF IV.4, v2.2）
  v2.2 では PERFECT=False 時、単なる「ループのある迷路」ではなく
  「Pac-Man 的ゲームにそのまま使える盤面」が要求される：
  - [ ] 四隅と中央が開いた通路であること — 現状、保証も検証もない
        （特に「42」サインは中央付近に配置されるため、中央セルが
        閉鎖セルになり得る）
  - [ ] **独立ルート（ループ）が2本以上** — `braiding.braid()` はデッドエンド
        削減でループを作るが、本数の保証がない（0〜1本でも警告されない）。
        「完全迷路＋壁1枚除去（ループ1本）は不合格」と明記されている
  - [ ] デッドエンドは稀（数個は許容）であること — braid 後の残数を
        数えて抑制・報告する仕組みがない
  - [ ] `validator.validate()` は `perfect=False` のときプレイアブル要件を
        一切チェックしない（perfect 用チェックをスキップするだけ）

- [ ] **#3 課題付属の `maze_analyzer.py` による検証が未組込**（PDF IV.5, v2.2）
  - 出力ファイルの整合性と perfect / playable 判定を行う公式スクリプト。
    入手してテスト/Make ターゲットから実行し、両モードの出力が
    期待判定になることを確認する。

## テスト不足

- [ ] **#4 Pac-Man 盤面要件のテストがない**
  - `tests/test_braiding.py` は「エッジ数が増える（ループができる）」ことしか
    確認していない。以下のテストを追加する：
    - PERFECT=False 時に四隅・中央が通路であること
    - 独立ループ数（= 開エッジ数 −（自由セル数 − 1)）が 2 以上であること
    - デッドエンド残数が閾値以下であること
    - 小さい迷路（braid が壁を開けにくい条件）でも上記が成立するか

## ドキュメント（README ほか）

- [ ] **#5 README の再利用モジュール文書が Ch.VI 要件と不一致**
  - Ch.VI は「パッケージ化されたモジュール（`mazegen.MazeGenerator`）の
    インスタンス化・パラメータ・構造アクセス・解の取得」を README にも
    記載することを要求。現状の「Reusable code and usage」節は内部モジュール
    （`maze.py` / `generator.py` / `initializer.py`）の使用例になっている。
  - さらに「Packaging as a single-file pip package (mazegen-*) is future work」
    という記述が残っているが、実際には `mazegen.py` と wheel/tar.gz が存在し
    矛盾している。
- [ ] **#6 README 1行目の `<login>` プレースホルダが未置換**（PDF Ch.VII）
- [ ] **#7 README「Team and project management」の Members and roles が
  `(fill in)` のまま**（PDF Ch.VII 必須項目）
- [ ] **#8 README の「What could improve」が実装状況と乖離**
  - braiding / 2セル幅の後処理 / パッケージングを「未着手」と記載しているが
    実装済み。振り返りとして現状に合わせ更新する。
- [ ] **#9 README に PERFECT=False（Pac-Man 盤面）モードの仕様説明がない**
  - v2.2 要件（四隅・中央・ループ2本以上・デッドエンド稀）と、現状の
    実装がどこまで満たすかを明記する。
- [ ] **#10 `a_maze_ing.md`（要約）が v2.1 のまま** — v2.2 の差分
  （IV.4 Pac-Man 盤面、Ch.VI LICENSE.md、IV.5 maze_analyzer.py、
  Ch.VIII ボーナス例の変更）を反映する。

## 軽微 / ボーナス

- [ ] **#11 (minor) `mazegen.py` の `_braid()` は 3x3 開放禁止・「42」保護を
  考慮しない** — 単体モジュールの要件（Ch.VI）としては許容だが、本課題の
  盤面生成に再利用すると IV.4 違反の迷路を作り得る。docstring に制約を
  明記するか、本体 `braiding.py` と同等のガードを入れる。
- [ ] **#12 (bonus) デッドエンド0の完全ブレイド盤面**（PDF Ch.VIII）
  - `maze_analyzer.py --max-dead-ends 0` で確認できる「デッドエンドなし」
    盤面はボーナス対象。braid の残デッドエンド解消（2本目の壁開放許可など）
    が必要。

---

## 適合確認済み（参考）

- 実行形態 `python3 a_maze_ing.py config.txt` / 主ファイル名（IV.2）
- 必須キー6種の検証・`#` コメント・エラー時の原因別メッセージ（IV.3）
- seed 再現性・壁の整合性・境界壁・連結性・3x3 開放禁止・
  PERFECT=True の完全迷路判定（IV.4、`validator.py` で自動検証）
- 出力ファイル形式（16進・空行・ENTRY/EXIT/PATH・`\n` 終端）（IV.5）
- ASCII 表示と対話（再生成・経路トグル・壁色変更）（Ch.V）
- `mazegen-1.0.0` の whl/tar.gz がルートに存在し、`pyproject.toml` から
  再ビルド可能（Ch.VI 前半）
- Makefile の install/run/debug/clean/lint/lint-strict（III.2）
