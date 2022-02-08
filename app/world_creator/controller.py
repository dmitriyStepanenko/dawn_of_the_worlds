from typing import Optional, Union

from .model import Actions, GodProfile, Race, World, LayerName, RaceFraction, City
from .tiles import Tile, ClimateType, ImageRef
from .world_manager import Manager, WorldManager, GodManager, RaceManager
from app.storage.storage import Storage


class Controller:
    def __init__(self, world_id: int, god_id: int):
        self.storage = Storage()
        self._god_id = god_id
        self._world_id = world_id

        self._init_manager()

    def _init_manager(self):
        if self.is_world_created:
            self.manager = Manager(self.load())

    @property
    def current_god(self) -> GodProfile:
        return self.manager.world.gods.get(self._god_id)

    @property
    def world(self) -> World:
        assert self.manager  # для mypy
        return self.manager.world

    @property
    def is_world_created(self):
        return self.storage.is_world_exist(self._world_id)

    @property
    def is_creation_end(self):
        return self.manager.is_creation_end

    def get_layer_num_tiles(self, layer_name: LayerName):
        layer = self.manager.get_layer(layer_name)
        if not layer:
            raise ValueError()
        return layer.num_tiles

    def save(self):
        self.storage.save_world(self._world_id, self.world)

    def load(self) -> World:
        return self.storage.load_world(self._world_id)

    def spend_force(self, action: Actions):
        value = self.manager.calc_action_cost(action)
        self.manager.spend_force(god_id=self._god_id, value=value)

    def render_map(self, layer_name: str = ''):
        layer_names = {l_name.value: l_name for l_name in LayerName}
        return self.manager.render_map(layer_names.get(layer_name))


class WorldController(Controller):
    def _init_manager(self):
        if self.is_world_created:
            self.manager = WorldManager(self.load())

    def create_world(self, name: str, layers_shape: tuple[int, int], percent: int):
        world = World(name=name, layers_shape=layers_shape)
        self.manager = WorldManager(world)
        self.manager.add_init_layers()
        self.manager.fill_base_lands_layer(percent)
        self.save()

    def remove_world(self):
        self.storage.remove_world(self._world_id)

    def start_game(self):
        self.world.is_start_game = True
        self.save()

    def render_story(self):
        return self.manager.render_story()


class GodController(Controller):
    def _init_manager(self):
        if self.is_world_created:
            self.manager = GodManager(world=self.load(), god_id=self._god_id)

    def add_god(self, name: str):
        if name in self.world.god_names:
            return None
        god = GodProfile(name=name)
        self.manager.add_god_profile(god)
        self.manager.receive_force(self._god_id)
        if self.world.redactor_god_id is None:
            self.world.redactor_god_id = self._god_id
        self.save()
        return god

    def next_redactor_god(self):
        god_ids = [god_id for god_id, god in self.world.gods.items() if not god.confirm_end_round]
        index = god_ids.index(self._god_id)
        index = index + 1 if index < len(god_ids) - 1 else 0

        self.world.redactor_god_id = god_ids[index]
        self.save()

    def set_current_message_id(self, message_id):
        self.world.current_message_with_buttons_id = message_id
        self.save()

    @property
    def is_allowed_to_act(self):
        if self.manager.is_creation_end or not self.world.is_start_game:
            return False

        if self.current_god.confirm_end_round:
            return False

        return self._god_id == self.world.redactor_god_id

    @property
    def is_allowed_to_end_era(self):
        return self.world.n_round > 4 and not self.current_god.confirm_end_era

    def end_round(self):
        self.current_god.confirm_end_round = True
        for other_god_id, other_god in self.manager.world.gods.items():
            if other_god_id == self._god_id:
                continue
            if not other_god.confirm_end_round:
                self.save()
                return None

        end_era_confirmations = [g.confirm_end_era for g in self.world.gods.values()]
        if all(end_era_confirmations) or (self.world.n_round > 9 and any(end_era_confirmations)):
            self.manager.start_new_era()

        self.manager.start_new_round()
        self.save()

    def end_era(self):
        self.current_god.confirm_end_era = True
        self.save()

    def collect_allowed_actions(self) -> list[str]:
        if self.is_allowed_to_act:
            actions = [
                action.name for action in Actions
                if action.value.costs[self.world.n_era] <= self.current_god.value_force
            ]
            if len(self.world.races) == 0:
                if Actions.DECREASE_REALM_ALIGNMENT.name in actions:
                    actions.remove(Actions.DECREASE_REALM_ALIGNMENT.name)
                if Actions.INCREASE_REALM_ALIGNMENT.name in actions:
                    actions.remove(Actions.INCREASE_REALM_ALIGNMENT.name)

            if not self.manager.get_controlled_race_names() and Actions.CONTROL_RACE.name in actions:
                actions.remove(Actions.CONTROL_RACE.name)
            return actions
        return []

    def get_controlled_race_names(self) -> list[str]:
        return self.manager.get_controlled_race_names()


