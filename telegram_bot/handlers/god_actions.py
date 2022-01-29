from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State

from telegram_bot.utils import get_controller, convert_image, get_god_name_from_message

from world_creator.controller import Controller
from world_creator.tiles import LandType
from world_creator.model import Actions

CB_START_ACTION = 'start_action'
CB_END_ACTION = 'end_action'
CB_SPEND_FORCE = 'spend_force'
CB_FORM_LAND = 'form_land'
CB_END_ROUND = 'end_round'
CB_END_ERA = 'end_era'


def register_handlers_god_actions(dispatcher: Dispatcher):

    GodActionOrder().register(dispatcher)

    OrderFormLand().register(dispatcher)


class GodActionOrder(StatesGroup):
    start = State()
    act = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.start_action_callback, text=CB_START_ACTION, state=self.start
        )
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

    async def start_action_callback(self, call: types.CallbackQuery):
        controller = get_controller(call)
        god_name = get_god_name_from_message(call.message)
        if god_name != controller.current_god.name:
            await call.answer('Эта кнопка управляет чужим богом, найдите вашу или заведите новую')
            return
        if controller.is_allowed_to_act():
            controller.set_redactor_god()
            # сброс состояний всем богам кроме текущего
            await remove_all_god_action_states(call)

            buttons = [
                types.InlineKeyboardButton(text="Потратить силу", callback_data=CB_SPEND_FORCE),
                types.InlineKeyboardButton(text="Завершить ход", callback_data=CB_END_ACTION),
                types.InlineKeyboardButton(text="Завершить раунд", callback_data=CB_END_ROUND),
            ]
            keyboard = types.InlineKeyboardMarkup(row_width=1)
            if controller.world.n_round > 4 and not controller.current_god.confirm_end_era:
                buttons.append(types.InlineKeyboardButton(text="Завершить эпоху", callback_data=CB_END_ERA))
            keyboard.add(*buttons)
            await self.act.set()
            await call.message.edit_reply_markup(keyboard)
            await call.answer()
        else:
            await call.message.edit_reply_markup(None)
            await call.answer('Сейчас чужой ход')

    @staticmethod
    async def end_action_callback(call: types.CallbackQuery, state: FSMContext):
        controller = get_controller(call)
        controller.remove_redactor_god()
        await call.message.edit_reply_markup(None)
        await state.finish()
        await call.answer()

    @staticmethod
    async def end_round_callback(call: types.CallbackQuery, state: FSMContext):
        controller = get_controller(call)
        n_round = controller.world.n_round
        n_era = controller.world.n_era
        controller.end_round()
        controller.remove_redactor_god()

        await call.message.edit_reply_markup(None)
        await state.finish()
        if controller.world_manager.is_creation_end:
            await call.message.answer('Мир создан')
        elif n_round < controller.world.n_round:
            await call.message.answer('Начался новый раунд, боги получили силу, мир стал старше')
        elif n_era < controller.world.n_era:
            await call.message.answer('Началась новая эпоха, время теперь течет быстрее')
        await call.answer()

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
        shape = controller.world.layers['lands'].shape
        max_num = shape[0] * shape[1]
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

        await call.message.delete()
        message = await call.message.reply_photo(
            photo=convert_image(get_controller(call).world_manager.render_map()),
            caption='Ландшафт изменен',
            reply=False,
        )
        await call.answer()
        call.message = message
        await GodActionOrder().start_action_callback(call)


async def remove_all_god_action_states(call):
    controller = get_controller(call)
    for god_id in controller.world.gods:
        if god_id == call.from_user.id:
            continue
        state = await Dispatcher.get_current().current_state(user=god_id).get_state()
        if state in [GodActionOrder.start.state, GodActionOrder.act.state]:
            await Dispatcher.get_current().current_state(user=god_id).set_state()