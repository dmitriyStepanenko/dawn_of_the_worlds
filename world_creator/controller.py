from .model import Actions, GodProfile, Race, Avatar, World
from .tiles import InitPositionRaceTile, Tile, TerrainTile, LandType
from .world_manager import WorldManager
from storage.storage import Storage


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

    def save(self):
        self.storage.save_world(self._world_id, self.world)

    def create_world(self, name: str, layers_shape: tuple[int, int], percent: int):
        world = World(name=name, layers_shape=layers_shape)
        self.world_manager = WorldManager(world)
        self.world_manager.create_base_lands_layer(percent)
        self.save()

    def remove_world(self):
        self.storage.remove_world(self._world_id)

    def start_game(self):
        self.world.is_start_game = True
        self.save()

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

    def collect_allowed_actions(self):
        if self.is_allowed_to_act:
            return [
                action.name for action in Actions
                if action.value.costs[self.world.n_era] <= self.current_god.value_force
            ]
        return []

    def form_land(self, tile_type: str, tile_num: int):
        # todo move constant
        layer_name = 'lands'

        land_types = {
            LandType.WATER.value: LandType.WATER,
            LandType.FOREST.value: LandType.FOREST,
            LandType.SAND.value: LandType.SAND,
            LandType.ROCK.value: LandType.ROCK,
            LandType.PLATEAU.value: LandType.PLATEAU,
        }
        tile = TerrainTile(position=tile_num, type_land=land_types[tile_type])

        force_value = self.world_manager.calc_action_cost(Actions.CREATE_LAND)
        tile.creator = self.current_god.name
        self.world_manager.change_tile(layer_name, tile)

        self.world_manager.spend_force(god_id=self._god_id, value=force_value)
        self.world_manager.log(f'{self.current_god} изменил ландшафт в координатах {tile.position} на {tile}')
        self.save()

    #
    # def form_climate(self, god: GodProfile, tile: Tile):
    #     layer_name = 'climate'
    #     cost_coefficient = self.world_manager.calc_action_cost_coefficient(layer_name, tile, god)
    #     force_value = self.world_manager.calc_action_cost(Actions.CREATE_CLIMATE) * cost_coefficient
    #     god.check_force_enough(force_value)
    #     tile.creator = god.name
    #     self.world_manager.change_tile(layer_name, tile)
    #
    #     god.spend_force(force_value)
    #     if cost_coefficient == 1:
    #         message = f'{god} создал климатическую зону {tile} в координатах {tile.position}'
    #     else:
    #         message = f'{god} изменил климатическую зону в координатах {tile.position} на {tile}'
    #     self.world_manager.log(message)
    #
    # def create_race(self, god: GodProfile, race: Race):
    #     if self.world_manager.is_exist_race(race.name):
    #         raise ValueError(f'Раса {race.name} уже существует')
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.CREATE_RACE)
    #     god.check_force_enough(force_value)
    #     self.world_manager.world.races[race.name] = race
    #
    #     layer = self.world_manager.get_layer('races')
    #     layer.replace_tile(InitPositionRaceTile(*race.init_position))
    #     god.spend_force(force_value)
    #     self.world_manager.log(f'{god} создал расу {race.name} с начальной позицией {race.init_position}')
    #
    # def create_subrace(self, god: GodProfile, race: Race):
    #     if self.world_manager.is_exist_race(race.name):
    #         raise ValueError(f'Раса {race.name} уже существует')
    #
    #     if not self.world_manager.is_exist_race(race.parent_name):
    #         raise ValueError(f'У подрасы должна быть раса предок')
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.CREATE_SUBRACE)
    #     god.check_force_enough(force_value)
    #     self.world_manager.world.races[race.name] = race
    #
    #     layer = self.world_manager.get_layer('races')
    #     layer.replace_tile(InitPositionRaceTile(*race.init_position))
    #     god.spend_force(force_value)
    #     self.world_manager.log(
    #         f'{god} создал подрасу {race.name} расы {race.parent_name} с начальной позицией {race.init_position}'
    #     )
    #
    # def control_race(self, god: GodProfile, race_name: str, race_action):
    #     race = self.world_manager.get_race(race_name)
    #
    #     if god.name not in [f.god_owner.name for f in race.fractions.values()]:
    #         raise ValueError(f'{god.name} не имеет влияния на расу {race_name}')
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.CONTROL_RACE)
    #     god.check_force_enough(force_value)
    #     tile = race.apply_action(race_action)
    #
    #     if tile is not None:
    #         layer_name = ...
    #         layer = self.world_manager.get_layer(layer_name)
    #         layer.replace_tile(tile)
    #
    #     god.spend_force(force_value)
    #
    #     self.world_manager.log(f'{god} приказал расе {race.name} {race_action.description}')
    #
    # def control_city(self, god: GodProfile, city_name: str, city_action):
    #     city = self.world_manager.get_city(city_name)
    #
    #     if god.name not in [f.god_owner.name for f in city.fractions + city.avatars]:
    #         raise ValueError(f'{god.name} не имеет влияния на город {city_name}')
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.CONTROL_CITY)
    #     god.check_force_enough(force_value)
    #     tile = city.apply_action()
    #
    # def develop_race(self, god: GodProfile, race_name: str, technology: str):
    #     race = self.world_manager.get_race(race_name)
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.DEVELOP_REALM)
    #     god.check_force_enough(force_value)
    #
    #     race.technologies.append(technology)
    #     god.spend_force(force_value)
    #     self.world_manager.log(f'{god} даровал расе знания: {technology}')
    #
    # def develop_city(self, god: GodProfile, city_name: str, technology: str):
    #     city = self.world_manager.get_city(city_name)
    #
    #     force_value = self.world_manager.calc_action_cost(Actions.DEVELOP_CITY)
    #     god.check_force_enough(force_value)
    #
    #     city.technologies.append(technology)
    #     god.spend_force(force_value)
    #     self.world_manager.log(f'{god} даровал городу знания: {technology}')
    #
    # def change_alignment(self, god: GodProfile, obj, value: int, action: Actions):
    #     if not hasattr(obj, 'alignment'):
    #         raise ValueError(f'У объекта {obj} нет элаймента')
    #
    #     force_value = self.world_manager.calc_action_cost(action)
    #     god.check_force_enough(force_value)
    #
    #     obj.alignment += value
    #     god.spend_force(force_value)
    #
    # def increase_race_alignment(self, god: GodProfile, race_name: str):
    #     race = self.world_manager.get_race(race_name)
    #
    #     self.change_alignment(god, race, 1, Actions.INCREASE_REALM_ALIGNMENT)
    #     self.world_manager.log(f'{god.name} очистил расу {race_name}')
    #
    # def decrease_realm_alignment(self, god: GodProfile, race_name: str):
    #     race = self.world_manager.get_race(race_name)
    #
    #     self.change_alignment(god, race, -1, Actions.INCREASE_REALM_ALIGNMENT)
    #     self.world_manager.log(f'{god.name} совратил расу {race_name}')
    #
    # def increase_city_alignment(self, god: GodProfile, city_name: str):
    #     city = self.world_manager.get_city(city_name)
    #
    #     self.change_alignment(god, city, 1, Actions.INCREASE_CITY_ALIGNMENT)
    #     self.world_manager.log(f'{god} очистил город {city_name}')
    #
    # def decrease_city_alignment(self, god: GodProfile, city_name: str):
    #     city = self.world_manager.get_city(city_name)
    #
    #     self.change_alignment(god, city, -1, Actions.INCREASE_CITY_ALIGNMENT)
    #     self.world_manager.log(f'{god} совратил город {city_name}')
    #
    # def make_event(self):
    #     ...
    #
    # def create_order(self):
    #     ...
    #
    # def control_order(self):
    #     ...
    #
    # def create_avatar(self, god: GodProfile, race: Race, avatar: Avatar):
    #     force_value = self.world_manager.calc_action_cost(Actions.CREATE_AVATAR)
    #     god.check_force_enough(force_value)
    #     race = self.world_manager.get_race(race.name)
    #
    #     if race.avatars.get(avatar.name) is None:
    #         raise ValueError(f'Аватар {avatar.name} уже существует у расы {race.name}')
    #
    #     race.avatars[avatar.name] = avatar
    #
    #     god.spend_force(force_value)
    #     self.world_manager.log(f'{god} создал аватара {avatar.name} у расы {race.name}')
    #
    # def control_avatar(self):
    #     ...
    #
    # def catastrophe(self):
    #     ...
