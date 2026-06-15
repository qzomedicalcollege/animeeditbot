# -*- coding: utf-8 -*-
"""
Точка входа бота.
Инициализирует aiogram 3.x, подключает все роутеры и запускает polling.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.database.models import init_db
from bot.handlers.start import router as start_router
from bot.handlers.upload import router as upload_router
from bot.handlers.edit import router as edit_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Главная функция запуска бота."""
    logger.info("Инициализация бота...")

    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")

    # Создаём бота с HTML-разметкой по умолчанию
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Диспетчер с хранилищем состояний в памяти (подходит для Termux)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры (порядок важен — первый совпавший обработчик сработает)
    dp.include_router(start_router)
    dp.include_router(upload_router)
    dp.include_router(edit_router)

    logger.info("Бот запущен! Ожидание сообщений...")

    try:
        # Удаляем необработанные апдейты и запускаем polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())
