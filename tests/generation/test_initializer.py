# [TEST FILE] 提出・採点対象外（仕様 III.3）— 動作確認専用。実行: make test / pytest
"""Unit tests for the initializer module (initial map + "42" sign)."""

from __future__ import annotations

import pytest

from core.errors import SignOverlapError, SignTooBigError
from generation.initializer import (
    GLYPH_HEIGHT,
    initialize_maze,
    reserved_cells,
    sign_bitmap,
)


def test_bitmap_dimensions() -> None:
    bitmap = sign_bitmap("42")
    assert len(bitmap) == GLYPH_HEIGHT
    # 3 + gap(1) + 3 = 7
    assert all(len(row) == 7 for row in bitmap)


def test_bitmap_gap() -> None:
    # Gap 1 (default) is width 7, gap 2 is width 8. Height is always fixed.
    assert all(len(r) == 7 for r in sign_bitmap("42", gap=1))
    assert all(len(r) == 8 for r in sign_bitmap("42", gap=2))


def test_gap_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        sign_bitmap("42", gap=3)


def test_unknown_glyph_raises() -> None:
    with pytest.raises(KeyError):
        sign_bitmap("9")


def test_reserved_cells_centered_and_in_bounds() -> None:
    w, h = 20, 15
    cells = reserved_cells(w, h)
    assert len(cells) > 0
    assert all(0 <= x < w and 0 <= y < h for x, y in cells)


def test_reserved_cell_count_matches_ones() -> None:
    bitmap = sign_bitmap("42")
    ones = sum(row.count("1") for row in bitmap)
    assert len(reserved_cells(20, 15)) == ones


def test_too_small_raises() -> None:
    with pytest.raises(SignTooBigError):
        reserved_cells(6, 6)


def test_overlap_relocates_when_room() -> None:
    # Even if a centered cell is passed in avoid, it relocates to a
    # non-overlapping position when there is room (does not error).
    centered = reserved_cells(20, 15)
    a_sign_cell = next(iter(centered))
    moved = reserved_cells(20, 15, avoid={a_sign_cell})
    assert len(moved) == len(centered)
    assert a_sign_cell not in moved


def test_cannot_place_when_not_generatable() -> None:
    # The frame (7x7) fits, but the "2" notch gets trapped at the right edge
    # and no generatable placement exists, so SignOverlapError is raised.
    with pytest.raises(SignOverlapError):
        reserved_cells(7, 7)


def test_smallest_generatable_is_8x6() -> None:
    # The minimum size 8x6 is placeable. All free cells stay connected.
    cells = reserved_cells(8, 6)
    assert len(cells) > 0
    free = {(x, y) for y in range(6) for x in range(8) if (x, y) not in cells}
    # The free cells are connected (guaranteeing generatability).
    start = next(iter(free))
    seen, stack = {start}, [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in free and n not in seen:
                seen.add(n)
                stack.append(n)
    assert seen == free


def test_endpoints_decide_sign_at_same_size() -> None:
    # Even at the same size 8x7, the entry/exit coords decide placeable or not.
    placed = reserved_cells(8, 7, avoid={(0, 6), (7, 0)})
    assert len(placed) > 0
    # (0,1) is a cell common to every valid placement -> nowhere to put it,
    # so it is omitted.
    with pytest.raises(SignOverlapError):
        reserved_cells(8, 7, avoid={(0, 1), (7, 6)})


def test_no_overlap_when_endpoints_far() -> None:
    # Corners do not overlap the centered sign.
    cells = reserved_cells(20, 15, avoid={(0, 0), (19, 14)})
    assert (0, 0) not in cells and (19, 14) not in cells


def test_too_small_and_overlap_are_distinct() -> None:
    # The two sign errors are distinguishable as separate classes.
    assert not issubclass(SignTooBigError, SignOverlapError)
    assert not issubclass(SignOverlapError, SignTooBigError)


def test_default_gap_is_one() -> None:
    # Auto-selection uses gap 1 by default (width 7).
    cells = reserved_cells(20, 15)
    xs = {x for x, _ in cells}
    assert max(xs) - min(xs) + 1 == 7  # 3+1+3 = 7


def test_explicit_gap_too_wide_rejected() -> None:
    with pytest.raises(ValueError):
        reserved_cells(20, 15, gap=3)  # 3+ is too far apart


def test_explicit_gap_two_allowed() -> None:
    cells = reserved_cells(20, 15, gap=2)
    xs = {x for x, _ in cells}
    assert max(xs) - min(xs) + 1 == 8  # 3+2+3 = 8


def test_frame_too_small_raises_toobig() -> None:
    # Width 6 does not fit the frame at any gap -> SignTooBigError.
    with pytest.raises(SignTooBigError):
        reserved_cells(6, 15)
    # Height 4 also does not fit the frame.
    with pytest.raises(SignTooBigError):
        reserved_cells(20, 4)


def test_initialize_maze_all_closed_and_reserved() -> None:
    maze, reserved = initialize_maze(20, 15, entry=(0, 0), exit_=(19, 14))
    # Every cell is initialized walled on all four sides (0xF).
    assert all(cell == 0xF for row in maze.cells for cell in row)
    assert len(reserved) > 0


def test_initialize_maze_omits_sign_when_frame_too_small(
        capsys: pytest.CaptureFixture[str]) -> None:
    maze, reserved = initialize_maze(6, 6, entry=(0, 0), exit_=(5, 5))
    assert reserved == set()
    assert "does not fit" in capsys.readouterr().out


def test_initialize_maze_relocates_sign_on_overlap() -> None:
    # Even with the entry near the center, it relocates to a non-overlapping
    # position when there is room.
    maze, reserved = initialize_maze(20, 15, entry=(10, 7), exit_=(0, 0))
    assert len(reserved) > 0
    assert (10, 7) not in reserved
    assert (0, 0) not in reserved


def test_initialize_maze_omits_sign_when_not_generatable(
        capsys: pytest.CaptureFixture[str]) -> None:
    # 7x7 fits the frame but has no generatable placement, so it is omitted.
    maze, reserved = initialize_maze(7, 7, entry=(0, 0), exit_=(6, 6))
    assert reserved == set()
    assert "cannot place" in capsys.readouterr().out
