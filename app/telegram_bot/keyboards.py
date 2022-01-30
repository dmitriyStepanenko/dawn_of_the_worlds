from aiogram import types


def get_one_button_keyboard(text: str, callback_data: str):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(text=text, callback_data=callback_data))
    return keyboard
