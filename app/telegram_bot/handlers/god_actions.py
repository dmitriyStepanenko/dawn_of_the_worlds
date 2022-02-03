from typing import Union

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton as Button

from app.telegram_bot.utils import (
    get_god_controller,
    get_race_controller,
    get_god_action_controller,
    convert_image,
    remove_buttons_from_current_message_with_buttons,
    is_position_incorrect
)
from app.world_creator.controller import GodActionController

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
CB_CONTROL_RACE = 'control_race'
CB_CHOOSE_RACE_FRACTION = 'choose_race_fraction'
CB_CREATE_CITY = 'create_city'

CB_CHANGE_RACE_ALIGNMENT = 'change_race_alignment'

CB_EVENT = 'event'
CB_EVENT_POSITION = 'event_position'

MAX_NAME_LEN = 30
MAX_RACE_DESCRIPTION_LEN = 500
MAX_EVENT_DESCRIPTION_LEN = 200


def register_handlers_god_actions(dispatcher: Dispatcher):

    GodActionOrder().register(dispatcher)

    register_order_form_land(dispatcher)
    register_order_form_climate(dispatcher)

    RaceCreationOrder().register(dispatcher)

    ChangeRaceAlignmentOrder().register(dispatcher)

    EventCreationOrder().register(dispatcher)

    RaceControlOrder().register(dispatcher)
    CityCreationOrder().register(dispatcher)


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
        layer_name=LayerName.LANDS,
        tile_type_keyboard=keyboard,
        form_tile_function=GodActionController.form_land
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
        layer_name=LayerName.CLIMATE,
        tile_type_keyboard=keyboard,
        form_tile_function=GodActionController.form_climate
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
        controller = get_god_controller(call)
        controller.next_redactor_god()
        await call.message.edit_reply_markup(None)
        await state.finish()
        await call.answer()

    @staticmethod
    async def end_round_callback(call: types.CallbackQuery):
        await _end_round_answer(call)

    @staticmethod
    async def end_era_callback(call: types.CallbackQuery):
        controller = get_god_controller(call)
        controller.end_era()
        await call.answer()

    @staticmethod
    async def spend_force_callback(call: types.CallbackQuery):
        controller = get_god_controller(call)
        allowed_actions = controller.collect_allowed_actions()
        n_era = controller.world.n_era

        action_text_cb = [
            (Actions.CREATE_LAND, 'Формировать землю', CB_FORM_LAND),
            (Actions.CREATE_CLIMATE, 'Формировать климат', CB_FORM_CLIMATE),
            (Actions.CREATE_RACE, 'Создать расу', CB_CREATE_RACE),
            (Actions.INCREASE_REALM_ALIGNMENT, 'Очистить расу', CB_CHANGE_RACE_ALIGNMENT+'_+'),
            (Actions.DECREASE_REALM_ALIGNMENT, 'Совратить расу', CB_CHANGE_RACE_ALIGNMENT + '_-'),
            (Actions.EVENT, 'Событие', CB_EVENT),
            (Actions.CONTROL_RACE, 'Управлять расой', CB_CONTROL_RACE),
        ]
        buttons_by_actions = {
            action.name: Button(text=f"{text} ({action.value.costs[n_era]} БС)", callback_data=cb)
            for action, text, cb in action_text_cb
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

    def __init__(self, cb_start, layer_name: LayerName, tile_type_keyboard, form_tile_function):
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
            photo=convert_image(get_god_controller(call).render_map(self.LAYER_NAME.value)),
            caption=f'Введите номер тайла, где вы хотите {button_text}',
            reply=False,
        )
        await call.answer()

    async def choose_coord(self, message: types.Message, state: FSMContext):
        is_incorrect = await is_position_incorrect(message, self.LAYER_NAME)
        if is_incorrect:
            return

        await state.update_data(tile_num=int(message.text))
        await self.tile_type.set()
        await message.answer('Выберите тип тайла:', reply_markup=self.tile_type_keyboard)

    async def choose_tile_type_callback(self, call: types.CallbackQuery, state: FSMContext):
        land_type_str = call.data.split('_')[-1]
        user_data = await state.get_data()

        controller = get_god_action_controller(call)
        self.form_tile_function(controller, land_type_str, user_data["tile_num"])

        await call.message.reply_photo(
            photo=convert_image(controller.render_map(self.LAYER_NAME.value)),
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
        if len(message.text) > MAX_NAME_LEN:
            await message.answer(f'Название расы не может быть длиннее {MAX_NAME_LEN} символов')
            return
        controller = get_race_controller(message)
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
            convert_image(get_god_controller(message).render_map(LayerName.RACE.value)),
            caption=f'Введите номер тайла, где "{race_name}" появятся в мире',
            reply=False
        )
        await state.update_data(race_description=message.text)
        await self.init_position.set()

    async def set_init_position(self, message: types.Message, state: FSMContext):
        is_incorrect = await is_position_incorrect(message, LayerName.RACE)
        if is_incorrect:
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
        controller = get_race_controller(call)
        user_data = await state.get_data()
        controller.create_race(
            name=user_data['race_name'],
            description=user_data['race_description'],
            init_position=user_data['init_position'],
            alignment=alignment_by_sign[sign],
        )
        await _finalize_god_action(call, state)