class GodActionController(Controller):
    def _add_tile_on_layer(self, position: int, image_ref: Optional[str], layer_name: LayerName):
        tile = Tile(position=position, image_ref=image_ref, creator=self.current_god.name)
        self.manager.change_tile(layer_name, tile)
        return tile

    def form_land(self, tile_type: str, tile_num: int):
        tile = self._add_tile_on_layer(position=tile_num, image_ref=tile_type, layer_name=LayerName.LANDS)

        self.spend_force(Actions.CREATE_LAND)
        self.manager.log(f'{self.current_god} изменил ландшафт в координатах {tile.position} на {tile}')
        self.save()

    def form_climate(self, tile_type: str, tile_num: int):
        tile = self._add_tile_on_layer(
            position=tile_num,
            image_ref=tile_type if tile_type != ClimateType.CLEAR.value else None,
            layer_name=LayerName.CLIMATE
        )

        self.spend_force(Actions.CREATE_CLIMATE)
        self.manager.log(f'{self.current_god} изменил климат в координатах {tile.position} на {tile}')
        self.save()

    def create_event(self, description: str, position: Optional[int] = None):
        add_message = ''
        if position is not None:
            self._add_tile_on_layer(position=position, image_ref=ImageRef.EVENT.value, layer_name=LayerName.EVENT)
            add_message = f'в координатах {position}'
        self.world.events.append(description)
        self.spend_force(Actions.EVENT)
        self.manager.log(f'{self.current_god} создал событие {description}' + add_message)
        self.save()


class RaceController(Controller):
    def _init_manager(self):
        if self.is_world_created:
            self.manager = RaceManager(self.load())

    def is_race_exist(self, race_name: str):
        self.manager.is_exist_race(race_name)

    def create_race(self, name: str, description: str, init_position: int, alignment: int):
        race = Race(
            name=name,
            description=description,
            init_position=init_position,
            god_creator=self.current_god.name,
            alignment=alignment,
            fractions=[RaceFraction(god_owner=self.current_god.name, name=name)]
        )
        self.manager.world.races[race.name] = race

        self.manager.change_tile(LayerName.RACE, Tile(position=race.init_position))
        self.spend_force(Actions.CREATE_RACE)
        self.manager.log(f'{self.current_god} создал расу {race.name} с начальной позицией {race.init_position}')
        self.save()

    def change_race_alignment(self, race_name: str, alignment: int):
        if alignment == 1:
            action = Actions.INCREASE_REALM_ALIGNMENT
        elif alignment == -1:
            action = Actions.DECREASE_REALM_ALIGNMENT
        else:
            raise NotImplementedError

        race = self.manager.get_race(race_name)
        race.alignment += alignment
        self.spend_force(action)
        text_interpretation = 'очистил' if alignment == 1 else 'совратил'
        self.manager.log(f'{self.current_god} {text_interpretation} {race.name}')
        self.save()

    def get_race_names_and_alignments(self) -> list[tuple[str, int]]:
        return [(r.name, r.alignment) for r in self.world.races.values()]

    def get_race_fraction_names(self, race_name: str):
        race = self.manager.get_race(race_name)
        return [
            fraction.name for fraction in race.fractions
            if fraction.god_owner == self.current_god.name
        ]

    def create_city(self, race_name: str, city_name: str, position: int, fraction_name: str):
        race = self.manager.get_race(race_name)

        self.world.cities.append(City(
            name=city_name, base_race_name=race_name, fractions=[fraction_name], alignment=race.alignment))

        self.manager.change_tile(LayerName.RACE, Tile(position=position, image_ref=ImageRef.CITY.value))
        self.spend_force(Actions.CONTROL_RACE)

        self.manager.log(
            f'{self.current_god} приказал расе {race_name} основать город {city_name} в координатах {position}'
        )
        self.save()
