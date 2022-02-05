from app.world_creator.tiles import Tile, EmptyTile
from app.world_creator.world_manager import Manager
from app.world_creator.model import LayerName, Layer, GodProfile
import pytest


@pytest.mark.parametrize('layer_name', LayerName)
@pytest.mark.parametrize('shape', [(1, 1), (4, 5), None])
def test_create_layer(world, layer_name, shape):
    count_layers = len(world.layers)
    manager = Manager(world)
    manager.create_layer(layer_name, shape)

    assert len(world.layers) == count_layers + 1
    assert world.layers.get(layer_name.value) is not None
    if shape:
        assert world.layers.get(layer_name.value).shape == shape
    else:
        assert world.layers.get(layer_name.value).shape == world.layers_shape


@pytest.mark.parametrize('layer_name', LayerName)
def test_get_layer(world, layer_name):
    manager = Manager(world)
    manager.create_layer(layer_name)
    layer = manager.get_layer(layer_name)

    assert layer == world.layers[layer_name.value]


def test_fill_layer(world):
    layer_name = LayerName.LANDS
    layer = Layer(layer_name=layer_name.value, shape=world.layers_shape)
    world.layers[layer.layer_name] = layer
    manager = Manager(world)

    start_count_tiles = len(layer.tiles)
    manager.fill_layer(layer_name, Tile(position=0))

    assert start_count_tiles == 0
    assert len(layer.tiles) > start_count_tiles
    assert len(layer.tiles) == layer.shape[0] * layer.shape[1]
    for tile in layer.tiles:
        assert isinstance(tile, Tile)


@pytest.mark.parametrize('percent', [0, 20, 40, 60, 80, 100])
def test_random_filling(world, percent):
    layer_name = LayerName.LANDS
    manager = Manager(world)
    manager.create_layer(layer_name=layer_name, shape=(10, 10))

    manager.random_partial_fill_layer(
        layer_name=layer_name,
        percent_filling=percent,
        filling_tile=Tile(position=0, image_ref=None)
    )

    assert len([t for t in manager.get_layer(layer_name).tiles if isinstance(t, EmptyTile)]) == 100 - percent


@pytest.mark.parametrize('value', [0, 10, 100, -4])
def test_spend_force(world, value):
    god_id = 0
    init_value_force = 0
    manager = Manager(world)
    world.gods[god_id] = GodProfile(name='test god', value_force=init_value_force)

    manager.spend_force(god_id, value)

    assert world.gods[god_id].value_force == init_value_force - value

