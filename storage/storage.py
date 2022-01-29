from pathlib import Path

from world_creator.model import World

STORAGE_DIR = Path(__file__).parent / 'data'


class Storage:
    def __init__(self):
        self.storage_dir = STORAGE_DIR

    def save_world(self, file_name, world: World):
        with open(self.storage_dir / f'{file_name}.json', 'w') as f:
            f.write(world.json())

    def load_world(self, file_name):
        return World.parse_file(self.storage_dir / f'{file_name}.json')

    def remove_world(self, file_name):
        Path(self.storage_dir / f'{file_name}.json').unlink()

    def is_world_exist(self, file_name):
        return f'{file_name}.json' in [f.name for f in self.storage_dir.glob('*.json')]