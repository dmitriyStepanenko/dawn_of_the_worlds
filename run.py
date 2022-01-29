from world_creator.model import GodProfile, Race, RaceFraction
from world_creator.model import World
from world_creator.tiles import TerrainTile, Tile, ClimateType
from world_creator.tiles import LandType
from world_creator.world_manager import WorldManager
from world_creator.controller import Controller


def main():
    world_manager = WorldManager(World(name='aa', layers_shape=(2, 3)))
    controller = Controller(world_manager)
    god1 = GodProfile(name='first god')
    god1.value_force = 1000000

    world_manager.add_god_profile(god1, 1324)

    print(f"Бог {god1.name} имеет {god1.value_force} очков божественной силы.")

    world_manager.create_base_lands_layer()
    obj = world_manager.world.json()

    deobj = World.parse_raw(obj)
    a = 1
    # world_manager.create_layer('races', (12, 12))
    # world_manager.create_layer('climate')

    # controller.form_land(god1, TerrainTile(0, 0, LandType.FOREST))
    # controller.create_race(god1, Race('People', '', (1, 5), god1, RaceFraction(god1, 'atheists')))
    # controller.form_climate(god1, Tile(3, 3, ClimateType.CLOUD))

    # print(world_manager.world.render_story())
    #
    # image = world_manager.world.render_map()
    # image.save('world_map.png')


if __name__ == '__main__':
    main()
