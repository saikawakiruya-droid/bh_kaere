*This project has been created as part of the 42 curriculum by naarai, ksadayas.*

# A-Maze-ing — This is the way

A custom maze generator. It takes a configuration file, generates a (optionally
perfect) maze, and writes it to a file as a hex wall representation. It also
provides ASCII rendering to the terminal and a dedicated validator that checks
whether the generated result satisfies the conditions.


---

## Description

- Reads a configuration file (`KEY=VALUE`) and generates a maze.
- At the center of the maze, a **"42"** drawn from several fully closed cells
  emerges.
- When `PERFECT=True`, there is exactly one path between entry and exit (a
  spanning tree).
- When `PERFECT=False` (the default), it produces a **playable Pac-Man board**
  (spec IV.4, v2.2): open four corners and centre, at least two independent
  loops, and only rare dead ends.
- After generation it automatically validates the conditions (connectivity,
  wall consistency, border, no 3x3 opening, shortest path, and — for
  `PERFECT=False` — the playable-board rules).
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
| `LICENSE.md` | MIT license permitting reuse of the `mazegen` module (spec VI) |
| `config.txt` / `Makefile` / `pyproject.toml` / `setup.cfg` / `README.md` | Config, build, docs |

**For testing (not submitted / graded. Spec III.3):**

- `test_*.py` under `tests/` … for behavior verification. Run with `make test`.
- `examples/` … sample outputs kept for development only. Every scenario they
  cover is reproduced by the "Usage examples" section below, so the directory
  itself is not part of the submission.

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

> Note: `make` targets use `python3` by default. To run with a different
> interpreter, override the `PYTHON` variable, e.g. `make run PYTHON=python3.11`.

> Note: `flake8` is configured with `max-line-length = 100` in `setup.cfg`
> (a deliberate relaxation of the default 79 to keep docstrings and type hints
> readable). `make lint` runs `flake8 .` and `mypy .` with the subject's flags.

### Validating the output file

```bash
python3 validator.py maze.txt
```

---

## Usage examples (verification checklist)

The `examples/` directory is not part of the submission, so every scenario can
be reproduced with the commands below. Each example lists **what to check**, so
it doubles as an evaluation checklist.

### 1. Standard perfect maze (default `config.txt`)

```bash
python3 a_maze_ing.py config.txt
```

- [ ] The ASCII rendering shows the **"42"** pattern near the centre, drawn
      from fully closed cells.
- [ ] Entry, exit, and the shortest path are visible in the rendering.
- [ ] `maze.txt` is written: hex grid (one row per line), one blank line, then
      3 lines (entry `x,y` / exit `x,y` / path of `N`/`E`/`S`/`W`), every line
      ending with `\n`.
- [ ] No `warning:` lines are printed (the built-in post-generation validation
      passed: connectivity, wall consistency, border walls, no 3x3 open area,
      exactly one path for `PERFECT=True`).
- [ ] `python3 validator.py maze.txt` prints `OK`.

### 2. Reproducibility via seed

```bash
python3 a_maze_ing.py config.txt   # SEED=42 in config.txt
mv maze.txt run1.txt
python3 a_maze_ing.py config.txt
diff maze.txt run1.txt             # no output = identical
```

- [ ] With the same `SEED`, two runs produce byte-identical output files.
- [ ] With the `SEED` line removed, runs produce different mazes.

### 3. Playable board (`PERFECT=False`)

```bash
printf 'WIDTH=25\nHEIGHT=20\nENTRY=0,0\nEXIT=24,19\nOUTPUT_FILE=maze.txt\nPERFECT=False\nSEED=42\n' > imperfect.txt
python3 a_maze_ing.py imperfect.txt
```

- [ ] No `warning:` lines are printed: the built-in playable-board validation
      passed (open four corners and centre, at least two independent loops, and
      only rare dead ends — spec IV.4, v2.2).
- [ ] The maze contains loops (`braiding.py`); toggling the path display shows
      alternative corridors, and `python3 validator.py maze.txt` reports `OK`.
- [ ] Full connectivity: no isolated cells besides the "42" pattern.

### 4. Sign relocation when entry/exit sit in the centre

```bash
printf 'WIDTH=20\nHEIGHT=15\nENTRY=10,7\nEXIT=19,14\nOUTPUT_FILE=maze.txt\nPERFECT=True\nSEED=1\n' > center.txt
python3 a_maze_ing.py center.txt
```

- [ ] The "42" is relocated so it does not overlap the entry; no omission
      warning is printed.

### 5. Maze too small for the sign (spec IV.4 fallback)

```bash
printf 'WIDTH=5\nHEIGHT=5\nENTRY=0,0\nEXIT=4,4\nOUTPUT_FILE=maze.txt\nPERFECT=True\nSEED=1\n' > tiny.txt
python3 a_maze_ing.py tiny.txt
```

