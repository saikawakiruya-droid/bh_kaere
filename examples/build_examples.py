"""Generate end-to-end examples of the whole A-Maze-ing pipeline.

Run: ``python examples/build_examples.py``

This script regenerates the entire ``examples/`` set from scratch. It writes
two kinds of scenarios, each carrying its **intent** as a comment so the reason
the example exists is obvious at a glance:

1. Success cases (``NN_*.txt`` + ``NN_*_result.txt``)
   A real config file plus the full result: the spec IV.5 hex output followed
   by the ASCII rendering (entry ``E`` / exit ``X`` / one shortest path ``*`` /
   "42" reserved cells ``#``). The set deliberately varies the **ENTRY / EXIT
   position** — corners, edge midpoints and interior cells — because a maze
   must work no matter where the endpoints sit, not only at the corners.

2. Error cases (``err_*.txt`` + ``err_*_result.txt``)
   An intentionally invalid config file plus the captured console output and
   exit code from actually running ``python3 a_maze_ing.py`` on it. These show
   that every category of bad input is rejected with a clear message instead of
   a crash (spec: "handles all errors gracefully and never crashes").

The examples are development artifacts and are not part of the submission.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from typing import Any, Dict, List, Optional, Tuple

# Add the parent of examples/ (the project root) to the import path.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from a_maze_ing import build_maze              # noqa: E402
from core.maze import path_to_cells, solve     # noqa: E402
from output.ascii_display import render_ascii  # noqa: E402
from output.writer import format_maze          # noqa: E402
from validation.config import parse_config     # noqa: E402
from verification.verifier import validate     # noqa: E402

Coord = Tuple[int, int]
HERE = os.path.dirname(os.path.abspath(__file__))


def _write(name: str, text: str) -> None:
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    print(f"  -> {name}")


def _clean_examples() -> None:
    """Delete every previously generated example file (keep this script)."""
    for fname in sorted(os.listdir(HERE)):
        if fname == os.path.basename(__file__):
            continue
        if fname.endswith(".txt") or fname.endswith(".out"):
            os.remove(os.path.join(HERE, fname))
            print(f"  removed {fname}")


# --------------------------------------------------------------------------- #
# Success cases
# --------------------------------------------------------------------------- #
def _config_text(intent: str, width: int, height: int, entry: Coord,
                 exit_: Coord, perfect: bool, seed: int, sign: str,
                 output_file: str) -> str:
    """Render a real, runnable config file, leading with its intent comment."""
    return (
        f"# intent (意図): {intent}\n"
        f"# {output_file} example config\n"
        f"# --- required keys ---\n"
        f"WIDTH={width}\n"
        f"HEIGHT={height}\n"
        f"ENTRY={entry[0]},{entry[1]}\n"
        f"EXIT={exit_[0]},{exit_[1]}\n"
        f"OUTPUT_FILE={output_file}\n"
        f"PERFECT={perfect}\n"
        f"# --- optional keys ---\n"
        f"SEED={seed}\n"
        f"ALGORITHM=backtracker\n"
        f"DISPLAY=ascii\n"
        f"SIGN={sign}\n"
    )


def build(name: str, intent: str, width: int, height: int, entry: Coord,
          exit_: Coord, perfect: bool, seed: int = 42,
          sign: str = "42") -> None:
    """Write one success scenario's config file and full result file."""
    mode = "perfect maze" if perfect else "playable Pac-Man board"
    print(f"[{name}] {width}x{height} PERFECT={perfect} "
          f"entry={entry} exit={exit_} seed={seed} sign={sign} ({mode})")

    # 1. Write a real config file and parse it back (exercise the real path).
    cfg_name = f"{name}.txt"
    _write(cfg_name, _config_text(intent, width, height, entry, exit_, perfect,
                                  seed, sign, output_file=f"{name}.out"))
    config = parse_config(os.path.join(HERE, cfg_name))

    # 2. Build the maze (capture any sign-omission warning printed to stdout).
    buf = io.StringIO()
    with redirect_stdout(buf):
        maze, reserved = build_maze(config)
    note = buf.getvalue().strip()

    # 3. Solve and validate exactly as the main program does.
    solution = solve(maze, entry, exit_)
    # Highlight exactly one shortest path (spec V), not every shortest-path
    # cell, so a board with loops does not show several overlaid paths.
    path = path_to_cells(entry, solution) if solution is not None else set()
    problems = validate(maze, entry, exit_, reserved=reserved,
                        perfect=perfect, playable=not perfect,
                        solution=solution)

    # 4. Compose the result file: hex output (spec IV.5) + ASCII rendering.
    header = [
        f"# intent (意図): {intent}",
        f"# {name}: {width}x{height} PERFECT={perfect} "
        f"entry={entry} exit={exit_} seed={seed} sign={sign} ({mode})",
        f"# reserved cells (42) = {len(reserved)} "
        f"({'sign placed' if reserved else 'sign omitted'})",
        f"# validation: {'OK (no problems)' if not problems else problems}",
    ]
    if note:
        header.append(f"# note: {note}")

    hex_output = format_maze(maze, entry, exit_, solution).rstrip("\n")
    render = render_ascii(maze, entry=entry, exit_=exit_, path=path,
                          reserved=reserved)

    body = (
        "\n".join(header)
        + "\n\n== Output file (spec IV.5: hex grid, blank line, "
          "entry / exit / shortest path) ==\n"
        + hex_output
        + "\n\n== ASCII rendering (E=entry, X=exit, *=one shortest path, "
          "#=42) ==\n"
        + render
    )
    _write(f"{name}_result.txt", body)


