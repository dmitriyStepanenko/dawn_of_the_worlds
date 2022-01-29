from enum import Enum
from typing import Any, Union

from .base_model import BaseModel
from pydantic import Field


class Tile(BaseModel):
    x_pos: int = Field(...)
    y_pos: int = Field(...)
    image_ref: str = Field(None)
    creator: str = Field(None)
    # TODO: name
    name: str = Field(None)

    @property
    def position(self):
        return self.x_pos, self.y_pos

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


class TerrainTile(Tile):
    type_land: LandType = Field(...)

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.image_ref = self.type_land.value

    def __str__(self):
        return self.type_land.value


class ClimateType(Enum):
    CLOUD = 'CLOUD'
    SNOW = 'SNOW'
    FOG = 'FOG'
    RAIN = 'RAIN'
    CLEAR = 'CLEAR'


class InitPositionRaceTile(Tile):
    def __init__(self, x_pos: int, y_pos: int):
        super(InitPositionRaceTile, self).__init__(x_pos=x_pos, y_pos=y_pos, image_ref=self.__class__.__name__)


TILES = Union[
    Tile,
    TerrainTile,
    InitPositionRaceTile,
]
