"""Generate end-to-end examples of the whole A-Maze-ing pipeline.

Run: ``python examples/build_examples.py``

For each scenario it writes two files into ``examples/``:

- ``<name>.txt``          a real config file (``KEY=VALUE``), runnable as
                          ``python3 a_maze_ing.py examples/<name>.txt``
- ``<name>_result.txt``   the full result: the spec IV.5 hex output produced by
                          the program, followed by the ASCII rendering (entry
                          ``E`` / exit ``X`` / shortest path ``*`` / "42"
                          reserved cells ``#``)

Both maze modes are covered so the examples reflect the whole project:

- ``PERFECT=True``  — a perfect maze (a single path; corners may be dead ends).
- ``PERFECT=False`` — a playable Pac-Man board (open corners/centre, at least
  two loops, rare dead ends).

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
from maze import solution_cells, solve     # noqa: E402
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
                 perfect: bool, seed: int, output_file: str) -> str:
    return (
        f"# {output_file} example config\n"
        f"WIDTH={width}\n"
        f"HEIGHT={height}\n"
        f"ENTRY={entry[0]},{entry[1]}\n"
        f"EXIT={exit_[0]},{exit_[1]}\n"
        f"OUTPUT_FILE={output_file}\n"
        f"PERFECT={perfect}\n"
        f"SEED={seed}\n"
    )


def build(name: str, width: int, height: int, entry: Coord, exit_: Coord,
          perfect: bool, seed: int = 42) -> None:
    """Write one scenario's config file and full result file."""
    mode = "perfect maze" if perfect else "playable Pac-Man board"
    print(f"[{name}] {width}x{height} PERFECT={perfect} "
          f"entry={entry} exit={exit_} ({mode})")

    # 1. Write a real config file and parse it back (exercise the real path).
    cfg_name = f"{name}.txt"
    _write(cfg_name, _config_text(width, height, entry, exit_, perfect, seed,
                                  output_file=f"{name}.out"))
    config = parse_config(os.path.join(HERE, cfg_name))

    # 2. Build the maze (capture any sign-omission warning printed to stdout).
    buf = io.StringIO()
    with redirect_stdout(buf):
        maze, reserved = build_maze(config)
    note = buf.getvalue().strip()

    # 3. Solve and validate exactly as the main program does.
    solution = solve(maze, entry, exit_)
    path = solution_cells(maze, entry, exit_)
    problems = validate(maze, entry, exit_, reserved=reserved,
                        perfect=perfect, playable=not perfect,
                        solution=solution)

    # 4. Compose the result file: hex output (spec IV.5) + ASCII rendering.
    header = [
        f"# {name}: {width}x{height} PERFECT={perfect} "
        f"entry={entry} exit={exit_} seed={seed} ({mode})",
        f"# reserved cells (42) = {len(reserved)}",
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
        + "\n\n== ASCII rendering (E=entry, X=exit, *=path, #=42) ==\n"
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
        dict(name="04_relocated_20x15", width=20, height=15,
             entry=(10, 7), exit_=(0, 0), perfect=True),
        # Too small for the sign -> "42" omitted (still a valid maze).
        dict(name="05_sign_omitted_7x7", width=7, height=7,
             entry=(0, 0), exit_=(6, 6), perfect=True),
    ]
    for s in scenarios:
        build(**s)
    print("\nDone: wrote to examples/.")


if __name__ == "__main__":
    main()
