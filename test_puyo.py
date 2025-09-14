import pytest

pygame = pytest.importorskip('pygame')

import puyo


def test_apply_gravity():
    board = [[None for _ in range(puyo.COLUMNS)] for _ in range(puyo.ROWS)]
    board[2][0] = puyo.PUYO_COLORS[0]
    board[0][0] = puyo.PUYO_COLORS[1]
    puyo.FieldUtils.apply_gravity(board, puyo.COLUMNS, puyo.ROWS)
    assert board[-1][0] == puyo.PUYO_COLORS[0]
    assert board[0][0] == puyo.PUYO_COLORS[1]


def test_find_4plus_groups():
    puyo.reset_game()
    color = puyo.PUYO_COLORS[0]
    puyo.field[2][0] = color
    puyo.field[2][1] = color
    puyo.field[3][0] = color
    puyo.field[3][1] = color
    groups = puyo.find_4plus_groups()
    assert any(len(g) == 4 for g in groups)
