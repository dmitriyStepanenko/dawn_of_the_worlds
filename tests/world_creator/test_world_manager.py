import pytest

from app.world_creator.model import LayerName
from app.world_creator.tiles import EmptyTile, Tile
from app.world_creator.world_manager import WorldManager


@pytest.mark.parametrize('percent', [0, 20, 40, 60, 80, 100])
def test_random_filling(world, percent):
    layer_name = LayerName.LANDS
    manager = WorldManager(world)
    manager.create_layer(layer_name=layer_name, shape=(10, 10))

    manager.random_partial_fill_layer(
        layer_name=layer_name,
        percent_filling=percent,
        filling_tile=Tile(position=0, image_ref=None)
    )

    assert len([t for t in manager.get_layer(layer_name).tiles if isinstance(t, EmptyTile)]) == 100 - percent
