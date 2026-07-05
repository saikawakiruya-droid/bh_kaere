"""Generate end-to-end examples of the whole A-Maze-ing pipeline.

Run: ``python examples/build_examples.py``

For each scenario it writes two files into ``examples/``:

- ``<name>.txt``          a real config file (``KEY=VALUE``, all keys shown),
                          runnable as ``python3 a_maze_ing.py examples/<name>.txt``
- ``<name>_result.txt``   the full result: the spec IV.5 hex output produced by
                          the program, followed by the ASCII rendering (entry
                          ``E`` / exit ``X`` / the single shortest path ``*`` /
                          "42" reserved cells ``#``)

The set is arranged so several config values can be compared side by side:

- ``PERFECT=True`` (perfect maze) vs ``PERFECT=False`` (playable Pac-Man board)
- different ``ENTRY`` / ``EXIT`` (corners vs interior cells)
- same board, different ``SEED`` (06 vs 07)
- same board, different ``SIGN`` glyphs (08 vs 09)
- same size, the "42" sign present vs omitted depending on ``ENTRY``/``EXIT``
  (10 vs 11)

The examples are development artifacts and are not part of the submission.
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from typing import Any, Dict, List, Tuple

# Add the parent of examples/ (the project root) to the import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a_maze_ing import build_maze          # noqa: E402
from config import parse_config            # noqa: E402
from display import render_ascii           # noqa: E402
from maze import path_to_cells, solve      # noqa: E402
from validator import validate             # noqa: E402
from writer import format_maze             # noqa: E402

Coord = Tuple[int, int]
HERE = os.path.dirname(os.path.abspath(__file__))


def _write(name: str, text: str) -> None:
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")
    print(f"  -> {name}")


def _config_text(width: int, height: int, entry: Coord, exit_: Coord,
                 perfect: bool, seed: int, sign: str,
                 output_file: str) -> str:
    return (
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


def build(name: str, width: int, height: int, entry: Coord, exit_: Coord,
          perfect: bool, seed: int = 42, sign: str = "42") -> None:
    """Write one scenario's config file and full result file."""
    mode = "perfect maze" if perfect else "playable Pac-Man board"
    print(f"[{name}] {width}x{height} PERFECT={perfect} "
          f"entry={entry} exit={exit_} seed={seed} sign={sign} ({mode})")

    # 1. Write a real config file and parse it back (exercise the real path).
    cfg_name = f"{name}.txt"
    _write(cfg_name, _config_text(width, height, entry, exit_, perfect, seed,
                                  sign, output_file=f"{name}.out"))
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


def main() -> None:
    scenarios: List[Dict[str, Any]] = [
        # Playable Pac-Man board (PERFECT=False): open corners/centre + loops.
        dict(name="01_playable_25x20", width=25, height=20,
             entry=(0, 0), exit_=(24, 19), perfect=False),
        # Perfect maze (PERFECT=True): single path, dead ends allowed.
        dict(name="02_perfect_20x15", width=20, height=15,
             entry=(0, 0), exit_=(19, 14), perfect=True),
        # Wide playable board.
        dict(name="03_playable_wide_30x12", width=30, height=12,
             entry=(0, 0), exit_=(29, 11), perfect=False, seed=7),
        # Perfect maze where the entry near the centre relocates the "42".
        dict(name="04_perfect_relocated_20x15", width=20, height=15,
             entry=(10, 7), exit_=(0, 0), perfect=True),
        # Different entry/exit: interior cells instead of corners.
        dict(name="05_perfect_custom_endpoints_22x16", width=22, height=16,
             entry=(3, 2), exit_=(18, 13), perfect=True),
        # Same board, different SEED (06 vs 07) -> different maze, both valid.
        dict(name="06_playable_seed1_20x15", width=20, height=15,
             entry=(0, 0), exit_=(19, 14), perfect=False, seed=1),
        dict(name="07_playable_seed2_20x15", width=20, height=15,
             entry=(0, 0), exit_=(19, 14), perfect=False, seed=2),
        # Same board, different SIGN glyphs (08 "42" vs 09 "24").
        dict(name="08_sign_42_24x14", width=24, height=14,
             entry=(0, 0), exit_=(23, 13), perfect=True, sign="42"),
        dict(name="09_sign_24_24x14", width=24, height=14,
             entry=(0, 0), exit_=(23, 13), perfect=True, sign="24"),
        # Same size 8x7: the "42" sign is placed or omitted depending only on
        # ENTRY/EXIT (10 places it, 11 blocks every placement -> omitted).
        dict(name="10_sign_present_8x7", width=8, height=7,
             entry=(0, 6), exit_=(7, 0), perfect=True),
        dict(name="11_sign_omitted_8x7", width=8, height=7,
             entry=(0, 1), exit_=(7, 6), perfect=True),
    ]
    for s in scenarios:
        build(**s)
    print("\nDone: wrote to examples/.")


if __name__ == "__main__":
    main()