# --------------------------------------------------------------------------- #
# Error cases
# --------------------------------------------------------------------------- #
def build_error(name: str, intent: str, expect: str, config_body: str) -> None:
    """Write an invalid config and capture what running the program reports.

    Args:
        name: File stem (``err_*``).
        intent: Why this bad-input example exists (kept as a comment).
        expect: The error category we expect to be reported (documentation).
        config_body: The raw config file contents that should be rejected.
    """
    print(f"[{name}] expect={expect}")
    cfg_name = f"{name}.txt"
    header = (
        f"# intent (意図): {intent}\n"
        f"# expected (期待する挙動): {expect}\n"
    )
    _write(cfg_name, header + config_body)

    # Run the real program on the bad config and capture stdout+stderr+code.
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "a_maze_ing.py"),
         os.path.join(HERE, cfg_name)],
        capture_output=True, text=True, cwd=HERE,
    )
    captured = (proc.stdout + proc.stderr).strip() or "(no output)"

    body = (
        f"# intent (意図): {intent}\n"
        f"# expected (期待する挙動): {expect}\n"
        f"# exit code: {proc.returncode} (0=success, 1=handled error, "
        f"2=usage)\n\n"
        "== Config file (invalid on purpose) ==\n"
        + (header + config_body).rstrip("\n")
        + "\n\n== Program output (python3 a_maze_ing.py <cfg>) ==\n"
        + captured
    )
    _write(f"{name}_result.txt", body)