class ChangeRaceAlignmentOrder(StatesGroup):
    race = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.choose_race, Text(startswith=CB_CHANGE_RACE_ALIGNMENT+'_'), state=GodActionOrder.act,
        )
        dispatcher.register_callback_query_handler(
            self.change_race_alignment, Text(startswith=CB_CHANGE_RACE_ALIGNMENT+'_'), state=self.race,
        )

    async def choose_race(self, call: types.CallbackQuery, state: FSMContext):
        sing = call.data.split('_')[-1]
        await state.update_data(race_alignment={'+': 1, '-': -1}.get(sing))
        controller = get_race_controller(call)
        buttons = [
            Button(text=f'{name} ({alignment})', callback_data=f'{CB_CHANGE_RACE_ALIGNMENT}_{name}')
            for name, alignment in controller.get_race_names_and_alignments()
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text(
            'Выберите расу',
            reply_markup=keyboard
        )
        await self.race.set()

    @staticmethod
    async def change_race_alignment(call: types.CallbackQuery, state: FSMContext):
        race_name = call.data.split('_')[-1]
        user_data = await state.get_data()
        controller = get_race_controller(call)
        controller.change_race_alignment(race_name, user_data['race_alignment'])
        await _finalize_god_action(call, state)


class EventCreationOrder(StatesGroup):
    description = State()
    yes_no_position = State()
    position = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.start_callback, text=CB_EVENT, state=GodActionOrder.act,
        )
        dispatcher.register_message_handler(
            self.set_description, state=self.description,
        )
        dispatcher.register_callback_query_handler(
            self.ask_position, Text(startswith=CB_EVENT_POSITION+'_'), state=self.yes_no_position,
        )
        dispatcher.register_message_handler(
            self.set_position, state=self.position
        )

    async def start_callback(self, call: types.CallbackQuery):
        await call.message.edit_text("Введите описание события", reply_markup=None)
        await call.answer()
        await self.description.set()

    async def set_description(self, message: types.Message, state: FSMContext):
        if len(message.text) > MAX_EVENT_DESCRIPTION_LEN:
            await message.answer(f'Длина описания события не должна превышать {MAX_EVENT_DESCRIPTION_LEN} символов')
            return

        await state.update_data(event_description=message.text)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*[
            Button(text="Да", callback_data=CB_EVENT_POSITION+'_+'),
            Button(text="Нет", callback_data=CB_EVENT_POSITION+'_-')
        ])
        await message.answer('Событие локализовано в какой-то области мира?', reply_markup=keyboard)
        await self.yes_no_position.set()

    async def ask_position(self, call: types.CallbackQuery, state: FSMContext):
        sign = call.data.split('_')[-1]
        controller = get_god_action_controller(call)
        if sign == '+':
            await call.message.reply_photo(
                convert_image(controller.render_map(LayerName.EVENT.value)),
                caption="Введите номер тайла, где совершиться событие",
                reply=False,
            )
            await self.position.set()
            await call.message.delete()
        else:
            user_data = await state.get_data()
            controller.create_event(description=user_data.get('event_description'))
            await _finalize_god_action(call, state)

    @staticmethod
    async def set_position(message: types.Message, state: FSMContext):
        is_incorrect = await is_position_incorrect(message, LayerName.EVENT)
        if is_incorrect:
            return

        user_data = await state.get_data()
        controller = get_god_action_controller(message)
        controller.create_event(description=user_data.get('event_description'), position=int(message.text))
        await _finalize_god_action(message, state)


