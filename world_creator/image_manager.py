from PIL import Image, ImageDraw
from .tiles import LandType
from .tiles import ClimateType
from .tiles import InitPositionRaceTile
from pathlib import Path


class ImageCollection:
    def __init__(self, images: dict, image_size: tuple[int, int]):
        """Коллекция изображений с одинаковым размером"""
        self.images: dict[str, Image] = images
        self.image_size = image_size
        self.validate()

    def validate(self):
        for image in self.images.values():
            if image.size != self.image_size:
                raise ValueError('Все изображения в коллекции должны быть одного размера')

    def get_image(self, ref):
        image = self.images.get(ref)
        if image is None:
            raise ValueError(f'Изображения со ссылкой {ref} нет в коллекции')
        return image


class ImageManager:
    def __init__(self):
        self.image_dir = Path(__file__).parent / 'tile_pics'

    @staticmethod
    def paste_scaled_image_with_alpha(base_image: Image, add_image: Image):
        add_image = add_image.resize(base_image.size)
        base_image.paste(add_image, mask=add_image)
        return base_image

    def load_land_tiles(self):
        images = {
            LandType.FOREST.value: Image.open(self.image_dir / 'forest.png'),
            LandType.WATER.value: Image.open(self.image_dir / 'water.png'),
            LandType.SAND.value: Image.open(self.image_dir / 'sand.png'),
            LandType.ROCK.value: Image.open(self.image_dir / 'rock.png'),
            LandType.PLATEAU.value: Image.open(self.image_dir / 'plateau.png'),
        }
        return ImageCollection(images=images, image_size=images[LandType.WATER.value].size)

    def load_race_init_tiles(self):
        init_pos_image = Image.open(self.image_dir / 'race_init_tile.png')
        return ImageCollection({InitPositionRaceTile.__name__: init_pos_image}, image_size=init_pos_image.size)

    def load_climate_tiles(self):
        images = {
            ClimateType.CLOUD: Image.open(self.image_dir / 'cloud.png'),
            ClimateType.RAIN: Image.open(self.image_dir / 'rain.png'),
            ClimateType.SNOW: Image.open(self.image_dir / 'snow.png')
        }
        return ImageCollection(images=images, image_size=images[ClimateType.CLOUD].size)

    @staticmethod
    def draw_grid(size: tuple[int, int], shape: tuple[int, int]) -> Image:
        image = Image.new('RGBA', size)
        draw = ImageDraw.Draw(image)
        x_coeff = size[0] / shape[0]
        y_coeff = size[1] / shape[1]
        for x in range(shape[0]):
            for y in range(shape[1]):
                draw.line(((x * x_coeff, 0), (x * x_coeff, size[1])), fill='black', width=2)
                draw.line(((0, y * y_coeff), (size[1], y * y_coeff)), fill='black', width=2)

                text = f'{x + shape[0] * y}'
                text_width, text_height = draw.textsize(text)
                draw.text(((x + 0.5) * x_coeff - 0.5 * text_width, (y + 0.5) * y_coeff - 0.5 * text_height), text)

        draw.line(((shape[0] * x_coeff, 0), (shape[0] * x_coeff, size[1])), fill='black', width=2)
        draw.line(((0, shape[1] * y_coeff), (size[1], shape[1] * y_coeff)), fill='black', width=2)

        return image
