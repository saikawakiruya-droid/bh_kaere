"""ASCII-art rendering of a maze.

Registered under the name ``"ascii"`` in :mod:`engine.display`'s
``DISPLAY_MODES`` registry; kept in its own file so a bonus display mode
(e.g. MLX) can be added as a sibling file without touching this one.

Standalone usage::

    from engine.maze import Maze
    from engine.ascii_display import render_ascii

    maze = Maze(5, 5)
    print(render_ascii(maze, entry=(0, 0), exit_=(4, 4)))
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from engine.maze import WALL_N, WALL_S, WALL_W, Maze

Coord = Tuple[int, int]

# ANSI colors selectable as the wall color (toggled during interaction).
RESET = "\033[0m"
WALL_COLORS: Dict[str, str] = {
    "none": "",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
}
SIGN_COLOR = "\033[1;33m"   # "42" sign (bold yellow)
PATH_COLOR = "\033[1;32m"   # solution path (bold green)


def _paint(text: str, color: str) -> str:
    """Wrap ``text`` in an ANSI color if ``color`` is non-empty."""
    return f"{color}{text}{RESET}" if color else text


def _body(cell: Coord, entry: Optional[Coord], exit_: Optional[Coord],
          path: Set[Coord], reserved: Set[Coord], color: bool) -> str:
    """Return the 3-character body shown at the center of a cell."""
    if cell in reserved:
        return _paint("###", SIGN_COLOR) if color else "###"
    if cell == entry:
        return " E "
    if cell == exit_:
        return " X "
    if cell in path:
        return _paint(" * ", PATH_COLOR) if color else " * "
    return "   "


def render_ascii(maze: Maze,
                 entry: Optional[Coord] = None,
                 exit_: Optional[Coord] = None,
                 path: Optional[Set[Coord]] = None,
                 reserved: Optional[Set[Coord]] = None,
                 show_path: bool = True,
                 wall_color: str = "") -> str:
    """Render the maze as an ASCII-art string.

    Walls are drawn with ``+``, ``-`` and ``|``; the entry as ``E``, the exit
    as ``X``, the solution path as ``*``, and the reserved cells of the "42"
    sign as ``#``. Passing an ANSI code from ``WALL_COLORS`` as ``wall_color``
    colors the walls (default is uncolored).

    Args:
        maze: The maze to render.
        entry: Entry coordinate.
        exit_: Exit coordinate.
        path: Set of cells on the solution path (shown when ``show_path``).
        reserved: Set of reserved cells of the "42" sign.
        show_path: Whether to show the path.
        wall_color: ANSI color code applied to walls (empty = uncolored).

    Returns:
        The rendered string, including newlines.
    """
    shown_path = path if (show_path and path is not None) else set()
    reserved = reserved if reserved is not None else set()
    color = bool(wall_color)
    w, h = maze.width, maze.height

    def hbar(x: int, y: int, bit: int) -> str:
        seg = "+" + ("---" if maze.has_wall(x, y, bit) else "   ")
        return _paint(seg, wall_color) if color else seg

    lines: List[str] = []
    for y in range(h):
        # North wall (top border line) of each cell.
        top = "".join(hbar(x, y, WALL_N) for x in range(w))
        top += _paint("+", wall_color) if color else "+"
        lines.append(top)
        # West wall + body of each cell.
        mid = ""
        for x in range(w):
            if maze.has_wall(x, y, WALL_W):
                mid += _paint("|", wall_color) if color else "|"
            else:
                mid += " "
            mid += _body((x, y), entry, exit_, shown_path, reserved, color)
        mid += _paint("|", wall_color) if color else "|"  # right outer border
        lines.append(mid)
    # South wall (bottom border line) of the last row.
    bottom = "".join(hbar(x, h - 1, WALL_S) for x in range(w))
    bottom += _paint("+", wall_color) if color else "+"
    lines.append(bottom)
    return "\n".join(lines)
