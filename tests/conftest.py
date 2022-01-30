import pytest
from app.world_creator.model import World


@pytest.fixture
def world() -> World:
    return World(
        name='test_world',
        layers_shape=(4, 5)
    )