def main() -> None:
    _clean_examples()

    print("\n--- success cases (endpoint variety) ---")
    success: List[Dict[str, Any]] = [
        dict(name="01_corners_playable_25x20",
             intent="角同士・プレイアブル盤面の基本形（四隅と中央が通路、"
                    "独立ループ2本以上）",
             width=25, height=20, entry=(0, 0), exit_=(24, 19),
             perfect=False),
        dict(name="02_corners_perfect_20x15",
             intent="角同士・完全迷路の基本形（入口出口間の経路がちょうど1本）",
             width=20, height=15, entry=(0, 0), exit_=(19, 14),
             perfect=True),
        dict(name="03_top_bottom_edge_mid_perfect_21x15",
             intent="上辺中央→下辺中央。入口出口を辺の中間に置いた完全迷路"
                    "（角以外の辺セルが扱えること）",
             width=21, height=15, entry=(10, 0), exit_=(10, 14),
             perfect=True),
        dict(name="04_left_right_edge_mid_playable_25x15",
             intent="左辺中央→右辺中央。辺の中間を入口出口にしたプレイアブル盤面",
             width=25, height=15, entry=(0, 7), exit_=(24, 7),
             perfect=False),
        dict(name="05_interior_endpoints_perfect_22x16",
             intent="内部セル同士。角でも辺でもない盤面内部に入口出口を置く完全迷路",
             width=22, height=16, entry=(5, 5), exit_=(16, 10),
             perfect=True),
        dict(name="06_interior_to_corner_playable_20x15",
             intent="内部→角。片方だけ内部に置いたプレイアブル盤面"
                    "（内部始点でも四隅・中央の通路化が働くこと）",
             width=20, height=15, entry=(10, 7), exit_=(0, 0),
             perfect=False),
        dict(name="07_near_center_relocates_sign_perfect_20x15",
             intent="中央付近を入口にすると、中央に置かれる「42」が衝突を避けて"
                    "自動的に再配置されること",
             width=20, height=15, entry=(10, 7), exit_=(0, 14),
             perfect=True),
        # Same board, SEED only differs (08 vs 09) -> different maze, both valid.
        dict(name="08_seed1_playable_20x15",
             intent="同一設定でSEEDだけ変える対比その1（seed=1）。09と見比べる",
             width=20, height=15, entry=(0, 0), exit_=(19, 14),
             perfect=False, seed=1),
        dict(name="09_seed2_playable_20x15",
             intent="同一設定でSEEDだけ変える対比その2（seed=2）。08と別の迷路",
             width=20, height=15, entry=(0, 0), exit_=(19, 14),
             perfect=False, seed=2),
        # Same board, SIGN glyph order differs (10 vs 11).
        dict(name="10_sign_42_24x14",
             intent="SIGNのグリフと並び順の対比その1（SIGN=42）。11と見比べる",
             width=24, height=14, entry=(0, 0), exit_=(23, 13),
             perfect=True, sign="42"),
        dict(name="11_sign_24_24x14",
             intent="SIGNのグリフと並び順の対比その2（SIGN=24）。10と鏡像の並び",
             width=24, height=14, entry=(0, 0), exit_=(23, 13),
             perfect=True, sign="24"),
        # Small board: sign placed (12) vs blocked by endpoints -> omitted (13).
        dict(name="12_sign_present_8x7",
             intent="小さい盤面でも入口出口の位置しだいで「42」が置けるケース",
             width=8, height=7, entry=(0, 6), exit_=(7, 0), perfect=True),
        dict(name="13_sign_omitted_8x7",
             intent="小さい盤面で入口出口が全配置を塞ぎ「42」が省略されるケース"
                    "（省略は致命的でなく迷路自体は生成される）",
             width=8, height=7, entry=(0, 1), exit_=(7, 6), perfect=True),
    ]
    for s in success:
        build(**s)

    print("\n--- error cases (every bad-input category) ---")
    errors: List[Dict[str, str]] = [
        dict(name="err_01_missing_required_key",
             intent="必須キー欠落（PERFECT がない）",
             expect="config error: missing required keys",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\n")),
        dict(name="err_02_malformed_line",
             intent="KEY=VALUE 形式でない行（'=' がない）",
             expect="config error: not in 'KEY=VALUE' form",
             config_body=(
                 "WIDTH=20\nHEIGHT 15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\n")),
        dict(name="err_03_width_not_integer",
             intent="WIDTH が整数でない",
             expect="config error: WIDTH must be an integer",
             config_body=(
                 "WIDTH=wide\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\n")),
        dict(name="err_04_nonpositive_size",
             intent="WIDTH が 1 未満",
             expect="config error: WIDTH must be 1 or greater",
             config_body=(
                 "WIDTH=0\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\n")),
        dict(name="err_05_entry_out_of_bounds",
             intent="ENTRY が盤面範囲外",
             expect="config error: ENTRY (...) is outside the maze bounds",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=99,99\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\n")),
        dict(name="err_06_entry_equals_exit",
             intent="ENTRY と EXIT が同一座標",
             expect="config error: ENTRY and EXIT must differ",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=5,5\nEXIT=5,5\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\n")),
        dict(name="err_07_bad_perfect_value",
             intent="PERFECT が真偽値でない",
             expect="config error: PERFECT must be True / False",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=maybe\n")),
        dict(name="err_08_undrawable_sign",
             intent="SIGN に描画不能文字（使えるのは 2 と 4 のみ）",
             expect="config error: SIGN contains characters that cannot be "
                    "drawn",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\nSIGN=7\n")),
        dict(name="err_09_seed_not_integer",
             intent="SEED が整数でない",
             expect="config error: SEED must be an integer",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\nSEED=abc\n")),
        dict(name="err_10_unknown_algorithm",
             intent="未登録の ALGORITHM 名",
             expect="config error: unknown ALGORITHM",
             config_body=(
                 "WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=19,14\n"
                 "OUTPUT_FILE=out.txt\nPERFECT=True\nALGORITHM=prim\n")),
    ]
    for e in errors:
        build_error(**e)

    print("\nDone: wrote to examples/.")


if __name__ == "__main__":
    main()
