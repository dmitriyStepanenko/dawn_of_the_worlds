import datetime
from copy import deepcopy
from enum import Enum
from random import randint
from typing import Any

from PIL import Image
from pydantic import Field

from .base_model import BaseModel
from .image_manager import ImageCollection, ImageManager
from .tiles import Tile, EmptyTile, TILES

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
    CONTROL_AVATAR = Action(name='CONTROL_AVATAR', costs=[2, 1, 1])
    CATASTROPHE = Action(name='CATASTROPHE', costs=[10, 10, 10])


class GodProfile(BaseModel):
    name: str = Field(...)
    avatar_picture: str = Field('')

    value_force: int = Field(0)
    bonus_force: int = Field(0)

    confirm_end_round: bool = Field(False)
    confirm_end_era: bool = Field(False)

    def receive_force(self):
        bonus = self.bonus_force
        if self.value_force < 5:
            if self.bonus_force < 4:
                self.bonus_force += 1
        else:
            self.bonus_force = 0

        self.value_force += randint(1, 6) + randint(1, 6) + bonus

    def spend_force(self, value: int):
        self.value_force -= value

    def check_force_enough(self, target_value: int):
        if self.value_force < target_value:
            raise ValueError('Недостаточно силы')

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
    init_position: tuple[int, int] = Field(...)
    avatars: dict[str, Avatar] = Field({})
    god_creator: GodProfile = Field(...)
    fractions: dict[str, RaceFraction] = Field({})
    alignment: int = Field(0)
    parent_name: str = Field(None)
    technologies: list[str] = Field([])

    def apply_action(self, action):
        # TODO: вольные действия?
        ...


class City(BaseModel):
    def __init__(self, name, init_fraction, base_race: Race, **data: Any):
        super().__init__(**data)
        self.name = name
        self.fractions = [init_fraction]
        self.avatars = []

        self.alignment = base_race.alignment
        self.technologies: list[str] = []


class Layer(BaseModel):
    layer_name: str = Field(...)
    shape: tuple[int, int] = Field(...)
    tiles: list[list[TILES]] = Field([])

    def fill_empty(self):
        self.tiles: list[list[Tile]] = [
            [EmptyTile(x_pos=j, y_pos=i) for j in range(self.shape[0])]
            for i in range(self.shape[1])
        ]

    def get_tile(self, x_pos, y_pos):
        return self.tiles[x_pos][y_pos]

    def fill_layer(self, filling_tile: Tile):
        for j in range(self.shape[0]):
            for i in range(self.shape[1]):
                filling_tile.x_pos = j
                filling_tile.y_pos = i
                self.tiles[i][j] = deepcopy(filling_tile)

    def random_partial_fill_layer(self, percent_filling: int, filling_tile: Tile):
        if 0 > percent_filling > 100:
            raise ValueError('Количество процентов заполненности слоя должно быть от 0 до 100')

        list_changes = []
        while len(list_changes) <= self.shape[0] * self.shape[1] * percent_filling // 100:
            y_pos = randint(0, self.shape[1] - 1)
            x_pos = randint(0, self.shape[0] - 1)
            if (y_pos, x_pos) in list_changes:
                continue
            else:
                list_changes.append((y_pos, x_pos))

        for y_pos, x_pos in list_changes:
            filling_tile.x_pos = x_pos
            filling_tile.y_pos = y_pos
            self.tiles[y_pos][x_pos] = deepcopy(filling_tile)

    def replace_tile(self, tile: Tile):
        if 0 <= tile.x_pos <= self.shape[0] and 0 <= tile.y_pos <= self.shape[1]:
            self.tiles[tile.x_pos][tile.y_pos] = tile
        else:
            raise ValueError(f'Положение тайла {tile} выходит за границы слоя {self.shape}')

    def render(self, images: ImageCollection):
        world_map_image = Image.new(
            'RGBA',
            (images.image_size[0] * self.shape[0], images.image_size[1] * self.shape[1])
        )
        for tile_line in self.tiles:
            for tile in tile_line:
                if tile.image_ref is not None:
                    world_map_image.paste(
                        images.get_image(tile.image_ref),
                        (tile.x_pos * images.image_size[0], tile.y_pos * images.image_size[1]),
                    )
        return world_map_image

    def __str__(self):
        out_str = ''
        for tile_lines in self.tiles:
            for tile in tile_lines:
                out_str += str(tile) + ' '
            out_str += '\n'
        return out_str


class World(BaseModel):
    name: str = Field(...)
    layers: dict[str, Layer] = Field({})
    layers_shape: tuple[int, int] = Field(...)
    change_log: list[str] = Field([])

    gods: dict[int, GodProfile] = Field({}, description='Профайлы богов по id их владельцев')
    races: dict[str, Race] = Field({})
    cities: dict[str, City] = Field({})

    redactor_god_name: str = Field('')
    time_block: datetime.datetime = Field(datetime.datetime.min)

    n_era: int = Field(0)
    n_round: int = Field(0)

    @property
    def info(self):
        # todo
        return f'Мир: {self.name},\n' \
               f'Эпоха: {self.n_era} \n' \
               f'Раунд: {self.n_round} \n' \
               f'Боги: {[g.name for g in self.gods.values()]},\n'
