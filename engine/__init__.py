"""The maze engine: build, validate, and output a maze — usable in parts.

Each stage lives in its own module and can be imported on its own (see that
module's docstring for a copy-pasteable example): :mod:`engine.maze` (core data
structure), :mod:`engine.build` (sign reservation, generation, braiding),
:mod:`engine.validator` (spec IV.4 condition checks), and :mod:`engine.output`
(file writing and terminal display).

Basic usage (the full pipeline, PERFECT=False)::

    import random
    from engine import (
        initialize_maze, generate_backtracker, braid, solve, validate,
        write_maze, render_ascii,
    )

    rng = random.Random(42)
    entry, exit_ = (0, 0), (19, 14)
    _, reserved = initialize_maze(20, 15, entry=entry, exit_=exit_)
    maze = generate_backtracker(20, 15, reserved, rng, start=entry)
    braid(maze, reserved, rng, min_loops=2)

    solution = solve(maze, entry, exit_)
    problems = validate(maze, entry, exit_, reserved=reserved,
                        solution=solution, playable=True)

    write_maze("maze.txt", maze, entry, exit_, solution)
    print(render_ascii(maze, entry=entry, exit_=exit_))
"""

from __future__ import annotations

import importlib
from typing import Any, Dict

# name -> the submodule that defines it. Resolved lazily by __getattr__
# (PEP 562) instead of importing every submodule eagerly at package-import
# time: eager imports here would make each submodule already present in
# ``sys.modules`` under ``engine.*``, which triggers a RuntimeWarning when a
# submodule with its own CLI (e.g. ``engine.validator``) is run directly with
# ``python -m engine.validator``.
_SUBMODULE_OF: Dict[str, str] = {
    "GLYPHS": "engine.build",
    "algorithm_names": "engine.build",
    "braid": "engine.build",
    "count_dead_ends": "engine.build",
    "count_loops": "engine.build",
    "generate_backtracker": "engine.build",
    "get_algorithm": "engine.build",
    "initialize_maze": "engine.build",
    "reserved_cells": "engine.build",
    "sign_bitmap": "engine.build",
    "ConfigError": "engine.errors",
    "ConfigKeyError": "engine.errors",
    "ConfigParseError": "engine.errors",
    "ConfigValueError": "engine.errors",
    "MazeError": "engine.errors",
    "SignError": "engine.errors",
    "SignOverlapError": "engine.errors",
    "SignTooBigError": "engine.errors",
    "DIRECTIONS": "engine.maze",
    "Maze": "engine.maze",
    "bfs_distances": "engine.maze",
    "path_to_cells": "engine.maze",
    "solution_cells": "engine.maze",
    "solve": "engine.maze",
    "WALL_COLORS": "engine.output",
    "display_names": "engine.output",
    "format_maze": "engine.output",
    "get_display_mode": "engine.output",
    "render_ascii": "engine.output",
    "write_maze": "engine.output",
    "validate": "engine.validator",
}

__all__ = sorted(_SUBMODULE_OF)


def __getattr__(name: str) -> Any:
    """Lazily resolve a re-exported name from its submodule (PEP 562)."""
    try:
        module_name = _SUBMODULE_OF[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module_name), name)
