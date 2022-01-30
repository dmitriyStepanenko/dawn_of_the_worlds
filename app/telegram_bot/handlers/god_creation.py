import aiogram.utils.exceptions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram import types, Dispatcher

from app.telegram_bot.utils import get_controller
from app.telegram_bot.keyboards import get_one_button_keyboard
from app.telegram_bot.handlers.world import create_world
from app.telegram_bot.handlers.god_actions import render_god_info


MAX_GOD_NAME_LEN = 30

CMD_GOD_INFO = 'god_info'
CB_CREATE_GOD = 'create_god'


def register_handlers_god_creation(dispatcher: Dispatcher):
    dispatcher.register_message_handler(cmd_get_god, commands=[CMD_GOD_INFO], state='*')

    GodCreationOrder().register(dispatcher)


class GodCreationOrder(StatesGroup):
    start = State()
    name = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(self.create_god_callback, text=CB_CREATE_GOD, state=self.start)
        dispatcher.register_message_handler(self.set_god_name, state=self.name)

    async def create_god_callback(self, call: types.CallbackQuery):
        controller = get_controller(call)
        if not controller.is_world_created:
            await create_world(call.message)
            return

        if controller.current_god:
            await render_god_info(call.message)
            return

        await self.name.set()
        await call.message.edit_text('Введите имя бога')
        await call.answer()

    @staticmethod
    async def set_god_name(message: types.Message, state: FSMContext):
        if len(message.text) > MAX_GOD_NAME_LEN:
            await message.answer(f'Имя бога должно быть не больше {MAX_GOD_NAME_LEN} символов')
            return

        controller = get_controller(message)
        if not controller.add_god(message.text):
            await message.answer(f'Уже есть бог с именем {message.text}, выберите другое')
            return

        await state.finish()
        await render_god_info(message)


async def cmd_get_god(message: types.Message, state: FSMContext):
    controller = get_controller(message)
    if not controller.is_world_created:
        await create_world(message)
        return
    if not controller.current_god:
        if controller.world.is_start_game:
            await message.answer(
                'У вас нет бога. \n'
                'К сожалению, после начала игры нельзя создавать богов, '
                'дождитесь пока администраторы создадут новый мир и успейте до начала игры.')
            return

        await GodCreationOrder.start.set()
        await message.answer(
            'У вас еще нет бога.',
            reply_markup=get_one_button_keyboard('Создать бога', CB_CREATE_GOD)
        )
        return

    await render_god_info(message)




