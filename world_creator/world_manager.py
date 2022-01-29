from copy import deepcopy
from random import randint, choice

from PIL import Image

from .image_manager import ImageCollection, ImageManager
from .model import World, Actions
from .model import Layer
from .tiles import TerrainTile, EmptyTile
from .tiles import LandType
from .model import GodProfile
from .tiles import Tile
from .model import Race


class WorldManager:
    def __init__(self, world: World):
        """
        Класс для управления объектом "мир"
        """
        self.world = world

        self.is_creation_end = False
        self.REMOVE_COEFFICIENT = 1

    def end_of_world(self):
        self.log('Мир создан')
        self.is_creation_end = True

    def start_new_round(self):
        self.world.redactor_god_id = list(self.world.gods.keys())[0]
        self.world.n_round += 1
        for god_id, god in self.world.gods.items():
            god.confirm_end_round = False
            self.receive_force(god_id)

    def start_new_era(self):
        if self.world.n_era > 3:
            self.end_of_world()
            return

        self.world.n_era += 1
        self.world.n_round = -1
        for god in self.world.gods.values():
            god.confirm_end_round = False
            god.confirm_end_era = False

    def add_god_profile(self, god: GodProfile, god_id: int):
        if getattr(self.world.gods.get(god_id), 'name', None) == god.name:
            raise ValueError(f'В этом мире уже есть бог с именем {god.name}')

        self.world.gods[god_id] = god

    def spend_force(self, god_id: int, value: int):
        god = self.world.gods[god_id]
        god.value_force -= value

    def receive_force(self, god_id: int):
        god = self.world.gods[god_id]
        bonus = god.bonus_force
        if god.value_force < 5:
            if god.bonus_force < 4:
                god.bonus_force += 1
        else:
            god.bonus_force = 0

        god.value_force += randint(1, 6) + randint(1, 6) + bonus

    def create_layer(self, layer_name: str, shape: tuple[int, int] = None):
        layer = Layer(layer_name=layer_name, shape=shape or self.world.layers_shape)
        self.fill_layer(layer, EmptyTile(position=0))
        self.world.layers[layer_name] = layer
        return layer

    def get_layer(self, layer_name: str):
        layer: Layer = self.world.layers.get(layer_name)
        if layer is None:
            raise ValueError(f'Нет слоя с названием: {layer_name}')
        return layer

    def get_race(self, name: str):
        race: Race = self.world.races.get(name)
        if race is None:
            raise ValueError(f'Нет расы с названием: {name}')
        return race

    def is_exist_race(self, name: str):
        return self.world.races.get(name) is not None

    def get_city(self, name: str):
        city = self.world.cities.get(name)
        if city is None:
            raise ValueError(f'Нет города с названием: {name}')
        return city

    def add_init_layers(self):
        """
        Считаем, что изначально есть слои:
        Территория, Климат, Чудеса, Расы
        """
        self.create_layer('lands')
        self.create_layer('climate')
        self.create_layer('races')
        self.create_layer('miracles')

    def create_base_lands_layer(self, percent_of_plateau: int = 40):
        """
        Создает слой Территории и случайно заполняет его тайлами "вода" и "плато"
        :param percent_of_plateau: процентное соотношение "плато" к площади всего слоя
        """
        layer = self.create_layer('lands')
        self.fill_layer(layer, TerrainTile(position=0, type_land=LandType.WATER))
        self.random_partial_fill_layer(layer, percent_of_plateau, TerrainTile(position=0, type_land=LandType.PLATEAU))

        self.log(
            f'Мир был создан с {percent_of_plateau} процентным соотношением земля/(земля + вода)'
        )

    def change_tile(self, layer_name: str, tile: Tile):
        layer = self.get_layer(layer_name)
        layer.tiles[tile.position] = tile

    def calc_action_cost(self, action: Actions):
        return action.value.costs[self.world.n_era]

    def log(self, message: str):
        self.world.change_log.append(message)

    def render_layer(
            self,
            layer_name: str,
            image_collection: ImageCollection,
            add_grid: bool = False,
            image_manager: ImageManager = ImageManager(),
    ):
        layer = self.world.layers.get(layer_name)
        layer_image = image_manager.render_layer(layer, image_collection)

        if add_grid:
            grid_image = image_manager.draw_grid(layer_image.size, layer.shape)
            image_manager.paste_scaled_image_with_alpha(layer_image, grid_image)

        return layer_image

    @staticmethod
    def fill_layer(layer: Layer, filling_tile: Tile):
        for i in range(layer.num_tiles):
            filling_tile.position = i
            layer.tiles[i] = deepcopy(filling_tile)

    @staticmethod
    def random_partial_fill_layer(layer: Layer, percent_filling: int, filling_tile: Tile):
        if 0 > percent_filling > 100:
            raise ValueError('Количество процентов заполненности слоя должно быть от 0 до 100')

        not_changed_tile_positions = list(range(layer.num_tiles))
        while layer.num_tiles * (1 - percent_filling // 100) < len(not_changed_tile_positions):
            pos = choice(not_changed_tile_positions)
            not_changed_tile_positions.remove(pos)
            filling_tile.position = pos
            layer.tiles[pos] = deepcopy(filling_tile)

    def render_map(self, image_manager: ImageManager = ImageManager(),) -> Image:
        world_map_image = self.render_layer('lands', image_manager.load_land_tiles(), add_grid=True)

        # race_layer_image = self.render_layer('races', image_manager.load_race_init_tiles())
        # image_manager.paste_scaled_image_with_alpha(world_map_image, race_layer_image)
        #
        # climate_layer_image = self.render_layer('climate', image_manager.load_climate_tiles())
        # image_manager.paste_scaled_image_with_alpha(world_map_image, climate_layer_image)

        return world_map_image

    def render_story(self) -> str:
        out_str = ''
        for change in self.world.change_log:
            out_str += str(change) + '\n'

        return out_str
