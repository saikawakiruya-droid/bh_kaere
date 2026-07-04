*This project has been created as part of the 42 curriculum by &lt;login&gt;.*

# A-Maze-ing — This is the way

A custom maze generator. It takes a configuration file, generates a (optionally
perfect) maze, and writes it to a file as a hex wall representation. It also
provides ASCII rendering to the terminal and a dedicated validator that checks
whether the generated result satisfies the conditions.

> ⚠️ Replace `<login>` on line 1 with your own 42 login before submission.

---

## Description

- Reads a configuration file (`KEY=VALUE`) and generates a maze.
- At the center of the maze, a **"42"** drawn from several fully closed cells
  emerges.
- When `PERFECT=True`, there is exactly one path between entry and exit (a
  spanning tree).
- After generation it automatically validates the conditions (connectivity,
  wall consistency, border, no 3x3 opening, shortest path, etc.).
- The output file uses the spec's hex format and can be checked with the
  bundled validator or the Moulinette.

---

## File layout (submitted code vs. tests)

**Submitted / graded (repository root):**

| File | Role |
|------|------|
| `a_maze_ing.py` | Main program (entry point) |
| `maze.py` | Core (wall representation, open/close, BFS distances, shortest path) |
| `initializer.py` | Initial map generation and "42" sign placement |
| `generator.py` | Generation algorithm and selection registry |
| `braiding.py` | Imperfect-maze conversion (`PERFECT=False`) |
| `display.py` | ASCII rendering and display-mode registry |
| `config.py` / `options.py` | Required-key validation / optional-key handling |
| `errors.py` | Exception hierarchy |
| `writer.py` | Output-file writing (hex format) |
| `validator.py` | Post-generation condition checks (library + CLI) |
| `mazegen.py` | Reusable module (single file) |
| `mazegen-1.0.0-*.whl` / `.tar.gz` | Pre-built packages |
| `config.txt` / `Makefile` / `pyproject.toml` / `setup.cfg` / `README.md` | Config, build, docs |
| `examples/` | Sample outputs of initialization maps / generated results |

**For testing (not submitted / graded. Spec III.3):**

- `test_*.py` under `tests/` … for behavior verification. Run with `make test`.

> Because the tests are separated into `tests/`, they are clearly distinct from
> the submitted code (the `*.py` at the root). The tests are solely for
> verifying the project's behavior.

---

## Instructions (install / run)

### Dependencies

No external libraries are required to run (standard library only). For
development, `flake8` / `mypy` / `pytest` are used.

### Setup and run

```bash
# Install dev tools (grading environment)
make install

# Generate and display a maze (using the default config.txt)
make run

# Specify a different config file
make run CONFIG=my_config.txt

# Debug run (pdb)
make debug

# Tests
make test

# Static checks (flake8 + mypy)
make lint
```

To run directly:

```bash
python3 a_maze_ing.py config.txt
```

> Note: In this repository's development environment the system `python` was
> broken, so a virtual environment is created with `uv`. To run locally, after
> `uv venv .venv && uv pip install --python .venv flake8 mypy pytest`, you can
> override Python like `make run PYTHON=.venv/Scripts/python.exe` (Windows).

### Validating the output file

```bash
python3 validator.py maze.txt
```

---

## Configuration file structure and format

One `KEY=VALUE` per line. Lines starting with `#` and blank lines are ignored.

### Required keys

| Key | Description | Example |
|------|------|-----|
| `WIDTH` | Maze width (cells, 1 or more) | `WIDTH=25` |
| `HEIGHT` | Maze height (cells, 1 or more) | `HEIGHT=20` |
| `ENTRY` | Entry coordinate `x,y` | `ENTRY=0,0` |
| `EXIT` | Exit coordinate `x,y` (different from entry) | `EXIT=24,19` |
| `OUTPUT_FILE` | Output file name | `OUTPUT_FILE=maze.txt` |
| `PERFECT` | Whether to make a perfect maze (`True`/`False`) | `PERFECT=True` |

### Optional keys (handled by `options.py`)

| Key | Description | Default |
|------|------|--------|
| `SEED` | Random seed (reproducibility) | none (random each run) |
| `ALGORITHM` | Generation algorithm name | `backtracker` |
| `DISPLAY` | Display-mode name | `ascii` |
| `SIGN` | String to embed | `42` |

