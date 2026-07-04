"""Generate several initialization-map examples and write them to examples/.

Run: ``python examples/build_examples.py``

For each pattern it writes two files:

- ``*_init.txt``      the initialization map (all cells closed + the "42"
                      reserved cells shown as ``#``)
- ``*_generated.txt`` the maze after running the recursive backtracker on the
                      above (the surroundings become passages and "42" emerges)

The initialization map is the set of "cells walled on all sides", showing the
state where "42" has been reserved as closed cells within it.
"""

from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout
from typing import Any, Dict, List, Optional, Set, Tuple

# Add the parent of examples/ (the project root) to the import path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from display import render_ascii          # noqa: E402
from generator import generate_backtracker  # noqa: E402
from initializer import initialize_maze    # noqa: E402
from maze import solution_cells            # noqa: E402

Coord = Tuple[int, int]
HERE = os.path.dirname(os.path.abspath(__file__))


def _write(name: str, text: str) -> None:
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(f"  -> {name}")


def build(name: str, width: int, height: int,
          entry: Coord, exit_: Coord, seed: int = 42) -> None:
    """Write the initialization map and generated maze for one pattern."""
    print(f"[{name}] {width}x{height} entry={entry} exit={exit_}")

    # initialize_maze prints a warning to stdout when the sign cannot be
    # placed, so capture it.
    buf = io.StringIO()
    with redirect_stdout(buf):
        maze, reserved = initialize_maze(
            width, height, entry=entry, exit_=exit_)
    note = buf.getvalue().strip()

    header = (f"# {name}: {width}x{height} "
              f"entry={entry} exit={exit_}\n"
              f"# reserved cells (42) = {len(reserved)}")
    if note:
        header += f"\n# {note}"

    init_view = render_ascii(
        maze, entry=entry, exit_=exit_, reserved=reserved)
    _write(f"{name}_init.txt", header + "\n" + init_view)

    # Generate (never carving reserved cells) -> "42" emerges.
    gen = generate_backtracker(
        width, height, reserved, random.Random(seed), start=entry)
    path: Optional[Set[Coord]] = solution_cells(gen, entry, exit_)
    gen_view = render_ascii(
        gen, entry=entry, exit_=exit_, path=path, reserved=reserved)
    _write(f"{name}_generated.txt",
           header + f"\n# seed={seed} / * = shortest path\n" + gen_view)


def main() -> None:
    # The sign is always identical (PDF-compliant, natural scale, gap 1). The
    # examples use that fixed sign.
    patterns: List[Dict[str, Any]] = [
        # Standard size
        dict(name="01_standard_20x15", width=20, height=15,
             entry=(0, 0), exit_=(19, 14)),
        # Wide
        dict(name="02_wide_30x12", width=30, height=12,
             entry=(0, 0), exit_=(29, 11)),
        # Entry near the center collides with the sign (relocated to a
        # non-overlapping position)
        dict(name="03_relocated_20x15", width=20, height=15,
             entry=(10, 7), exit_=(0, 0)),
        # Same size 8x7, entry/exit are safe -> 42 can be placed
        dict(name="04a_endpoints_ok_8x7", width=8, height=7,
             entry=(0, 6), exit_=(7, 0)),
        # Same size 8x7, entry on a cell common to all placements -> 42 cannot
        # be placed and is omitted
        dict(name="04b_endpoints_block_8x7", width=8, height=7,
             entry=(0, 1), exit_=(7, 6)),
        # 7x7: fits the frame but the "2" notch gets trapped and generation is
        # impossible -> omitted
        dict(name="05_omitted_7x7", width=7, height=7,
             entry=(0, 0), exit_=(6, 6)),
    ]
    for p in patterns:
        build(**p)
    print("\nDone: wrote to examples/.")


if __name__ == "__main__":
    main()
