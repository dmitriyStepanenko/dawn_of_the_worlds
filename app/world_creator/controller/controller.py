from typing import Optional

from ..model import Actions, GodProfile, Race, World, LayerName, RaceFraction, City
from ..tiles import Tile, ClimateType, ImageRef
from ..world_manager import WorldManager
from app.storage.storage import Storage


class Controller:
    def __init__(self, world_id: int, god_id: int):
        self.storage = Storage()
        self._god_id = god_id
        self._world_id = world_id

        if self.is_world_created:
            world = self.storage.load_world(world_id)
            self.world_manager = WorldManager(world)

    @property
    def current_god(self) -> GodProfile:
        return self.world_manager.world.gods.get(self._god_id)

    @property
    def world(self) -> World:
        return self.world_manager.world

    @property
    def is_world_created(self):
        return self.storage.is_world_exist(self._world_id)

    def get_layer_num_tiles(self, layer_name: LayerName):
        return self.world_manager.get_layer(layer_name).num_tiles

    def save(self):
        self.storage.save_world(self._world_id, self.world)

    def spend_force(self, action: Actions):
        value = self.world_manager.calc_action_cost(action)
        self.world_manager.spend_force(god_id=self._god_id, value=value)

    def render_map(self, layer_name: str = None):
        layer_names = {l_name.value: l_name for l_name in LayerName}
        return self.world_manager.render_map(layer_names.get(layer_name))


class WorldController(Controller):
    def create_world(self, name: str, layers_shape: tuple[int, int], percent: int):
        world = World(name=name, layers_shape=layers_shape)
        self.world_manager = WorldManager(world)
        self.world_manager.add_init_layers()
        self.world_manager.fill_base_lands_layer(percent)
        self.save()

    def remove_world(self):
        self.storage.remove_world(self._world_id)

    def start_game(self):
        self.world.is_start_game = True
        self.save()


class GodController(Controller):
    def add_god(self, name: str):
        if name in self.world.god_names:
            return None
        god = GodProfile(name=name)
        self.world_manager.add_god_profile(god, self._god_id)
        self.world_manager.receive_force(self._god_id)
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
        if self.world_manager.is_creation_end or not self.world.is_start_game:
            return False

        if self.current_god.confirm_end_round:
            return False

        return self._god_id == self.world.redactor_god_id

    @property
    def is_allowed_to_end_era(self):
        return self.world.n_round > 4 and not self.current_god.confirm_end_era

    def end_round(self):
        self.current_god.confirm_end_round = True
        for other_god_id, other_god in self.world_manager.world.gods.items():
            if other_god_id == self._god_id:
                continue
            if not other_god.confirm_end_round:
                self.save()
                return None

        end_era_confirmations = [g.confirm_end_era for g in self.world.gods.values()]
        if all(end_era_confirmations) or (self.world.n_round > 9 and any(end_era_confirmations)):
            self.world_manager.start_new_era()

        self.world_manager.start_new_round()
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

            if not self.world_manager.get_controlled_race_names(self._god_id) and Actions.CONTROL_RACE.name in actions:
                actions.remove(Actions.CONTROL_RACE.name)
            return actions
        return []


class GodActionController(Controller):
    def form_land(self, tile_type: str, tile_num: int):
        tile = Tile(position=tile_num, image_ref=tile_type)
        tile.creator = self.current_god.name
        self.world_manager.change_tile(LayerName.LANDS, tile)

        self.spend_force(Actions.CREATE_LAND)
        self.world_manager.log(f'{self.current_god} изменил ландшафт в координатах {tile.position} на {tile}')
        self.save()

    def form_climate(self, tile_type: str, tile_num: int):
        if tile_type == ClimateType.CLEAR.value:
            tile_type = None
        tile = Tile(position=tile_num, image_ref=tile_type)

        tile.creator = self.current_god.name
        self.world_manager.change_tile(LayerName.CLIMATE, tile)

        self.spend_force(Actions.CREATE_CLIMATE)
        self.world_manager.log(f'{self.current_god} изменил климат в координатах {tile.position} на {tile}')
        self.save()

    def create_event(self, description: str, position: Optional[int] = None):
        add_message = ''
        if position is not None:
            self.world_manager.change_tile(LayerName.EVENT, Tile(position=position, image_ref=ImageRef.EVENT.value))
            add_message = f'в координатах {position}'
        self.world.events.append(description)
        self.spend_force(Actions.EVENT)
        self.world_manager.log(f'{self.current_god} создал событие {description}' + add_message)
        self.save()


class RaceController(Controller):
    def is_race_exist(self, race_name: str):
        self.world_manager.is_exist_race(race_name)

    def create_race(self, name: str, description: str, init_position: int, alignment: int):
        race = Race(
            name=name,
            description=description,
            init_position=init_position,
            god_creator=self.current_god.name,
            alignment=alignment,
            fractions=[RaceFraction(god_owner=self.current_god.name, name=name)]
        )
        self.world_manager.world.races[race.name] = race

        self.world_manager.change_tile(LayerName.RACE, Tile(position=race.init_position))
        self.spend_force(Actions.CREATE_RACE)
        self.world_manager.log(f'{self.current_god} создал расу {race.name} с начальной позицией {race.init_position}')
        self.save()

    def change_race_alignment(self, race_name: str, alignment: int):
        if alignment == 1:
            action = Actions.INCREASE_REALM_ALIGNMENT
        elif alignment == -1:
            action = Actions.DECREASE_REALM_ALIGNMENT
        else:
            raise NotImplementedError

        race = self.world_manager.get_race(race_name)
        race.alignment += alignment
        self.spend_force(action)
        text_interpretation = 'очистил' if alignment == 1 else 'совратил'
        self.world_manager.log(f'{self.current_god} {text_interpretation} {race.name}')
        self.save()

    def get_race_names_and_alignments(self) -> list[tuple[str, int]]:
        return [(r.name, r.alignment) for r in self.world.races.values()]

    def get_controlled_race_names(self) -> list[str]:
        return self.world_manager.get_controlled_race_names(self._god_id)

    def get_race_fraction_names(self, race_name: str):
        race = self.world_manager.get_race(race_name)
        return [
            fraction.name for fraction in race.fractions
            if fraction.god_owner == self.current_god.name
        ]

    def create_city(self, race_name: str, city_name: str, position: int, fraction_name: str):
        race = self.world_manager.get_race(race_name)

        self.world.cities.append(City(
            name=city_name, base_race_name=race_name, fractions=[fraction_name], alignment=race.alignment))

        self.world_manager.change_tile(LayerName.RACE, Tile(position=position, image_ref=ImageRef.CITY.value))
        self.spend_force(Actions.CONTROL_RACE)

        self.world_manager.log(
            f'{self.current_god} приказал расе {race_name} основать город {city_name} в координатах {position}'
        )
        self.save()
