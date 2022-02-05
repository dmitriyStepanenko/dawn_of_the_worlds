from app.world_creator.world_manager import GodManager
from app.world_creator.model import GodProfile, Race, RaceFraction

import pytest


@pytest.fixture
def god() -> GodProfile:
    return GodProfile(name='test god')


def test_add_god_profile(world, god):
    god_id = 0
    manager = GodManager(world, god_id)

    manager.add_god_profile(god)

    assert world.gods[god_id] == god


@pytest.mark.parametrize(
    'init_force, init_bonus_force, result_bonus_force',
    [(0, 0, 1), (4, 1, 2), (4, 3, 3), (5, 0, 0), (6, 2, 0), (10, 3, 0)]
)
def test_receive_force(world, god, init_force, init_bonus_force, result_bonus_force):
    god_id = 0
    manager = GodManager(world, god_id)
    manager.add_god_profile(god)
    god.value_force = init_force
    god.bonus_force = init_bonus_force

    manager.receive_force(god_id)

    assert init_force + 2 <= god.value_force <= init_force + 12
    assert god.bonus_force == result_bonus_force


@pytest.mark.parametrize('redactor_god_id', [0, 1, 4])
def test_start_new_round(world, redactor_god_id):
    for i in range(4):
        world.gods[i] = GodProfile(name=f'test god {i}', confirm_end_round=True)
    world.redactor_god_id = redactor_god_id
    manager = GodManager(world, 0)
    init_n_round = world.n_round

    manager.start_new_round()

    assert world.n_round == init_n_round + 1
    assert world.redactor_god_id == 0
    for g in world.gods.values():
        assert g.confirm_end_era is False
        assert g.value_force > 0


@pytest.mark.parametrize('n_era, n_round', [(0, 0), (3, 0), (2, 4), (4, 2)])
def test_start_new_era(world, n_era, n_round):
    world.n_era = n_era
    world.n_round = n_round
    for i in range(4):
        world.gods[i] = GodProfile(name=f'test god {i}', confirm_end_round=True, confirm_end_era=True)
    manager = GodManager(world, 0)

    manager.start_new_era()

    if n_era < 4:
        assert world.n_era == n_era + 1
        assert world.n_round == -1
        for god in world.gods.values():
            assert god.confirm_end_round is False
            assert god.confirm_end_era is False
    else:
        assert world.change_log[-1] == 'Мир создан'


def test_get_controlled_race_names(world):
    god0 = GodProfile(name='test_god0')
    god1 = GodProfile(name='test_god1')
    world.gods = {0: god0, 1: god1}
    race = Race(
        name='race0',
        description='aaa',
        init_position=0,
        god_creator=god0.name,
        fractions=[RaceFraction(name='fff', god_owner=god0.name)]
    )
    world.races[race.name] = race
    race1 = Race(
        name='race1',
        description='aaa',
        init_position=2,
        god_creator=god1.name,
        fractions=[RaceFraction(name='ddd', god_owner=god1.name)]
    )
    world.races[race1.name] = race1
    race2 = Race(
        name='race2',
        description='aaa',
        init_position=4,
        god_creator=god1.name,
        fractions=[RaceFraction(name='hhh', god_owner=god1.name), RaceFraction(name='kkk', god_owner=god0.name)]
    )
    world.races[race2.name] = race2

    manager = GodManager(world, 0)

    race_names = manager.get_controlled_race_names()

    assert race.name in race_names
    assert race2.name in race_names