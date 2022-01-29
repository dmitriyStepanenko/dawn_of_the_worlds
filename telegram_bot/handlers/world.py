from typing import Union

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram import types, Dispatcher


from telegram_bot.utils import convert_image, get_controller, is_user_admin, is_admin_state
from telegram_bot.keyboards import get_one_button_keyboard
from world_creator.controller import Controller
from world_creator.model import MAX_SIZE_LAYER


MAX_WORLD_NAME_LEN = 30

CMD_WORLD_INFO = 'world_info'

CB_RENDER_WORLD_MAP = 'render_world_map'
CB_CREATE_WORLD = 'create_world'
CB_DELETE_WORLD = 'delete_world'
CB_FILL_LANDS = 'fill_lands_'


def register_handlers_world_creation(db: Dispatcher):
    db.register_message_handler(cmd_get_world, commands=[CMD_WORLD_INFO], state='*')

    db.register_callback_query_handler(render_world_map_callback, text=CB_RENDER_WORLD_MAP, state='*')

    WorldDeletionOrder().register(db)
    WorldCreationOrder().register(db)


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
        controller = get_controller(call)
        if get_controller(call).is_world_created:
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

        controller = get_controller(call)
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
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        is_admin = await is_user_admin(message_or_call)
        if is_admin:
            admin_buttons = [
                types.InlineKeyboardButton(text="Удалить мир", callback_data=CB_DELETE_WORLD)
            ]
            keyboard.add(*admin_buttons)
        return keyboard

    async def render_world_info(
            self,
            message_or_call: Union[types.Message, types.CallbackQuery],
            controller: Controller
    ):
        keyboard = await self.get_render_world_keyboard(message_or_call)
        await self.render.set()
        if isinstance(message_or_call, types.Message):
            await message_or_call.answer(
                controller.world.info,
                reply_markup=keyboard
            )
        elif isinstance(message_or_call, types.CallbackQuery):
            await message_or_call.message.answer(
                controller.world.info,
                reply_markup=keyboard
            )
            await message_or_call.answer()
        else:
            raise NotImplementedError


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
    controller = get_controller(message)
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
        controller = get_controller(call)
        if not controller.is_world_created:
            await create_world(call.message)
        else:
            await self.clear.set()
            await call.message.answer('подтвердите удаление мира: да / нет')
        await call.answer()

    @staticmethod
    async def world_deleted(message: types.Message, state: FSMContext):
        if message.text == 'да':
            controller = get_controller(message)
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
    controller = get_controller(call)
    if controller.is_world_created:
        image = controller.world_manager.render_map()
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
