from pydantic import BaseModel as PydanticBaseModel
import abc


class BaseModel(PydanticBaseModel, abc.ABC):
    """
    Базовый класс
    """

    class Config:
        extra = 'forbid'
        #: Конфигурация объектов модели. Делаем всегда проверку присвоения свойств
        validate_assignment = True