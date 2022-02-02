from copy import deepcopy
from random import randint, choice
from typing import Optional

from PIL import Image

from .image_manager import ImageManager
from .model import World, Actions
from .model import Layer, LayerName
from .tiles import Tile, EmptyTile
from .tiles import LandType
from .model import GodProfile
from .model import Race

LAYER_SHAPE_SCALE_COEFFICIENT = 3


class WorldManager:
    def __init__(self, world: World):
        """
        Класс для управления объектом "мир"
        """
        self.world = world

        self.is_creation_end = False

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

    def create_layer(self, layer_name: LayerName, shape: tuple[int, int] = None):
        self.world.layers[layer_name.value] = Layer(layer_name=layer_name.value, shape=shape or self.world.layers_shape)
        self.fill_layer(layer_name, EmptyTile(position=0))

    def get_layer(self, layer_name: LayerName):
        layer: Layer = self.world.layers.get(layer_name.value)
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

    def add_init_layers(self):
        """
        Считаем, что изначально есть слои:
        Территория, Климат
        """
        scaled_shape = (
            self.world.layers_shape[0] * LAYER_SHAPE_SCALE_COEFFICIENT,
            self.world.layers_shape[1] * LAYER_SHAPE_SCALE_COEFFICIENT
        )
        self.create_layer(LayerName.LANDS)
        self.create_layer(LayerName.CLIMATE)
        self.create_layer(LayerName.RACE, shape=scaled_shape)
        self.create_layer(LayerName.EVENT, shape=scaled_shape)

    def fill_base_lands_layer(self, percent_of_plateau: int = 40):
        """
        Создает слой Территории и случайно заполняет его тайлами "вода" и "плато"
        :param percent_of_plateau: процентное соотношение "плато" к площади всего слоя
        """
        self.fill_layer(
            layer_name=LayerName.LANDS,
            filling_tile=Tile(position=0, image_ref=LandType.WATER.value)
        )
        self.random_partial_fill_layer(
            layer_name=LayerName.LANDS,
            percent_filling=percent_of_plateau,
            filling_tile=Tile(position=0, image_ref=LandType.PLATEAU.value)
        )

        self.log(
            f'Мир был создан с {percent_of_plateau} процентным соотношением земля/(земля + вода)'
        )

    def change_tile(self, layer_name: LayerName, tile: Tile):
        layer = self.get_layer(layer_name)
        layer.tiles[tile.position] = tile

    def calc_action_cost(self, action: Actions) -> int:
        return action.value.costs[self.world.n_era]

    def log(self, message: str):
        self.world.change_log.append(message)

    def fill_layer(self, layer_name: LayerName, filling_tile: Tile):
        layer = self.get_layer(layer_name)
        layer.tiles = []
        for i in range(layer.num_tiles):
            filling_tile.position = i
            layer.tiles.append(deepcopy(filling_tile))

    def random_partial_fill_layer(self, layer_name: LayerName, percent_filling: int, filling_tile: Tile):
        if 0 > percent_filling > 100:
            raise ValueError('Количество процентов заполненности слоя должно быть от 0 до 100')

        layer = self.get_layer(layer_name)

        not_changed_tile_positions = list(range(layer.num_tiles))
        while round(layer.num_tiles * (1 - percent_filling / 100)) < len(not_changed_tile_positions):
            pos = choice(not_changed_tile_positions)
            not_changed_tile_positions.remove(pos)
            filling_tile.position = pos
            layer.tiles[pos] = deepcopy(filling_tile)

    def get_controlled_race_names(self, god_id: int):
        god = self.world.gods.get(god_id)
        race_names = []
        for race in self.world.races.values():
            for fraction in race.fractions:
                if fraction.god_owner == god.name:
                    race_names.append(race.name)
        return race_names

    def render_map(
            self,
            add_grid_for_layer: Optional[LayerName] = None
    ) -> Image:
        image_manager = ImageManager()

        world_map_image = None
        image_collection_loaders = [
            image_manager.load_land_tiles,
            image_manager.load_climate_tiles,
            image_manager.load_race_init_tiles,
            image_manager.load_event_tiles,
        ]
        for layer_name, image_collection_loader in zip(LayerName, image_collection_loaders):
            layer = self.get_layer(layer_name)
            layer_image = image_manager.render_layer(layer, image_collection_loader())
            if world_map_image:
                image_manager.paste_scaled_image_with_alpha(world_map_image, layer_image)
            else:
                world_map_image = layer_image

        if add_grid_for_layer:
            gird_layer = self.get_layer(add_grid_for_layer)
            grid_image = image_manager.draw_grid(world_map_image.size, gird_layer.shape)
            image_manager.paste_scaled_image_with_alpha(world_map_image, grid_image)

        return world_map_image

    def render_story(self) -> str:
        out_str = ''
        for change in self.world.change_log:
            out_str += str(change) + '\n'

        return out_str
