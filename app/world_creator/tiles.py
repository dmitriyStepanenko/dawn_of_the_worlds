from enum import Enum
from typing import Any, Union, Optional

from .base_model import BaseModel
from pydantic import Field


class Tile(BaseModel):
    position: int = Field(...)
    image_ref: Optional[str] = Field(None)
    creator: str = Field(None)
    name: str = Field(None)

    def __str__(self):
        return str(self.position)


class EmptyTile(Tile):
    def __str__(self):
        return 'empty'


class LandType(Enum):
    PLATEAU = 'PLATEAU'
    WATER = 'WATER'
    SAND = 'SAND'
    FOREST = 'FOREST'
    ROCK = 'ROCK'


class ClimateType(Enum):
    CLOUD = 'CLOUD'
    SNOW = 'SNOW'
    RAIN = 'RAIN'
    CLEAR = 'CLEAR'


class ImageRef(Enum):
    RACE_INIT_POSITION = 'race_init_position'
    CITY = 'city'
    EVENT = 'event'


TILES = Union[
    Tile,
]
