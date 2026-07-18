"""A-Maze-ing — the main program of the maze generator.

Usage::

    python a_maze_ing.py config.txt

Reads a config file, generates a (optionally perfect) maze, and writes it to a
file in the spec IV.5 hex format. After generation it confirms the conditions
with :mod:`verification.verifier`, and finally renders the maze to the terminal.

It handles all errors gracefully and never crashes unexpectedly. On any
problem it prints a clear message and returns an exit code.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Set, Tuple

import mazegen
from core.errors import MazeError
from core.maze import ALL_WALLS, Maze, path_to_cells, solve
from output.ascii_display import WALL_COLORS
from output.display import get_display_mode
from output.writer import write_maze
from validation.config import Config, parse_config
from verification.verifier import validate

Coord = Tuple[int, int]


# Minimum independent loops required for a playable board (spec IV.4, v2.2).
PLAYABLE_MIN_LOOPS = 2


def build_maze(config: Config) -> Tuple[Maze, Set[Coord]]:
    """Build the maze by delegating generation to :mod:`mazegen`.

    Assembles a spec dict from the config and passes it to
    :func:`mazegen.generate_mazes`, which carves the maze, embeds the "42"
    sign, and — when ``PERFECT=False`` — braids it into a playable Pac-Man
    board. The returned wall grid is wrapped back into a :class:`~core.maze.Maze`
    for evaluation and output, and the reserved ("42") cells are recovered as
    the fully closed cells of that grid.

    Args:
        config: The validated configuration.

    Returns:
        ``(maze, reserved)``, where ``reserved`` is the "42" reserved-cell set.
    """
    spec: Dict[str, Any] = {
        "width": config.width,
        "height": config.height,
        "perfect": config.perfect,
        "seed": config.options.seed,
        "entry": config.entry,
        "exit": config.exit,
        "sign": config.options.sign,
        "min_loops": PLAYABLE_MIN_LOOPS,
    }
    grid = mazegen.generate_mazes([spec])[0]
    maze = Maze(config.width, config.height, cells=grid)
    reserved = {(x, y)
                for y in range(config.height)
                for x in range(config.width)
                if grid[y][x] == ALL_WALLS}
    return maze, reserved


def interact(config: Config, maze: Maze, reserved: Set[Coord]) -> None:
    """Simple terminal interaction (spec V).

    - 1: regenerate a new maze and display it (seed auto +1)
    - 2: regenerate with a specified seed value
    - 3: toggle the shortest-path display
    - 4: change the wall color
    - 5: quit

    Args:
        config: The configuration (used while varying the seed on regenerate).
        maze: The current maze.
        reserved: The "42" reserved-cell set.
    """
    render = get_display_mode(config.options.display)
    color_names = list(WALL_COLORS)
    color_idx = 0
    show_path = True
    seed = config.options.seed if config.options.seed is not None else 0

    def show() -> None:
        sol = solve(maze, config.entry, config.exit)
        path_cells = (path_to_cells(config.entry, sol)
                      if sol is not None else set())
        print(render(maze, entry=config.entry, exit_=config.exit,
                     path=path_cells, reserved=reserved,
                     show_path=show_path,
                     wall_color=WALL_COLORS[color_names[color_idx]]))

    def regenerate() -> None:
        nonlocal maze, reserved
        try:
            maze, reserved = build_maze(config)
        except MazeError as err:
            print(f"regeneration error: {err}", file=sys.stderr)
            return
        show()

    while True:
        print("\n=== A-Maze-ing ===")
        print(f"1. Regenerate a new maze (next seed: {seed + 1})")
        print("2. Regenerate with a specified seed")
        print("3. Toggle the shortest-path display")
        print(f"4. Change the wall color (current: {color_names[color_idx]})")
        print(f"5. Quit (current seed: {seed})")
        try:
            choice = input("choice (1-5): ").strip()
        except EOFError:
            return

        if choice == "1":
            seed += 1
            config.options.seed = seed
            regenerate()
        elif choice == "2":
            try:
                raw = input("seed value (integer): ").strip()
            except EOFError:
                return
            try:
                seed = int(raw)
            except ValueError:
                print("Please enter an integer.")
                continue
            config.options.seed = seed
            regenerate()
        elif choice == "3":
            show_path = not show_path
            show()
        elif choice == "4":
            color_idx = (color_idx + 1) % len(color_names)
            show()
        elif choice == "5":
            return
        else:
            print("Please enter 1-5.")


def run(config_path: str) -> int:
    """Process the config file: generate, validate, write, and display the maze.

    Args:
        config_path: Path to the config file.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    try:
        config = parse_config(config_path)
    except MazeError as err:
        print(f"config error: {err}", file=sys.stderr)
        return 1

    try:
        maze, reserved = build_maze(config)
    except MazeError as err:
        print(f"generation error: {err}", file=sys.stderr)
        return 1

    solution = solve(maze, config.entry, config.exit)

    # Confirm post-generation that the conditions hold (spec IV.4). For
    # PERFECT=False, also check the playable Pac-Man board rules.
    problems = validate(maze, config.entry, config.exit,
                        reserved=reserved, perfect=config.perfect,
                        solution=solution, playable=not config.perfect)
    if problems:
        print(f"warning: the generated maze fails {len(problems)} condition(s):",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)

    try:
        write_maze(config.output_file, maze, config.entry, config.exit,
                   solution)
    except MazeError as err:
        print(f"output error: {err}", file=sys.stderr)
        return 1
    print(f"wrote output file: {config.output_file}")

    # Highlight exactly one shortest path (spec V), not every shortest-path
    # cell, so a board with loops does not show several overlaid paths.
    path_cells = (path_to_cells(config.entry, solution)
                  if solution is not None else set())
    render = get_display_mode(config.options.display)
    print(render(maze, entry=config.entry, exit_=config.exit,
                 path=path_cells, reserved=reserved, show_path=True))

    # Offer interaction only when running interactively in a terminal
    # (skip for pipes and other non-interactive runs so we do not hang).
    if sys.stdin.isatty() and sys.stdout.isatty():
        interact(config, maze, reserved)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python a_maze_ing.py <config_file>", file=sys.stderr)
        return 2
    try:
        return run(args[0])
    except Exception as err:  # never crash, even on the unexpected.
        print(f"unexpected error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
