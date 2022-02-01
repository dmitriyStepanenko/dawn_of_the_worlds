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
    # FOG = 'FOG'
    RAIN = 'RAIN'
    CLEAR = 'CLEAR'


class InitPositionRaceTile(Tile):
    def __init__(self, **data: Any):
        super(InitPositionRaceTile, self).__init__(**data)
        self.image_ref = self.__class__.__name__


class EventTile(Tile):
    def __init__(self, **data: Any):
        super().__init__(**data)
        self.image_ref = self.__class__.__name__


TILES = Union[
    Tile,
    InitPositionRaceTile,
    EventTile,
]
