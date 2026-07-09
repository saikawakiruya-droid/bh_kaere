"""Selection registry for maze generation algorithms.

Currently the only choice is the **recursive backtracker**
(:func:`generation.backtracker.generate_backtracker`), but a mechanism to select
one via the ``ALGORITHM`` config key is provided from the start (to add more
algorithms as a bonus, just register them in ``ALGORITHMS``).

Every generator function shares the same signature ``(width, height,
reserved, rng, start) -> Maze``. ``reserved`` is the set of cells kept closed
for the "42" sign, and generation never carves them.

Standalone usage::

    from generation.generator import get_algorithm

    generate = get_algorithm("backtracker")
    maze = generate(20, 15, reserved=set(), rng=random.Random(42))
"""

from __future__ import annotations

from typing import Dict, List

from core.errors import ConfigValueError
from generation.backtracker import GeneratorFn, generate_backtracker

ALGORITHMS: Dict[str, GeneratorFn] = {
    "backtracker": generate_backtracker,
}


def algorithm_names() -> List[str]:
    """Return the available algorithm names in ascending order."""
    return sorted(ALGORITHMS)


def get_algorithm(name: str) -> GeneratorFn:
    """Look up a generator function by name.

    Args:
        name: Algorithm name (the ``ALGORITHM`` config value).

    Returns:
        The corresponding generator function.

    Raises:
        ConfigValueError: If the algorithm name is unknown.
    """
    try:
        return ALGORITHMS[name]
    except KeyError:
        raise ConfigValueError(
            f"unknown algorithm '{name}'. choices: {algorithm_names()}"
        )
