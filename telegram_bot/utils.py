from typing import Union
from pathlib import Path
import io

from PIL import Image

from aiogram import types, Dispatcher

from world_creator.controller import Controller
from world_creator.model import World


def convert_image(image: Image) -> types.InputFile:
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return types.InputFile(image_bytes)


def get_chat_id(message_or_call: Union[types.CallbackQuery, types.Message]):
    return get_chat(message_or_call).id


def get_user_id(message_or_call: Union[types.CallbackQuery, types.Message]):
    # todo
    if isinstance(message_or_call, types.Message):
        return message_or_call.from_user.id
    elif isinstance(message_or_call, types.CallbackQuery):
        return message_or_call.from_user.id
    else:
        raise NotImplementedError


def get_chat(message_or_call: Union[types.CallbackQuery, types.Message]):
    if isinstance(message_or_call, types.Message):
        return message_or_call.chat
    elif isinstance(message_or_call, types.CallbackQuery):
        return message_or_call.message.chat
    else:
        raise NotImplementedError


async def is_admin_state(message: types.Message):
    if message.chat.type != 'private':
        admins = await message.chat.get_administrators()
        admin_ids = [a.user.id for a in admins]
        for admin_id in admin_ids:
            if message.from_user.id == admin_id:
                continue
            state = await Dispatcher.get_current().current_state(chat=message.chat.id, user=admin_id).get_state()
            if state is not None:
                return True
    return False


async def is_user_admin(message_or_call: Union[types.Message, types.CallbackQuery]):
    chat = get_chat(message_or_call)
    if chat.type != 'private':
        admins = await chat.get_administrators()
        admin_ids = [a.user.id for a in admins]
        return message_or_call.from_user.id in admin_ids
    return True


def get_controller(message_or_call: Union[types.CallbackQuery, types.Message]) -> Controller:
    return Controller(get_chat_id(message_or_call), get_user_id(message_or_call))


def get_god_name_from_message(message: types.Message):
    try:
        return message.text.split('\n')[0].split(' ')[1]
    except Exception:
        return None
