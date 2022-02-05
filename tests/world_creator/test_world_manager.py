import pytest

from app.world_creator.model import LayerName
from app.world_creator.tiles import LandType
from app.world_creator.world_manager import WorldManager


def test_add_init_layers(world):
    manager = WorldManager(world)
    manager.add_init_layers()

    for layer_name in LayerName:
        assert manager.get_layer(layer_name)


@pytest.mark.parametrize('percent', [0, 50, 100])
def test_fill_base_lands(world, percent):
    manager = WorldManager(world)
    manager.create_layer(layer_name=LayerName.LANDS, shape=(10, 10))
    layer = manager.get_layer(LayerName.LANDS)

    manager.fill_base_lands_layer(percent)

    assert len([t for t in layer.tiles if t.image_ref == LandType.WATER.value]) == 100 - percent
    assert len([t for t in layer.tiles if t.image_ref == LandType.PLATEAU.value]) == percent
