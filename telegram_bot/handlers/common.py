from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from telegram_bot.keyboards import get_one_button_keyboard
from telegram_bot.utils import get_controller

CMD_CANCEL = 'cancel'


def register_last_handlers(dispatcher: Dispatcher):
    dispatcher.register_callback_query_handler(no_state_callback, state='*')


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_cancel, commands=CMD_CANCEL, state="*")
    dp.register_message_handler(cmd_cancel, Text(equals="отмена", ignore_case=True), state="*")

# todo help command


async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    # todo
    await message.answer(
        "Привет! Я бот для игры 'Рассвет миров'! \n Для начала создайте мир:",
        reply_markup=get_one_button_keyboard('Создать мир', 'create_world'),
    )


async def cmd_cancel(message: types.Message, state: FSMContext):
    controller = get_controller(message)
    if controller.is_allowed_to_act():
        controller.remove_redactor_god()
    await state.finish()
    await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


async def no_state_callback(call: types.CallbackQuery, state: FSMContext):

    await call.answer('Это не твоя кнопка, найди себе другую)')