class RaceControlOrder(StatesGroup):
    race = State()
    fraction = State()
    action = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.start_callback, text=CB_CONTROL_RACE, state=GodActionOrder.act,
        )
        dispatcher.register_callback_query_handler(
            self.control_callback, Text(startswith=CB_CONTROL_RACE+'_'), state=self.race
        )
        dispatcher.register_callback_query_handler(
            self.set_fraction_callback, Text(startswith=CB_CHOOSE_RACE_FRACTION+'_'), state=self.race
        )

    async def start_callback(self, call: types.CallbackQuery):
        controller = get_god_controller(call)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*[
            Button(text=race_name, callback_data=f"{CB_CONTROL_RACE}_{race_name}")
            for race_name in controller.get_controlled_race_names()
        ])
        await call.message.edit_text(
            'Выберите расу которой будете управлять:',
            reply_markup=keyboard
        )
        await self.race.set()

    async def control_callback(self, call: types.CallbackQuery, state: FSMContext):
        race_name = call.data.split('_')[-1]
        controller = get_race_controller(call)
        fraction_names = controller.get_race_fraction_names(race_name)
        if len(fraction_names) == 1:
            await self.set_fraction_callback(call, state)
            await state.update_data(fraction_name=fraction_names[0])
        else:
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            keyboard.add(*[
                Button(text=name, callback_data=f'{CB_CHOOSE_RACE_FRACTION}_{name}')
                for name in fraction_names
            ])
            await call.message.edit_text(
                'Выберите орден:',
                reply_markup=keyboard
            )

        await state.update_data(race_name=race_name)

    async def set_fraction_callback(self, call: types.CallbackQuery, state: FSMContext):
        fraction_name = call.data.split('_')[-1]
        await state.update_data(fraction_name=fraction_name)

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*[
            Button(text='Создать город', callback_data=CB_CREATE_CITY)
        ])
        await call.message.edit_text(
            'Выберите действие:',
            reply_markup=keyboard
        )
        await self.action.set()


class CityCreationOrder(StatesGroup):
    city_name = State()
    city_position = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.create_city_callback, text=CB_CREATE_CITY, state=RaceControlOrder.action
        )
        dispatcher.register_message_handler(
            self.set_city_name, state=self.city_name,
        )
        dispatcher.register_message_handler(
            self.set_city_position, state=self.city_position,
        )

    async def create_city_callback(self, call: types.CallbackQuery):
        await call.message.edit_text(
            'Введите название города',
            reply_markup=None
        )
        await self.city_name.set()

    async def set_city_name(self, message: types.Message, state: FSMContext):
        if len(message.text) > MAX_NAME_LEN:
            await message.answer(f"Название города не может быть больше {MAX_NAME_LEN} символов")
            return
        await state.update_data(city_name=message.text)
        await self.city_position.set()
        await message.reply_photo(
            convert_image(get_race_controller(message).render_map(LayerName.RACE.name)),
            caption=f'Введите номер тайла, где будет размещен город "{message.text}"',
            reply=False
        )

    @staticmethod
    async def set_city_position(message: types.Message, state: FSMContext):
        is_incorrect = await is_position_incorrect(message, LayerName.RACE)
        if is_incorrect:
            return

        user_data = await state.get_data()
        controller = get_race_controller(message)
        controller.create_city(
            race_name=user_data.get('race_name'),
            city_name=user_data.get('city_name'),
            position=int(message.text),
            fraction_name=user_data.get('fraction_name'),
        )

        await _finalize_god_action(message, state)


async def render_god_info(message: types.Message):
    controller = get_god_controller(message)
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
    controller = get_god_controller(call_or_message)
    n_round = controller.world.n_round
    n_era = controller.world.n_era
    controller.next_redactor_god()
    controller.end_round()

    message = call_or_message if isinstance(call_or_message, types.Message) else call_or_message.message

    state = Dispatcher.get_current().current_state()
    await state.finish()
    if controller.is_creation_end:
        await message.answer('Мир создан')
    elif n_round < controller.world.n_round:
        await message.answer('Начался новый раунд, боги получили силу, мир стал старше')
    elif n_era < controller.world.n_era:
        await message.answer('Началась новая эпоха, время теперь течет быстрее')
    if isinstance(call_or_message, types.CallbackQuery):
        await call_or_message.message.edit_reply_markup(None)
        await call_or_message.answer()


async def _finalize_god_action(
        call_or_message: Union[types.Message, types.CallbackQuery],
        state: FSMContext
):
    """Надо вызывать в конце каждого божественного действия"""
    await state.finish()
    if isinstance(call_or_message, types.CallbackQuery):
        await call_or_message.answer()
        call_or_message.message.from_user = call_or_message.from_user
        await call_or_message.message.delete()
        message = call_or_message.message
    elif isinstance(call_or_message, types.Message):
        message = call_or_message
    else:
        raise NotImplementedError
    await render_god_info(message)
