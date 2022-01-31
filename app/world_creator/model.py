import enum
from enum import Enum

from typing import Any, Optional

from pydantic import Field

from .base_model import BaseModel
from .tiles import TILES
from .utils import get_position_from_coord

MAX_SIZE_LAYER = 10
DEFAULT_LAYER_SHAPE = (3, 3)


class Action(BaseModel):
    name: str = Field(...)
    costs: list[int] = Field(...)


class Actions(Enum):
    CREATE_LAND = Action(name='CREATE_LAND', costs=[3, 5, 8])
    CREATE_CLIMATE = Action(name='CREATE_CLIMATE', costs=[2, 4, 6])
    CREATE_RACE = Action(name='CREATE_RACE', costs=[22, 6, 15])
    CREATE_SUBRACE = Action(name='CREATE_SUBRACE', costs=[12, 4, 10])
    CONTROL_RACE = Action(name='CONTROL_RACE', costs=[8, 4, 3])
    CONTROL_CITY = Action(name='CONTROL_CITY', costs=[6, 4, 2])
    DEVELOP_REALM = Action(name='DEVELOP_REALM', costs=[10, 5, 6])
    DEVELOP_CITY = Action(name='DEVELOP_CITY', costs=[8, 4, 5])
    INCREASE_REALM_ALIGNMENT = Action(name='INCREASE_REALM_ALIGNMENT', costs=[5, 3, 4])
    DECREASE_REALM_ALIGNMENT = Action(name='DECREASE_REALM_ALIGNMENT', costs=[4, 3, 3])
    INCREASE_CITY_ALIGNMENT = Action(name='INCREASE_CITY_ALIGNMENT', costs=[4, 3, 3])
    DECREASE_CITY_ALIGNMENT = Action(name='DECREASE_CITY_ALIGNMENT', costs=[3, 2, 2])
    EVENT = Action(name='EVENT', costs=[10, 7, 9])
    CREATE_ORDER = Action(name='CREATE_ORDER', costs=[8, 6, 4])
    CONTROL_ORDER = Action(name='CONTROL_ORDER', costs=[4, 3, 2])
    CREATE_AVATAR = Action(name='CREATE_AVATAR', costs=[10, 7, 8])
    # CONTROL_AVATAR = Action(name='CONTROL_AVATAR', costs=[2, 1, 1])
    CATASTROPHE = Action(name='CATASTROPHE', costs=[10, 10, 10])


class GodProfile(BaseModel):
    name: str = Field(...)
    avatar_picture: str = Field('')

    value_force: int = Field(0)
    bonus_force: int = Field(0)

    confirm_end_round: bool = Field(False)
    confirm_end_era: bool = Field(False)

    def __str__(self):
        return self.name

    @property
    def info(self):
        return f'\n' \
               f'Бог: {self.name}\n' \
               f'Изображение: {self.avatar_picture}\n' \
               f'Божественная сила: {self.value_force}\n' \
               f'Бонус божественной силы: {self.bonus_force}\n' \
               f'{"Завершил раунд" if self.confirm_end_round else ""}\n' \
               f'{"Хочет завершить эпоху" if self.confirm_end_era else ""}\n'


class Avatar(BaseModel):
    god_owner: GodProfile = Field(...)
    name: str = Field(...)


class RaceFraction(BaseModel):
    god_owner: GodProfile = Field(...)
    name: str = Field(...)


class Race(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    init_position: int = Field(...)
    avatars: dict[str, Avatar] = Field({})
    god_creator: str = Field(...)
    fractions: dict[str, RaceFraction] = Field({})
    alignment: int = Field(0)
    parent_name: Optional[str] = Field(None)
    technologies: list[str] = Field([])


class Layer(BaseModel):
    layer_name: str = Field(...)
    shape: tuple[int, int] = Field(...)
    tiles: list[TILES] = Field([])

    @property
    def num_tiles(self):
        return self.shape[0] * self.shape[1]

    def __str__(self):
        out_str = ''
        for i in range(self.shape[0]):
            for j in range(self.shape[1]):
                out_str += str(self.tiles[get_position_from_coord(i, j, self.shape[0])]) + ' '
            out_str += '\n'
        return out_str


class LayerName(Enum):
    LANDS = 'lands'
    CLIMATE = 'climate'
    RACE = 'race'


class World(BaseModel):
    name: str = Field(...)
    layers: dict[str, Layer] = Field({})
    layers_shape: tuple[int, int] = Field(...)
    change_log: list[str] = Field([])

    gods: dict[int, GodProfile] = Field({}, description='Профайлы богов по id их владельцев')
    races: dict[str, Race] = Field({})

    redactor_god_id: Optional[int] = Field(None, description='id бога которому разрешено сейчас действовать')
    current_message_with_buttons_id: Optional[int] = Field(None)

    n_era: int = Field(0)
    n_round: int = Field(0)

    is_start_game: bool = Field(False)

    @property
    def god_names(self) -> str:
        return ', '.join([g.name for g in self.gods.values()])

    @property
    def info(self) -> str:
        redactor_god_name = getattr(self.gods.get(self.redactor_god_id), 'name', '')

        return f'Мир: {self.name},\n' \
               f'Эпоха: {self.n_era} \n' \
               f'Раунд: {self.n_round} \n' \
               f'Боги: {self.god_names},\n' \
               f'Ход бога: {redactor_god_name} \n'
