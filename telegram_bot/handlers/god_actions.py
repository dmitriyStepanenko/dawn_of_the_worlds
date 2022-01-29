from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State

from telegram_bot.utils import get_controller, convert_image, remove_buttons_from_current_message_with_buttons

from world_creator.tiles import LandType
from world_creator.model import Actions

CB_END_ACTION = 'end_action'
CB_SPEND_FORCE = 'spend_force'
CB_FORM_LAND = 'form_land'
CB_END_ROUND = 'end_round'
CB_END_ERA = 'end_era'


def register_handlers_god_actions(dispatcher: Dispatcher):

    GodActionOrder().register(dispatcher)

    OrderFormLand().register(dispatcher)


class GodActionOrder(StatesGroup):
    act = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.spend_force_callback, text=CB_SPEND_FORCE, state=self.act
        )
        dispatcher.register_callback_query_handler(
            self.end_action_callback, text=CB_END_ACTION, state=self.act
        )
        dispatcher.register_callback_query_handler(
            self.end_round_callback, text=CB_END_ROUND, state=self.act
        )
        dispatcher.register_callback_query_handler(
            self.end_era_callback, text=CB_END_ERA, state=self.act
        )

    @staticmethod
    async def end_action_callback(call: types.CallbackQuery, state: FSMContext):
        controller = get_controller(call)
        controller.next_redactor_god()
        await call.message.edit_reply_markup(None)
        await state.finish()
        await call.answer()

    @staticmethod
    async def end_round_callback(call: types.CallbackQuery, state: FSMContext):
        await _end_round_answer(call)

    @staticmethod
    async def end_era_callback(call: types.CallbackQuery):
        controller = get_controller(call)
        controller.end_era()
        await call.answer()

    @staticmethod
    async def spend_force_callback(call: types.CallbackQuery):
        controller = get_controller(call)
        allowed_actions = controller.collect_allowed_actions()
        buttons_by_actions = {
            Actions.CREATE_LAND.name: types.InlineKeyboardButton(text="Формировать землю", callback_data=CB_FORM_LAND)
        }

        buttons = []
        for action in allowed_actions:
            button = buttons_by_actions.get(action)
            if button:
                buttons.append(button)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)

        await call.message.edit_text(
            f'Бог: {controller.current_god.name}\n'
            f'Божественная сила: {controller.current_god.value_force}\n'
            f'Доступные действия:\n',
            reply_markup=keyboard,
        )
        await call.answer()


class OrderFormLand(StatesGroup):
    coord = State()
    land_type = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.form_land_callback, text=CB_FORM_LAND, state=GodActionOrder.act
        )
        dispatcher.register_message_handler(
            self.choose_coord, state=self.coord
        )
        dispatcher.register_callback_query_handler(
            self.choose_type_land_callback, Text(startswith=CB_FORM_LAND+'_'), state=self.land_type
        )

    async def form_land_callback(self, call: types.CallbackQuery):
        await self.coord.set()
        await call.message.delete()
        await call.message.reply_photo(
            photo=convert_image(get_controller(call).world_manager.render_map()),
            caption='Введите номер тайла, где вы хотите "Формировать землю"',
            reply=False,
        )
        await call.answer()

    async def choose_coord(self, message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer('Номер тайла должен быть число')
            return
        tile_num = int(message.text)

        controller = get_controller(message)
        max_num = controller.world.layers['lands'].num_tiles
        if max_num < tile_num < 0:
            await message.answer(f'Номер тайла не может превышать {max_num}')
            return

        await state.update_data(tile_num=int(message.text))
        await self.next()
        buttons = [
            types.InlineKeyboardButton(text="Лес", callback_data=f"{CB_FORM_LAND}_{LandType.FOREST.value}"),
            types.InlineKeyboardButton(text="Горы", callback_data=f"{CB_FORM_LAND}_{LandType.ROCK.value}"),
            types.InlineKeyboardButton(text="Плато", callback_data=f"{CB_FORM_LAND}_{LandType.PLATEAU.value}"),
            types.InlineKeyboardButton(text="Вода", callback_data=f"{CB_FORM_LAND}_{LandType.WATER.value}"),
            types.InlineKeyboardButton(text="Песок", callback_data=f"{CB_FORM_LAND}_{LandType.SAND.value}"),
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await message.answer('Выберите тип ландшафта:', reply_markup=keyboard)

    @staticmethod
    async def choose_type_land_callback(call: types.CallbackQuery, state: FSMContext):
        land_type_str = call.data.split('_')[-1]
        user_data = await state.get_data()

        controller = get_controller(call)
        controller.form_land(land_type_str, user_data["tile_num"])

        await call.message.reply_photo(
            photo=convert_image(get_controller(call).world_manager.render_map()),
            caption='Ландшафт изменен',
            reply=False,
        )
        await call.answer()
        call.message.from_user = call.from_user
        await render_god_info(call.message)
        await call.message.delete()


async def render_god_info(message: types.Message):
    controller = get_controller(message)
    keyboard = None
    if controller.is_allowed_to_act:
        if not controller.collect_allowed_actions():
            await _end_round_answer(message)
            return
        else:
            await remove_buttons_from_current_message_with_buttons(message, controller)

            buttons = [
                types.InlineKeyboardButton(text="Потратить силу", callback_data=CB_SPEND_FORCE),
                types.InlineKeyboardButton(text="Завершить ход", callback_data=CB_END_ACTION),
                types.InlineKeyboardButton(text="Завершить раунд", callback_data=CB_END_ROUND),
            ]
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            if controller.is_allowed_to_end_era:
                buttons.append(types.InlineKeyboardButton(text="Завершить эпоху", callback_data=CB_END_ERA))
            keyboard.add(*buttons)
            await GodActionOrder.act.set()

    message_text = controller.current_god.info
    if not controller.world.is_start_game:
        message_text += '\n Действия будут доступны после того как администратор начнет игру'

    answer = await message.answer(
        message_text,
        reply_markup=keyboard
    )
    controller.set_current_message_id(answer.message_id)


async def _end_round_answer(call_or_message: Union[types.Message, types.CallbackQuery]):
    controller = get_controller(call_or_message)
    n_round = controller.world.n_round
    n_era = controller.world.n_era
    controller.next_redactor_god()
    controller.end_round()

    message = call_or_message if isinstance(call_or_message, types.Message) else call_or_message.message

    state = Dispatcher.get_current().current_state()
    await state.finish()
    if controller.world_manager.is_creation_end:
        await message.answer('Мир создан')
    elif n_round < controller.world.n_round:
        await message.answer('Начался новый раунд, боги получили силу, мир стал старше')
    elif n_era < controller.world.n_era:
        await message.answer('Началась новая эпоха, время теперь течет быстрее')
    if isinstance(call_or_message, types.CallbackQuery):
        await call_or_message.message.edit_reply_markup(None)
        await call_or_message.answer()
