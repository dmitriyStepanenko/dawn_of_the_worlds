import asyncio
import os

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.telegram_bot.handlers.god_creation import register_handlers_god_creation, CMD_GOD_INFO
from app.telegram_bot.handlers.god_actions import register_handlers_god_actions
from app.telegram_bot.handlers.world import register_handlers_world_creation, CMD_WORLD_INFO
from app.telegram_bot.handlers.common import register_handlers_common, register_last_handlers, CMD_CANCEL


BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    exit("Error: no token provided")


# Регистрация команд, отображаемых в интерфейсе Telegram
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/" + CMD_WORLD_INFO, description="Инфо о мире"),
        BotCommand(command="/" + CMD_GOD_INFO, description="Инфо о вашем боге"),
        BotCommand(command="/" + CMD_CANCEL, description="Отменить текущее действие")
    ]
    await bot.set_my_commands(commands)


async def main():
    bot = Bot(token=BOT_TOKEN)
    db = Dispatcher(bot=bot, storage=MemoryStorage())

    register_handlers_common(db)
    register_handlers_world_creation(db)
    register_handlers_god_creation(db)
    register_handlers_god_actions(db)
    register_last_handlers(db)

    await set_commands(bot)

    await db.skip_updates()
    await db.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
