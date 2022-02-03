from typing import Union

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram import types, Dispatcher


from app.telegram_bot.utils import convert_image, is_user_admin, is_admin_state, convert_text, get_world_controller
from app.telegram_bot.keyboards import get_one_button_keyboard
from app.world_creator.controller.controller import Controller
from app.world_creator.model import MAX_SIZE_LAYER


MAX_WORLD_NAME_LEN = 30

CMD_WORLD_INFO = 'world_info'

CB_RENDER_WORLD_MAP = 'render_world_map'
CB_RENDER_WORLD_STORY = 'render_world_story'
CB_CREATE_WORLD = 'create_world'
CB_DELETE_WORLD = 'delete_world'
CB_FILL_LANDS = 'fill_lands_'
CB_START_GAME = 'start_game'


def register_handlers_world_creation(dispatcher: Dispatcher):
    dispatcher.register_message_handler(cmd_get_world, commands=[CMD_WORLD_INFO], state='*')

    dispatcher.register_callback_query_handler(start_game_callback, text=CB_START_GAME, state='*')
    dispatcher.register_callback_query_handler(render_world_map_callback, text=CB_RENDER_WORLD_MAP, state='*')
    dispatcher.register_callback_query_handler(render_world_story_callback, text=CB_RENDER_WORLD_STORY, state='*')

    WorldDeletionOrder().register(dispatcher)
    WorldCreationOrder().register(dispatcher)


class WorldCreationOrder(StatesGroup):
    start = State()
    name = State()
    size = State()
    fill = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_message_handler(self.set_world_name, state=self.name)
        dispatcher.register_message_handler(self.set_world_size, state=self.size)
        dispatcher.register_callback_query_handler(
            self.fill_world_callback,
            Text(startswith=CB_FILL_LANDS),
            state=self.fill,
        )

        dispatcher.register_callback_query_handler(self.create_world_callback, text=CB_CREATE_WORLD, state=self.start)

    async def create_world_callback(self, call: types.CallbackQuery, state: FSMContext):
        controller = get_world_controller(call)
        if controller.is_world_created:
            await call.message.edit_text('мир уже создан')
            await state.finish()
            await WorldRenderOrder().render_world_info(call.message, controller)
        else:
            await self.next()
            await call.message.edit_text('введите название мира')

        await call.answer()

    async def set_world_name(self, message: types.Message, state: FSMContext):
        if len(message.text) > MAX_WORLD_NAME_LEN:
            await message.answer(f'Название мира должно быть не больше {MAX_WORLD_NAME_LEN} символов')
            return

        await state.update_data(name=message.text, id_to_delete=[message.message_id])
        await self.next()
        await message.answer(f'введите размеры мира (два числа от 1 до {MAX_SIZE_LAYER} через пробел)')

    async def set_world_size(self, message: types.Message, state: FSMContext):
        args = message.text.split(' ')
        if len(args) != 2:
            await message.answer('введите пару чисел через пробел')
            return

        for arg in args:
            if not arg.isdecimal():
                await message.answer('введите пару чисел через пробел')
                return
            if MAX_SIZE_LAYER < int(arg) < 1:
                await message.answer(f'размеры должны быть в пределах от 1 до {MAX_SIZE_LAYER}')
                return

        await state.update_data(size=(int(args[0]), int(args[1])))
        await self.next()
        buttons = [
            types.InlineKeyboardButton(text=f"{i}%", callback_data=f"{CB_FILL_LANDS}{i}") for i in range(0, 101, 20)
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=6)
        keyboard.add(*buttons)
        await message.answer('Выберите процент суши в вашем мире:', reply_markup=keyboard)

    @staticmethod
    async def fill_world_callback(call: types.CallbackQuery, state: FSMContext):
        percent = int(call.data.split('_')[-1])
        user_data = await state.get_data()

        controller = get_world_controller(call)
        controller.create_world(name=user_data['name'], layers_shape=user_data['size'], percent=percent)
        await state.finish()
        await call.message.delete()
        await WorldRenderOrder().render_world_info(call, controller)
        await call.answer()


