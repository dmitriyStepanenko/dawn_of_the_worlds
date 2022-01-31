from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton as Button

from app.telegram_bot.keyboards import get_one_button_keyboard
from app.telegram_bot.utils import get_controller, convert_image, remove_buttons_from_current_message_with_buttons
from app.world_creator.controller import Controller

from app.world_creator.tiles import LandType
from app.world_creator.tiles import ClimateType
from app.world_creator.model import Actions, LayerName

CB_END_ACTION = 'end_action'
CB_SPEND_FORCE = 'spend_force'
CB_FORM_LAND = 'form_land'
CB_FORM_CLIMATE = 'form_climate'
CB_END_ROUND = 'end_round'
CB_END_ERA = 'end_era'

CB_CREATE_RACE = 'create_race'
CB_CREATE_SUBRACE = 'create_subrace'
CB_SET_START_ALIGNMENT = 'set_start_alignment'


MAX_RACE_NAME_LEN = 30
MAX_RACE_DESCRIPTION_LEN = 500


def register_handlers_god_actions(dispatcher: Dispatcher):

    GodActionOrder().register(dispatcher)

    register_order_form_land(dispatcher)
    register_order_form_climate(dispatcher)

    RaceCreationOrder().register(dispatcher)


def register_order_form_land(dispatcher: Dispatcher):
    buttons = [
        Button(text="Лес", callback_data=f"{CB_FORM_LAND}_{LandType.FOREST.value}"),
        Button(text="Горы", callback_data=f"{CB_FORM_LAND}_{LandType.ROCK.value}"),
        Button(text="Плато", callback_data=f"{CB_FORM_LAND}_{LandType.PLATEAU.value}"),
        Button(text="Вода", callback_data=f"{CB_FORM_LAND}_{LandType.WATER.value}"),
        Button(text="Песок", callback_data=f"{CB_FORM_LAND}_{LandType.SAND.value}"),
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    order_form_land = AddTileOrder(
        cb_start=CB_FORM_LAND,
        layer_name=LayerName.LANDS.value,
        tile_type_keyboard=keyboard,
        form_tile_function=Controller.form_land
    )

    order_form_land.register(dispatcher)


def register_order_form_climate(dispatcher: Dispatcher):
    base_cb = CB_FORM_CLIMATE
    buttons = [
        Button(text="Дождь", callback_data=f"{base_cb}_{ClimateType.RAIN.value}"),
        Button(text="Снег", callback_data=f"{base_cb}_{ClimateType.SNOW.value}"),
        Button(text="Туман", callback_data=f"{base_cb}_{ClimateType.CLOUD.value}"),
        Button(text="Ясно", callback_data=f"{base_cb}_{ClimateType.CLEAR.value}"),
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    order_form_climate = AddTileOrder(
        cb_start=base_cb,
        layer_name=LayerName.CLIMATE.value,
        tile_type_keyboard=keyboard,
        form_tile_function=Controller.form_climate
    )

    order_form_climate.register(dispatcher)


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
    async def end_round_callback(call: types.CallbackQuery):
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
            Actions.CREATE_LAND.name: Button(text="Формировать землю", callback_data=CB_FORM_LAND),
            Actions.CREATE_CLIMATE.name: Button(text="Формировать климат", callback_data=CB_FORM_CLIMATE),
            Actions.CREATE_RACE.name: Button(text="Создать расу", callback_data=CB_CREATE_RACE)
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


class AddTileOrder(StatesGroup):
    coord = State()
    tile_type = State()

    def __init__(self, cb_start, layer_name, tile_type_keyboard, form_tile_function):
        self.CB_START = cb_start
        self.LAYER_NAME = layer_name
        self.tile_type_keyboard = tile_type_keyboard
        self.form_tile_function = form_tile_function
        self.coord = State('coord' + cb_start)

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.start_callback, text=self.CB_START, state=GodActionOrder.act
        )
        dispatcher.register_message_handler(
            self.choose_coord, state=self.coord
        )
        dispatcher.register_callback_query_handler(
            self.choose_tile_type_callback, Text(startswith=self.CB_START+'_'), state=self.tile_type
        )

    async def start_callback(self, call: types.CallbackQuery):
        button_text = 'разместить тайл'
        for row_buttons in call.message.reply_markup.inline_keyboard:
            for button in row_buttons:
                if button.callback_data == call.data:
                    button_text = button.text

        await self.coord.set()
        await call.message.delete()
        await call.message.reply_photo(
            photo=convert_image(get_controller(call).render_map(self.LAYER_NAME)),
            caption=f'Введите номер тайла, где вы хотите {button_text}',
            reply=False,
        )
        await call.answer()

    async def choose_coord(self, message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer('Номер тайла должен быть число')
            return
        tile_num = int(message.text)

        controller = get_controller(message)
        max_num = controller.world.layers[self.LAYER_NAME].num_tiles
        if max_num < tile_num < 0:
            await message.answer(f'Номер тайла не может превышать {max_num}')
            return

        await state.update_data(tile_num=int(message.text))
        await self.tile_type.set()
        await message.answer('Выберите тип тайла:', reply_markup=self.tile_type_keyboard)

    async def choose_tile_type_callback(self, call: types.CallbackQuery, state: FSMContext):
        land_type_str = call.data.split('_')[-1]
        user_data = await state.get_data()

        controller = get_controller(call)
        self.form_tile_function(controller, land_type_str, user_data["tile_num"])

        await call.message.reply_photo(
            photo=convert_image(get_controller(call).render_map(self.LAYER_NAME)),
            caption=f'Тайл {user_data["tile_num"]} изменен',
            reply=False,
        )
        await _finalize_god_action(call, state)


class RaceCreationOrder(StatesGroup):
    name = State()
    description = State()
    init_position = State()
    alignment = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.create_race_callback, text=CB_CREATE_RACE, state=GodActionOrder.act
        )
        dispatcher.register_message_handler(
            self.set_name, state=self.name,
        )
        dispatcher.register_message_handler(
            self.set_description, state=self.description,
        )
        dispatcher.register_message_handler(
            self.set_init_position, state=self.init_position,
        )
        dispatcher.register_callback_query_handler(
            self.set_alignment, Text(startswith=CB_SET_START_ALIGNMENT+'_'), state=self.alignment,
        )

    async def create_race_callback(self, call: types.CallbackQuery):
        await self.name.set()
        await call.message.edit_text('Введите название расы', reply_markup=None)
        await call.answer()

    async def set_name(self, message: types.Message, state: FSMContext):
        if len(message.text) > MAX_RACE_NAME_LEN:
            await message.answer(f'Название расы не может быть длиннее {MAX_RACE_NAME_LEN} символов')
            return
        controller = get_controller(message)
        if controller.is_race_exist(message.text):
            await message.answer('Раса с таким названием уже существует, введите другое')
            return
        await message.answer(f'Введите описание расы "{message.text}"')
        await state.update_data(race_name=message.text)
        await self.description.set()

    async def set_description(self, message: types.Message, state: FSMContext):
        if len(message.text) > MAX_RACE_DESCRIPTION_LEN:
            await message.answer(f'Описание расы не может быть длиннее {MAX_RACE_DESCRIPTION_LEN} символов')
            return
        user_data = await state.get_data()
        race_name = user_data.get('race_name')
        await message.reply_photo(
            convert_image(get_controller(message).render_map(LayerName.RACE.value)),
            caption=f'Введите номер тайла, где "{race_name}" появятся в мире',
            reply=False
        )
        await state.update_data(race_description=message.text)
        await self.init_position.set()

    async def set_init_position(self, message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer('Номер тайла должен быть числом')
            return
        controller = get_controller(message)
        num_tiles = controller.world.layers[LayerName.RACE.value].num_tiles
        if num_tiles < int(message.text) < 0:
            await message.answer(f'Номер тайла не должен превышать {num_tiles}')
            return

        buttons = [
            Button(text=" +1 ", callback_data=CB_SET_START_ALIGNMENT+'_+'),
            Button(text="  0 ", callback_data=CB_SET_START_ALIGNMENT+'_0'),
            Button(text=" -1 ", callback_data=CB_SET_START_ALIGNMENT+'_-'),
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        keyboard.add(*buttons)
        user_data = await state.get_data()
        race_name = user_data.get('race_name')
        await message.answer(
            f'Выберете элаймент расы "{race_name}"',
            reply_markup=keyboard
        )
        await state.update_data(init_position=int(message.text))
        await self.alignment.set()

    @staticmethod
    async def set_alignment(call: types.CallbackQuery, state: FSMContext):
        sign = call.data.split('_')[-1]
        alignment_by_sign = {'+': 1, '0': 0, '-': -1}
        controller = get_controller(call)
        user_data = await state.get_data()
        controller.create_race(
            name=user_data['race_name'],
            description=user_data['race_description'],
            init_position=user_data['init_position'],
            alignment=alignment_by_sign[sign],
        )
        await _finalize_god_action(call, state)


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
                Button(text="Потратить силу", callback_data=CB_SPEND_FORCE),
                Button(text="Завершить ход", callback_data=CB_END_ACTION),
                Button(text="Завершить раунд", callback_data=CB_END_ROUND),
            ]
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            if controller.is_allowed_to_end_era:
                buttons.append(Button(text="Завершить эпоху", callback_data=CB_END_ERA))
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


async def _finalize_god_action(call: types.CallbackQuery, state: FSMContext):
    """Надо вызывать в конце каждого божественного действия"""
    await state.finish()
    await call.answer()
    call.message.from_user = call.from_user
    await render_god_info(call.message)
    await call.message.delete()