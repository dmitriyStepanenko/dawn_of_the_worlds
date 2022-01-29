from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from telegram_bot.keyboards import get_one_button_keyboard
from telegram_bot.handlers.world import CB_CREATE_WORLD
from telegram_bot.utils import get_controller

CMD_CANCEL = 'cancel'
CMD_START_BOT = 'start'
CMD_HELP = 'help'


def register_last_handlers(dispatcher: Dispatcher):
    dispatcher.register_callback_query_handler(no_state_callback, state='*')


def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=CMD_START_BOT, state="*")
    dp.register_message_handler(cmd_help, commands=CMD_HELP, state="*")
    dp.register_message_handler(cmd_cancel, commands=CMD_CANCEL, state="*")
    dp.register_message_handler(cmd_cancel, Text(equals="отмена", ignore_case=True), state="*")


async def cmd_help(message: types.Message):
    # todo help
    await message.answer('Здесь будет информация о том как играть. И ссылка на правила.')


async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    if not get_controller(message).is_world_created:
        await message.answer(
            "Привет! Я бот для игры 'Рассвет миров'! \n Для начала создайте мир:",
            reply_markup=get_one_button_keyboard('Создать мир', CB_CREATE_WORLD),
        )
    else:
        await message.answer("Наслаждайтесь игрой в 'Рассвет миров'")


async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await message.answer("Действие отменено", reply_markup=types.ReplyKeyboardRemove())


async def no_state_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer('Это не ваша кнопка, поищите себе другую)')