class WorldRenderOrder(StatesGroup):
    render = State()

    @staticmethod
    async def get_render_world_keyboard(message_or_call: Union[types.Message, types.CallbackQuery]):
        buttons = [
            types.InlineKeyboardButton(text="Показать карту", callback_data=CB_RENDER_WORLD_MAP),
            types.InlineKeyboardButton(text="Показать историю мира", callback_data=CB_RENDER_WORLD_STORY)
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        is_admin = await is_user_admin(message_or_call)
        if is_admin:
            admin_buttons = [
                types.InlineKeyboardButton(text="Удалить мир", callback_data=CB_DELETE_WORLD)
            ]
            if not get_world_controller(message_or_call).world.is_start_game:
                admin_buttons.append(types.InlineKeyboardButton(text="Начать игру", callback_data=CB_START_GAME))
            keyboard.add(*admin_buttons)
        return keyboard

    async def render_world_info(
            self,
            message_or_call: Union[types.Message, types.CallbackQuery],
            controller: Controller
    ):
        keyboard = await self.get_render_world_keyboard(message_or_call)
        await self.render.set()
        message = message_or_call if isinstance(message_or_call, types.Message) else message_or_call.message
        await message.answer(
            controller.world.info,
            reply_markup=keyboard
        )
        if isinstance(message_or_call, types.CallbackQuery):
            await message_or_call.answer()


async def create_world(message: types.Message):
    is_admin = await is_user_admin(message)
    if not is_admin:
        await message.answer('У вас недостаточно прав чтобы создать мир, попросите администратора', reply=True)
        return

    is_not_empty_admin_state = await is_admin_state(message)
    if is_not_empty_admin_state:
        await message.answer('Мир еще не создан, но кто-то уже создает мир')
        return

    await WorldCreationOrder.start.set()
    await message.answer(
        'Мир еще не создан',
        reply_markup=get_one_button_keyboard('Создать мир', CB_CREATE_WORLD),
    )


async def cmd_get_world(message: types.Message):
    controller = get_world_controller(message)
    if controller.is_world_created:
        await WorldRenderOrder().render_world_info(message, controller)
    else:
        await create_world(message)


class WorldDeletionOrder(StatesGroup):
    clear = State()

    def register(self, dispatcher: Dispatcher):
        dispatcher.register_callback_query_handler(
            self.clear_world_callback,
            text=CB_DELETE_WORLD,
            state=WorldRenderOrder.render
        )
        dispatcher.register_message_handler(self.world_deleted, state=self.clear)

    async def clear_world_callback(self, call: types.CallbackQuery):
        is_admin = await is_user_admin(call)
        if not is_admin:
            await call.answer('Эта кнопка для администратора')
            return

        controller = get_world_controller(call)
        if not controller.is_world_created:
            await create_world(call.message)
        else:
            await self.clear.set()
            await call.message.answer('подтвердите удаление мира: да / нет')
        await call.answer()

    @staticmethod
    async def world_deleted(message: types.Message, state: FSMContext):
        if message.text == 'да':
            controller = get_world_controller(message)
            controller.remove_world()
            await state.finish()
            await message.answer('мир удален')
            return
        elif message.text == 'нет':
            await state.finish()
            await message.answer('удаление мира отменено')
            return
        else:
            await message.answer('подтвердите удаление мира: да/нет')


async def render_world_map_callback(call: types.CallbackQuery):
    controller = get_world_controller(call)
    if controller.is_world_created:
        image = controller.render_map()
        await call.message.delete()
        await call.message.reply_photo(
            convert_image(image),
            caption=call.message.text,
            reply=False,
            reply_markup=await WorldRenderOrder().get_render_world_keyboard(call)
        )
    else:
        await create_world(call.message)

    await call.answer()


async def render_world_story_callback(call: types.CallbackQuery):
    controller = get_world_controller(call)
    if controller.is_world_created:
        story = controller.world_manager.render_story()
        document = convert_text(story)
        document.filename = f'История мира {controller.world.name}.txt'
        await call.message.delete()
        await call.message.reply_document(
            document,
            caption=call.message.text,
            reply=False,
            reply_markup=await WorldRenderOrder().get_render_world_keyboard(call)
        )
    else:
        await create_world(call.message)

    await call.answer()


async def start_game_callback(call: types.CallbackQuery):
    is_admin = await is_user_admin(call)
    if is_admin:
        get_world_controller(call).start_game()
        await call.message.edit_reply_markup(None)
        await call.answer()
    else:
        await call.answer('Эта кнопка для администратора')
