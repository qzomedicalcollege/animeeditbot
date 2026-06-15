# -*- coding: utf-8 -*-
"""
Обработчик команд /start и /help.
Приветственное сообщение и инструкция по использованию бота.
"""

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from bot.keyboards.inline import get_main_menu_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start — приветствие и главное меню."""
    welcome_text = (
        "🎬 <b>Anime Edit Bot</b>\n\n"
        "Привет! Я помогу тебе создать крутой аниме-эдит "
        "для TikTok / Shorts в формате 9:16.\n\n"
        "📋 <b>Как пользоваться:</b>\n"
        "1️⃣ Загрузи видео-клипы (до 5 штук, макс. 60 сек каждый)\n"
        "2️⃣ Загрузи аудио-трек (музыку)\n"
        "3️⃣ Выбери стиль эдита\n"
        "4️⃣ Получи готовое видео!\n\n"
        "Нажми <b>«🎬 Создать эдит»</b>, чтобы начать 👇"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help — подробная справка."""
    help_text = (
        "📖 <b>Справка по Anime Edit Bot</b>\n\n"
        "🎨 <b>Доступные стили:</b>\n"
        "🔥 <b>Hype</b> — быстрые нарезки, зум, тряска, вспышки яркости\n"
        "😢 <b>Sad</b> — замедление, размытие, обесцвечивание, зернистость\n"
        "🌊 <b>Chill</b> — плавные переходы, тёплые тона, мягкий зум\n"
        "⚡ <b>Glitch</b> — RGB-сдвиг, шум, смещение\n\n"
        "📏 <b>Ограничения:</b>\n"
        "• Максимум 5 клипов на один эдит\n"
        "• Каждый клип до 60 секунд\n"
        "• Размер файла до 50 МБ\n"
        "• Выходной формат: 1080×1920 (9:16)\n\n"
        "🔧 <b>Команды:</b>\n"
        "/start — главное меню\n"
        "/help — эта справка\n\n"
        "💡 Бит-детекция автоматически нарезает клипы под ритм музыки!"
    )
    await message.answer(help_text)
