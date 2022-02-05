import pytest

from app.world_creator.utils import get_coord_from_position, get_position_from_coord


@pytest.mark.parametrize(
    'position, len_row, true_coord',
    [(0, 1, (0, 0)), (0, 10, (0, 0)), (2, 1, (2, 0)), (5, 3, (1, 2))]
)
def test_get_coord(position, len_row, true_coord):
    coord = get_coord_from_position(position, len_row)

    assert coord == true_coord


@pytest.mark.parametrize(
    'x, y, len_row, true_position',
    [(0, 0, 0, 0), (0, 0, 1, 0), (3, 0, 4, 3), (1, 3, 3, 10)]
)
def test_get_position(x, y, len_row, true_position):
    position = get_position_from_coord(x, y, len_row)

    assert position == true_position