Invalid values become errors distinguished per cause (`ConfigParseError` /
`ConfigKeyError` / `ConfigValueError`), print a clear message, and exit.

---

## Output file format (spec IV.5)

- Each cell is a single upper-case hex digit. Closed walls are encoded as bits:
  `bit0=north, bit1=east, bit2=south, bit3=west` (1 if closed).
- One line of cells per row.
- One blank line, then 3 lines: entry `x,y` / exit `x,y` / shortest path
  (concatenation of `N`/`E`/`S`/`W`).
- Every line ends with `\n`.

---

## Algorithms used and rationale

### Generation: recursive backtracker (iterative)

Starting from every cell closed by walls, it carves randomly depth-first and
backtracks the stack at dead ends. Because it connects all cells into a single
tree (a **spanning tree**), it naturally satisfies `PERFECT=True` (exactly one
path between any two points).

**Rationale:**

- Guarantees a perfect maze (DFS tree = spanning tree).
- Simple to implement, concentrated on a single random source
  (`random.Random(seed)`) for strong reproducibility.
- Implemented iteratively with an explicit stack, so even large mazes do not
  hit Python's recursion limit.
- By simply not carving the "42" reserved cells, the sign remains within the
  passages.

The algorithm can be selected with the `ALGORITHM` key (currently only
`backtracker`); the design lets you register e.g. Prim's or Kruskal's algorithm
in `ALGORITHMS` of `generator.py` and select it directly.

### Solving: BFS (breadth-first search)

It computes the shortest distance from the entry and the exit to each cell, and
obtains the shortest path (and all cells on it). Because it is BFS, it
guarantees shortest paths even for imperfect mazes.

---

## Post-generation validation (`validator.py`)

The dedicated validator confirms that the generated maze satisfies the spec
IV.4 conditions:

- Entry and exit are in bounds and differ from each other
- Outward walls of border cells are closed
- Adjacent cells share their walls consistently
- Every cell except the "42" (`0xF` closed cells) is connected
- No fully open 3x3 area (passages are at most 2 cells wide)
- When `PERFECT`, exactly one path (no cycles)
- The attached shortest path is actually walkable and shortest

The main program runs this validation right after generation and warns on any
problem. It can be used both as a library (`validate()`) and as a CLI
(`python3 validator.py <file>`).

---

## Reusable code and usage

Maze generation, solving, and wall representation can be reused as modules.

```python
import random
from maze import Maze, solve, solution_cells
from generator import generate_backtracker
from initializer import reserved_cells

# Reserve the "42" cells and generate the maze
reserved = reserved_cells(25, 20)
maze = generate_backtracker(25, 20, reserved, random.Random(42), start=(0, 0))

# Get the solution (shortest path)
path = solve(maze, (0, 0), (24, 19))          # e.g. "EESS..."
cells = solution_cells(maze, (0, 0), (24, 19)) # set of cells on the path

# Access wall codes (bit0=N,1=E,2=S,3=W, closed=1)
code = maze.cells[0][0]
```

Main modules:

- `maze.py` — wall representation (`Maze`), `open_wall`, `bfs_distances`, `solve`, `solution_cells`
- `initializer.py` — initial map generation and "42" sign placement
- `generator.py` — generation algorithm and selection registry
- `display.py` — ASCII rendering and display-mode registry
- `validator.py` — condition checks

> Packaging as a single-file `pip` package (`mazegen-*`) is future work.

---

## Team and project management

- **Members and roles:** (fill in)
- **Plan and evolution:** Built incrementally in the order
  "solving → initialization (42) → generation → output → display → validation",
  committing each feature in small steps.
- **What went well:** Concentrating the wall representation in a single place
  (`maze.py`) avoided discrepancies between generation, display, output, and
  validation. Layering exceptions into fatal/non-fatal made errors easy to
  distinguish.
- **What could improve:** `PERFECT=False` braiding, post-processing for 2-cell
  passage width, MLX display, and packaging remain as open tasks.

---

## Resources (references / AI usage)

- General explanations of maze generation algorithms (recursive backtracker /
  Prim / Kruskal)
- The correspondence between spanning trees in graph theory and perfect mazes
- The exact shape of the "42" sign was taken from the figure in the assignment
  PDF (`a_maze_ing.pdf`)

**AI usage:** AI was used for design brainstorming, implementing each module
with docstrings and type annotations, writing tests, extracting the "42" shape
from the PDF (image analysis), and polishing the README.