- [ ] A console message states the sign is omitted (`warning (does not fit)`).
- [ ] The maze is still generated, validated, and written normally.

### 6. Error handling (never crashes, spec IV.2)

```bash
python3 a_maze_ing.py no_such_file.txt   # missing file
python3 a_maze_ing.py                    # missing argument -> usage
printf 'WIDTH=20\n' > broken.txt
python3 a_maze_ing.py broken.txt         # missing required keys
printf 'WIDTH=20\nHEIGHT=15\nENTRY=0,0\nEXIT=0,0\nOUTPUT_FILE=m.txt\nPERFECT=True\n' > same.txt
python3 a_maze_ing.py same.txt           # ENTRY == EXIT
```

- [ ] Each case prints a clear, cause-specific error message (no traceback)
      and exits with a non-zero code.

### 7. User interactions (spec V)

```bash
python3 a_maze_ing.py config.txt   # run in an interactive terminal
```

- [ ] Menu `1`/`2`: regenerate a new maze (auto-incremented or specified seed).
- [ ] Menu `3`: toggle the shortest-path display on/off.
- [ ] Menu `4`: cycle the wall color.
- [ ] Menu `5` (or EOF): quit cleanly.

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

### Playable board when `PERFECT=False` (spec IV.4, v2.2)

The default mode must be a board usable by a Pac-Man-like game, not just a maze
with a few loops. After the backtracker builds a spanning tree, `braiding.py`
reshapes it in three phases:

1. **Dead-end reduction** — each dead end opens one wall to connect elsewhere,
   so a chased player is rarely trapped.
2. **Corridor enforcement** — the four corners and the centre (kept free of the
   "42" sign by `initializer.py`) are given at least two openings, so the
   ghosts' corners and the player's central start are real corridors.
3. **Loop guarantee** — extra walls are opened until there are **at least two
   independent loops** (a perfect maze, or one with a single removed wall, is
   rejected).

Every wall removal is checked so it never creates a fully open 3x3 area, and
reserved "42" cells are never touched. Connectivity is preserved because walls
are only opened. Reaching **zero** dead ends is the subject's bonus; the
generator keeps them rare (typically a couple).

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
- When `PERFECT=False` (opt-in `playable` check): the four corners and centre
  are open corridors, there are at least two independent loops, and dead ends
  stay rare
- The attached shortest path is actually walkable and shortest

The main program runs this validation right after generation and warns on any
problem. It can be used both as a library (`validate()`, with a `playable`
flag) and as a CLI (`python3 validator.py <file>`). The CLI validates structure
only, because an output file does not record the intended mode; the subject's
`maze_analyzer.py` (not bundled here) can additionally classify a file as
perfect or playable.

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

The generator is also shipped as a self-contained, single-file `pip` package
(`mazegen.py`). Pre-built artifacts (`mazegen-1.0.0-py3-none-any.whl` and
`mazegen-1.0.0.tar.gz`) are at the repository root, and the package can be
rebuilt from source with `python -m build` (see `pyproject.toml`). It is
released under the MIT license (`LICENSE.md`), which explicitly allows reuse by
later 42 projects.

```python
from mazegen import MazeGenerator

gen = MazeGenerator(20, 15, seed=1, perfect=False).generate()
grid = gen.grid                       # 2D array of 4-bit wall codes
path = gen.solution((0, 0), (19, 14)) # shortest path "N/E/S/W"
```

---

## Team and project management

- **Members and roles:**
  - **naarai** — core & generation: `maze.py` (wall model, BFS/solve),
    `generator.py` (recursive backtracker), `braiding.py` (non-perfect board),
    and the `mazegen` reusable package.
  - **ksadayas** — I/O & verification: `config.py` / `options.py` / `errors.py`
    (config parsing), `writer.py`, `validator.py`, `display.py` (ASCII +
    interaction), tests, and docs.
  - _(Adjust the split above to match how the work was actually shared.)_
- **Plan and evolution:** Built incrementally in the order
  "solving → initialization (42) → generation → output → display → validation",
  committing each feature in small steps.
- **What went well:** Concentrating the wall representation in a single place
  (`maze.py`) avoided discrepancies between generation, display, output, and
  validation. Layering exceptions into fatal/non-fatal made errors easy to
  distinguish. The `PERFECT=False` mode meets the spec v2.2 playable-board
  rules (open four corners and centre, at least two independent loops, rare
  dead ends), enforced in `braiding.py` and confirmed by `validator.py`.
- **What could improve:** Dead ends are kept rare but not driven to zero, so
  the "no dead end at all" bonus is not yet reached. The subject's
  `maze_analyzer.py` is not bundled, so cross-checking with it is manual. Only
  the recursive backtracker is implemented (the `ALGORITHMS` registry is ready
  for Prim/Kruskal as a bonus), and the visual layer is ASCII-only — an MLX
  display remains an open task.

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
