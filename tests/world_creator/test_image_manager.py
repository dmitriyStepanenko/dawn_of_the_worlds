import pytest
from PIL import Image

from app.world_creator.image_manager import (
    ImageCollection,
    load_event_tiles,
    load_land_tiles,
    load_race_init_tiles,
    load_climate_tiles,
)


@pytest.mark.parametrize('size', [(10, 10), (1, 1)])
def test_image_collection_invalid(size):
    images = {
        'aaa': Image.new('RGBA', (10, 10)),
        'bbb': Image.new('RGBA', (10, 8))
    }
    with pytest.raises(ValueError, match='Все изображения в коллекции должны быть одного размера'):
        ImageCollection(images, image_size=size)


@pytest.mark.parametrize('load_function', [
    load_race_init_tiles,
    load_event_tiles,
    load_climate_tiles,
    load_land_tiles,
])
def test_work_load_functions(load_function):
    """К сожалению тут можно только проверить, что картинки успешно загрузились"""
    load_function()
