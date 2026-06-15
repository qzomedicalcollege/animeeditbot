#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  🎬 Anime Edit Bot — Полный установщик для Termux
#  Этот скрипт создаёт все файлы проекта и готовит среду.
#  Запуск: bash install.sh
# ============================================================

set -e

PROJECT_DIR="$HOME/anime-edit-bot"

echo ""
echo "🎬 =============================="
echo "   Anime Edit Bot — Установка"
echo "=============================== 🎬"
echo ""

# --- Создание директорий ---
echo "📁 Создаю директории проекта..."
mkdir -p "$PROJECT_DIR/bot/handlers"
mkdir -p "$PROJECT_DIR/bot/services"
mkdir -p "$PROJECT_DIR/bot/keyboards"
mkdir -p "$PROJECT_DIR/bot/database"
mkdir -p "$PROJECT_DIR/bot/utils"
mkdir -p "$PROJECT_DIR/media/clips"
mkdir -p "$PROJECT_DIR/media/music"
mkdir -p "$PROJECT_DIR/media/output"
mkdir -p "$PROJECT_DIR/media/temp"
echo "✅ Директории созданы"
echo ""

cd "$PROJECT_DIR"

# ============================================================
# requirements.txt
# ============================================================
echo "📝 Создаю requirements.txt..."
cat << 'EOF' > requirements.txt
aiogram==3.15.0
python-dotenv==1.1.0
aiosqlite==0.21.0
Pillow==11.2.1
aubio==0.4.9
aiofiles==24.1.0
EOF
echo "✅ requirements.txt"

# ============================================================
# .env.example
# ============================================================
echo "📝 Создаю .env.example..."
cat << 'EOF' > .env.example
# Telegram Bot Token от @BotFather
BOT_TOKEN=your_bot_token_here
EOF
echo "✅ .env.example"

# ============================================================
# bot/__init__.py
# ============================================================
echo "📝 Создаю bot/__init__.py..."
cat << 'EOF' > bot/__init__.py
# -*- coding: utf-8 -*-
"""Пакет Telegram-бота для создания аниме-эдитов."""
EOF
echo "✅ bot/__init__.py"

# ============================================================
# bot/config.py
# ============================================================
echo "📝 Создаю bot/config.py..."
cat << 'EOF' > bot/config.py
# -*- coding: utf-8 -*-
"""
Конфигурация бота.
Загружает настройки из переменных окружения и определяет пути к директориям.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Создайте .env файл с BOT_TOKEN=ваш_токен")

# Корневая директория проекта
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Директории для медиафайлов
MEDIA_DIR: Path = BASE_DIR / "media"
CLIPS_DIR: Path = MEDIA_DIR / "clips"
MUSIC_DIR: Path = MEDIA_DIR / "music"
OUTPUT_DIR: Path = MEDIA_DIR / "output"
TEMP_DIR: Path = MEDIA_DIR / "temp"

# Создаём все необходимые директории при старте
for directory in (CLIPS_DIR, MUSIC_DIR, OUTPUT_DIR, TEMP_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Ограничения
MAX_VIDEO_DURATION: int = 60        # Максимальная длительность видео (секунды)
MAX_CLIPS_PER_EDIT: int = 5         # Максимум клипов на один эдит
MAX_FILE_SIZE_MB: int = 50          # Максимальный размер файла (МБ)
OUTPUT_WIDTH: int = 1080             # Ширина выходного видео
OUTPUT_HEIGHT: int = 1920            # Высота выходного видео (9:16)
OUTPUT_FPS: int = 30                 # FPS выходного видео

# Путь к базе данных
DB_PATH: Path = BASE_DIR / "bot" / "database" / "bot.db"

# Доступные стили эдитов
STYLES: dict[str, str] = {
    "hype": "🔥 Hype",
    "sad": "😢 Sad",
    "chill": "🌊 Chill",
    "glitch": "⚡ Glitch",
}
EOF
echo "✅ bot/config.py"

# ============================================================
# bot/main.py
# ============================================================
echo "📝 Создаю bot/main.py..."
cat << 'EOF' > bot/main.py
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
EOF
echo "✅ bot/main.py"

# ============================================================
# bot/handlers/__init__.py
# ============================================================
echo "📝 Создаю bot/handlers/__init__.py..."
cat << 'EOF' > bot/handlers/__init__.py
# -*- coding: utf-8 -*-
"""Пакет обработчиков команд и сообщений."""
EOF
echo "✅ bot/handlers/__init__.py"

# ============================================================
# bot/handlers/start.py
# ============================================================
echo "📝 Создаю bot/handlers/start.py..."
cat << 'EOF' > bot/handlers/start.py
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
EOF
echo "✅ bot/handlers/start.py"

# ============================================================
# bot/handlers/upload.py
# ============================================================
echo "📝 Создаю bot/handlers/upload.py..."
cat << 'EOF' > bot/handlers/upload.py
# -*- coding: utf-8 -*-
"""
Обработчик загрузки видео и аудио файлов.
FSM-состояния для пошагового процесса: клипы → музыка → стиль → генерация.
"""

import logging
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import (
    CLIPS_DIR,
    MUSIC_DIR,
    MAX_CLIPS_PER_EDIT,
    MAX_VIDEO_DURATION,
    MAX_FILE_SIZE_MB,
)
from bot.keyboards.inline import (
    get_upload_clips_keyboard,
    get_style_keyboard,
    get_cancel_keyboard,
)
from bot.services.converter import get_video_duration
from bot.utils.helpers import generate_unique_filename, check_file_size

logger = logging.getLogger(__name__)

router = Router(name="upload")


# === FSM-состояния ===
class EditStates(StatesGroup):
    """Состояния конечного автомата для создания эдита."""
    waiting_clips = State()      # Ожидание загрузки клипов
    waiting_music = State()      # Ожидание загрузки музыки
    waiting_style = State()      # Ожидание выбора стиля
    waiting_text = State()       # Ожидание текста для наложения
    processing = State()         # Обработка видео


# === Начало создания эдита ===
@router.callback_query(F.data == "create_edit")
async def start_edit_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса создания эдита — переход к загрузке клипов."""
    await state.clear()
    await state.update_data(clips=[], music_path=None, style=None, text_overlay=None)
    await state.set_state(EditStates.waiting_clips)

    await callback.message.edit_text(
        "📹 <b>Шаг 1/4 — Загрузка клипов</b>\n\n"
        f"Отправь мне видео-клипы (до {MAX_CLIPS_PER_EDIT} штук).\n"
        f"Каждый клип должен быть не длиннее {MAX_VIDEO_DURATION} сек.\n\n"
        "Когда загрузишь все клипы, нажми <b>«✅ Готово»</b> 👇",
        reply_markup=get_upload_clips_keyboard(),
    )
    await callback.answer()


# === Загрузка видео-клипов ===
@router.message(EditStates.waiting_clips, F.video)
async def handle_video_upload(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка загруженного видео-клипа."""
    data = await state.get_data()
    clips: list[str] = data.get("clips", [])

    # Проверка количества клипов
    if len(clips) >= MAX_CLIPS_PER_EDIT:
        await message.answer(
            f"⚠️ Максимум {MAX_CLIPS_PER_EDIT} клипов! "
            "Нажми <b>«✅ Готово»</b>, чтобы продолжить.",
            reply_markup=get_upload_clips_keyboard(),
        )
        return

    video = message.video

    # Проверка размера файла
    if not check_file_size(video.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Проверка длительности
    if video.duration and video.duration > MAX_VIDEO_DURATION:
        await message.answer(
            f"⚠️ Клип слишком длинный ({video.duration} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    # Скачиваем файл
    filename = generate_unique_filename("clip", ".mp4")
    file_path = CLIPS_DIR / filename

    try:
        file = await bot.get_file(video.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания видео: %s", e)
        await message.answer("❌ Ошибка при скачивании видео. Попробуй ещё раз.")
        return

    # Дополнительная проверка длительности через FFmpeg
    duration = await get_video_duration(str(file_path))
    if duration is not None and duration > MAX_VIDEO_DURATION:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Клип слишком длинный ({duration:.1f} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    clips.append(str(file_path))
    await state.update_data(clips=clips)

    await message.answer(
        f"✅ Клип #{len(clips)} загружен!\n"
        f"Всего клипов: {len(clips)}/{MAX_CLIPS_PER_EDIT}\n\n"
        "Загрузи ещё или нажми <b>«✅ Готово»</b>.",
        reply_markup=get_upload_clips_keyboard(),
    )


@router.message(EditStates.waiting_clips, F.document)
async def handle_video_as_document(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка видео, отправленного как документ."""
    doc = message.document

    # Проверяем что это видео по mime-type
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        await message.answer("⚠️ Отправь видео-файл, а не документ другого типа.")
        return

    # Проверка размера
    if not check_file_size(doc.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Скачиваем
    ext = Path(doc.file_name).suffix if doc.file_name else ".mp4"
    filename = generate_unique_filename("clip", ext)
    file_path = CLIPS_DIR / filename

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания документа: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    # Проверка длительности
    duration = await get_video_duration(str(file_path))
    if duration is not None and duration > MAX_VIDEO_DURATION:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Клип слишком длинный ({duration:.1f} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    data = await state.get_data()
    clips: list[str] = data.get("clips", [])

    if len(clips) >= MAX_CLIPS_PER_EDIT:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Максимум {MAX_CLIPS_PER_EDIT} клипов!",
            reply_markup=get_upload_clips_keyboard(),
        )
        return

    clips.append(str(file_path))
    await state.update_data(clips=clips)

    await message.answer(
        f"✅ Клип #{len(clips)} загружен!\n"
        f"Всего клипов: {len(clips)}/{MAX_CLIPS_PER_EDIT}\n\n"
        "Загрузи ещё или нажми <b>«✅ Готово»</b>.",
        reply_markup=get_upload_clips_keyboard(),
    )


@router.message(EditStates.waiting_clips)
async def handle_invalid_clip(message: Message) -> None:
    """Подсказка, если пользователь отправил не видео."""
    await message.answer(
        "⚠️ Отправь видео-файл! Принимаются .mp4, .mov, .avi и другие форматы."
    )


# === Завершение загрузки клипов → переход к музыке ===
@router.callback_query(F.data == "clips_done", EditStates.waiting_clips)
async def clips_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь закончил загрузку клипов, переход к загрузке музыки."""
    data = await state.get_data()
    clips = data.get("clips", [])

    if not clips:
        await callback.answer("❌ Загрузи хотя бы один клип!", show_alert=True)
        return

    await state.set_state(EditStates.waiting_music)

    await callback.message.edit_text(
        f"📹 Загружено клипов: {len(clips)}\n\n"
        "🎵 <b>Шаг 2/4 — Загрузка музыки</b>\n\n"
        "Отправь мне аудио-файл (трек для эдита).\n"
        "Поддерживаются: .mp3, .wav, .ogg, .m4a",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


# === Загрузка аудио ===
@router.message(EditStates.waiting_music, F.audio)
async def handle_audio_upload(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка загруженного аудио-файла."""
    audio = message.audio

    # Проверка размера
    if not check_file_size(audio.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Скачиваем аудио
    ext = ".mp3"
    if audio.file_name:
        ext = Path(audio.file_name).suffix or ".mp3"
    filename = generate_unique_filename("music", ext)
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(audio.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания аудио: %s", e)
        await message.answer("❌ Ошибка при скачивании аудио. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music, F.voice)
async def handle_voice_as_music(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка голосового сообщения как аудио."""
    voice = message.voice

    filename = generate_unique_filename("music", ".ogg")
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(voice.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания голосового: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music, F.document)
async def handle_audio_as_document(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка аудио, отправленного как документ."""
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("audio/"):
        await message.answer("⚠️ Отправь аудио-файл (.mp3, .wav, .ogg, .m4a).")
        return

    if not check_file_size(doc.file_size, MAX_FILE_SIZE_MB):
        await message.answer(f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ.")
        return

    ext = Path(doc.file_name).suffix if doc.file_name else ".mp3"
    filename = generate_unique_filename("music", ext)
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания документа: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music)
async def handle_invalid_music(message: Message) -> None:
    """Подсказка, если отправлено не аудио."""
    await message.answer(
        "⚠️ Отправь аудио-файл! Принимаются .mp3, .wav, .ogg, .m4a."
    )


# === Отмена ===
@router.callback_query(F.data == "cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена текущего процесса создания эдита."""
    # Очищаем загруженные файлы
    data = await state.get_data()
    for clip_path in data.get("clips", []):
        Path(clip_path).unlink(missing_ok=True)
    music = data.get("music_path")
    if music:
        Path(music).unlink(missing_ok=True)

    await state.clear()

    await callback.message.edit_text(
        "❌ Создание эдита отменено.\n\n"
        "Нажми /start, чтобы начать заново."
    )
    await callback.answer("Отменено")
EOF
echo "✅ bot/handlers/upload.py"

# ============================================================
# bot/handlers/edit.py
# ============================================================
echo "📝 Создаю bot/handlers/edit.py..."
cat << 'EOF' > bot/handlers/edit.py
# -*- coding: utf-8 -*-
"""
Обработчик выбора стиля и запуска генерации видео.
Стили: Hype, Sad, Chill, Glitch.
"""

import logging
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext

from bot.config import STYLES, OUTPUT_DIR
from bot.handlers.upload import EditStates
from bot.keyboards.inline import get_confirm_keyboard, get_main_menu_keyboard
from bot.services.video_editor import create_edit
from bot.services.beat_detector import detect_beats
from bot.database.models import save_edit, save_user
from bot.utils.helpers import generate_unique_filename, cleanup_files

logger = logging.getLogger(__name__)

router = Router(name="edit")


# === Выбор стиля ===
@router.callback_query(F.data.startswith("style:"), EditStates.waiting_style)
async def handle_style_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора стиля эдита."""
    style = callback.data.split(":")[1]

    if style not in STYLES:
        await callback.answer("❌ Неизвестный стиль!", show_alert=True)
        return

    await state.update_data(style=style)
    await state.set_state(EditStates.waiting_text)

    style_name = STYLES[style]
    await callback.message.edit_text(
        f"🎨 Выбран стиль: {style_name}\n\n"
        "✏️ <b>Шаг 4/4 — Текст (необязательно)</b>\n\n"
        "Отправь текст для наложения на видео "
        "(например, название аниме).\n\n"
        "Или нажми <b>«⏩ Пропустить»</b>, чтобы создать без текста.",
        reply_markup=get_confirm_keyboard(),
    )
    await callback.answer()


# === Ввод текста для наложения ===
@router.message(EditStates.waiting_text, F.text)
async def handle_text_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка текста для наложения на видео."""
    text = message.text.strip()

    # Ограничиваем длину текста
    if len(text) > 100:
        await message.answer("⚠️ Текст слишком длинный! Максимум 100 символов.")
        return

    await state.update_data(text_overlay=text)

    # Запускаем генерацию
    await _start_generation(message, state, bot, reply_to_message=True)


# === Пропуск текста ===
@router.callback_query(F.data == "skip_text", EditStates.waiting_text)
async def skip_text(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Пропуск текстового наложения."""
    await state.update_data(text_overlay=None)
    await _start_generation(callback, state, bot, reply_to_message=False)
    await callback.answer()


# === Генерация видео ===
async def _start_generation(
    event: CallbackQuery | Message,
    state: FSMContext,
    bot: Bot,
    reply_to_message: bool,
) -> None:
    """Запуск процесса генерации видео."""
    data = await state.get_data()
    clips = data.get("clips", [])
    music_path = data.get("music_path")
    style = data.get("style")
    text_overlay = data.get("text_overlay")

    # Определяем куда отправлять сообщения
    if isinstance(event, CallbackQuery):
        chat_id = event.message.chat.id
        user_id = event.from_user.id
        username = event.from_user.username or ""
        progress_msg = await event.message.edit_text("⏳ Начинаю создание эдита...")
    else:
        chat_id = event.chat.id
        user_id = event.from_user.id
        username = event.from_user.username or ""
        progress_msg = await event.answer("⏳ Начинаю создание эдита...")

    await state.set_state(EditStates.processing)

    # Сохраняем пользователя в БД
    await save_user(user_id, username)

    try:
        # Шаг 1: Детекция битов
        await bot.edit_message_text(
            "🎵 Анализирую ритм музыки...",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
        )

        beats = await detect_beats(music_path)
        if not beats:
            # Если биты не обнаружены — используем равномерную нарезку
            logger.warning("Биты не обнаружены, используем равномерную нарезку")
            beats = [i * 0.5 for i in range(60)]  # Каждые 0.5 сек

        logger.info("Обнаружено %d битов", len(beats))

        # Шаг 2: Создание эдита
        await bot.edit_message_text(
            f"🎬 Создаю эдит в стиле {STYLES.get(style, style)}...\n"
            "Это может занять пару минут ⏱",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
        )

        output_filename = generate_unique_filename("edit", ".mp4")
        output_path = str(OUTPUT_DIR / output_filename)

        result = await create_edit(
            clips=clips,
            music_path=music_path,
            style=style,
            beats=beats,
            output_path=output_path,
            text_overlay=text_overlay,
        )

        if not result or not Path(result).exists():
            raise FileNotFoundError("Выходной файл не создан")

        # Шаг 3: Отправка результата
        await bot.edit_message_text(
            "📤 Отправляю готовое видео...",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
        )

        video_file = FSInputFile(result, filename=f"anime_edit_{style}.mp4")
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=(
                f"🎬 <b>Аниме-эдит готов!</b>\n"
                f"🎨 Стиль: {STYLES.get(style, style)}\n"
                f"📹 Клипов: {len(clips)}\n"
                f"🎵 Битов: {len(beats)}"
            ),
            supports_streaming=True,
        )

        # Сохраняем в БД
        await save_edit(user_id, style, result)

        # Финальное сообщение
        await bot.edit_message_text(
            "✅ Эдит готов! Нажми «🎬 Создать эдит», чтобы сделать ещё один.",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
            reply_markup=get_main_menu_keyboard(),
        )

    except Exception as e:
        logger.error("Ошибка при создании эдита: %s", e, exc_info=True)
        await bot.edit_message_text(
            "❌ <b>Ошибка при создании эдита</b>\n\n"
            f"Причина: {str(e)[:200]}\n\n"
            "Попробуй ещё раз с другими файлами или нажми /start.",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
            reply_markup=get_main_menu_keyboard(),
        )
    finally:
        # Очищаем временные файлы (клипы и музыку)
        temp_files = clips.copy()
        if music_path:
            temp_files.append(music_path)
        cleanup_files(temp_files)
        await state.clear()
EOF
echo "✅ bot/handlers/edit.py"

# ============================================================
# bot/keyboards/__init__.py
# ============================================================
echo "📝 Создаю bot/keyboards/__init__.py..."
cat << 'EOF' > bot/keyboards/__init__.py
# -*- coding: utf-8 -*-
"""Пакет инлайн-клавиатур."""
EOF
echo "✅ bot/keyboards/__init__.py"

# ============================================================
# bot/keyboards/inline.py
# ============================================================
echo "📝 Создаю bot/keyboards/inline.py..."
cat << 'EOF' > bot/keyboards/inline.py
# -*- coding: utf-8 -*-
"""
Инлайн-клавиатуры бота.
Главное меню, выбор стиля, подтверждение, отмена.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import STYLES


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Создать эдит", callback_data="create_edit")
    )
    builder.row(
        InlineKeyboardButton(text="📖 Помощь", callback_data="help_info")
    )
    return builder.as_markup()


def get_upload_clips_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время загрузки клипов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="clips_done")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля эдита."""
    builder = InlineKeyboardBuilder()
    for style_key, style_name in STYLES.items():
        builder.row(
            InlineKeyboardButton(
                text=style_name,
                callback_data=f"style:{style_key}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения / пропуска текста."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_text")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()
EOF
echo "✅ bot/keyboards/inline.py"

# ============================================================
# bot/services/__init__.py
# ============================================================
echo "📝 Создаю bot/services/__init__.py..."
cat << 'EOF' > bot/services/__init__.py
# -*- coding: utf-8 -*-
"""Пакет сервисов: видеоредактор, бит-детекция, эффекты, конвертер."""
EOF
echo "✅ bot/services/__init__.py"

# ============================================================
# bot/services/beat_detector.py
# ============================================================
echo "📝 Создаю bot/services/beat_detector.py..."
cat << 'EOF' > bot/services/beat_detector.py
# -*- coding: utf-8 -*-
"""
Детекция битов в аудиофайле с помощью aubio.
Возвращает список временных меток ударов в секундах.
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Размер буфера и шаг для анализа
BUFFER_SIZE = 1024
HOP_SIZE = 512
SAMPLE_RATE = 44100


async def detect_beats(audio_path: str) -> list[float]:
    """
    Асинхронная обёртка над синхронной функцией детекции битов.
    Запускает анализ в отдельном потоке, чтобы не блокировать event loop.

    Args:
        audio_path: путь к аудиофайлу

    Returns:
        Список временных меток битов в секундах
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _detect_beats_sync, audio_path)


def _detect_beats_sync(audio_path: str) -> list[float]:
    """
    Синхронная детекция битов через aubio.

    Алгоритм:
    1. Открываем аудиофайл через aubio.source
    2. Создаём tempo-детектор
    3. Считываем аудио по буферам, фиксируем удары
    4. Возвращаем отсортированный список временных меток

    Args:
        audio_path: путь к аудиофайлу

    Returns:
        Список временных меток битов в секундах
    """
    if not Path(audio_path).exists():
        logger.error("Аудиофайл не найден: %s", audio_path)
        return []

    try:
        import aubio

        # Открываем аудиофайл
        source = aubio.source(audio_path, SAMPLE_RATE, HOP_SIZE)
        actual_samplerate = source.samplerate

        # Создаём детектор темпа
        tempo = aubio.tempo("default", BUFFER_SIZE, HOP_SIZE, actual_samplerate)

        beats: list[float] = []
        total_frames = 0

        # Читаем аудио по блокам
        while True:
            samples, read = source()

            # Проверяем наличие бита в текущем блоке
            is_beat = tempo(samples)
            if is_beat[0] > 0:
                # Вычисляем время бита в секундах
                beat_time = total_frames / float(actual_samplerate)
                beats.append(round(beat_time, 4))

            total_frames += read

            # Конец файла
            if read < HOP_SIZE:
                break

        logger.info(
            "Обнаружено %d битов в файле %s (%.1f сек)",
            len(beats),
            Path(audio_path).name,
            total_frames / float(actual_samplerate),
        )

        return beats

    except ImportError:
        logger.warning("aubio не установлен, пробуем FFmpeg fallback")
        return _detect_beats_ffmpeg_fallback(audio_path)
    except Exception as e:
        logger.error("Ошибка детекции битов: %s", e)
        return _detect_beats_ffmpeg_fallback(audio_path)


def _detect_beats_ffmpeg_fallback(audio_path: str) -> list[float]:
    """
    Запасной вариант: равномерная нарезка, если aubio недоступен.
    Генерирует биты каждые ~0.5 секунды.

    Args:
        audio_path: путь к аудиофайлу

    Returns:
        Список равномерных временных меток
    """
    logger.info("Используем равномерную нарезку (fallback)")
    # Генерируем биты каждые 0.5 сек на 2 минуты
    return [i * 0.5 for i in range(240)]
EOF
echo "✅ bot/services/beat_detector.py"

# ============================================================
# bot/services/converter.py
# ============================================================
echo "📝 Создаю bot/services/converter.py..."
cat << 'EOF' > bot/services/converter.py
# -*- coding: utf-8 -*-
"""
Утилиты конвертации видео.
Конвертация в 9:16, получение длительности, извлечение информации об аудио.
Все операции через FFmpeg subprocess.
"""

import asyncio
import json
import logging

from bot.config import OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS

logger = logging.getLogger(__name__)


async def get_video_duration(file_path: str) -> float | None:
    """
    Получает длительность видео/аудио файла через ffprobe.

    Args:
        file_path: путь к файлу

    Returns:
        Длительность в секундах или None при ошибке
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=15
        )

        if process.returncode != 0:
            logger.error("ffprobe ошибка: %s", stderr.decode(errors="replace"))
            return None

        data = json.loads(stdout.decode("utf-8"))
        duration = float(data.get("format", {}).get("duration", 0))
        return duration if duration > 0 else None

    except asyncio.TimeoutError:
        logger.error("ffprobe таймаут для %s", file_path)
        return None
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Ошибка парсинга ffprobe: %s", e)
        return None
    except Exception as e:
        logger.error("Ошибка получения длительности: %s", e)
        return None


async def get_video_info(file_path: str) -> dict | None:
    """
    Получает полную информацию о видео через ffprobe.

    Args:
        file_path: путь к видео-файлу

    Returns:
        Словарь с информацией (width, height, duration, fps) или None
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=15
        )

        if process.returncode != 0:
            return None

        data = json.loads(stdout.decode("utf-8"))

        # Ищем видео-поток
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            return None

        # Парсим FPS из r_frame_rate (например, "30/1")
        fps = 30.0
        r_frame_rate = video_stream.get("r_frame_rate", "30/1")
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 30.0

        return {
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "duration": float(data.get("format", {}).get("duration", 0)),
            "fps": fps,
            "codec": video_stream.get("codec_name", "unknown"),
        }

    except Exception as e:
        logger.error("Ошибка получения информации о видео: %s", e)
        return None


async def get_audio_info(file_path: str) -> dict | None:
    """
    Извлекает информацию об аудио-файле через ffprobe.

    Args:
        file_path: путь к аудио-файлу

    Returns:
        Словарь с информацией (duration, sample_rate, channels, codec) или None
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=15
        )

        if process.returncode != 0:
            return None

        data = json.loads(stdout.decode("utf-8"))

        # Ищем аудио-поток
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if not audio_stream:
            return None

        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "sample_rate": int(audio_stream.get("sample_rate", 44100)),
            "channels": int(audio_stream.get("channels", 2)),
            "codec": audio_stream.get("codec_name", "unknown"),
        }

    except Exception as e:
        logger.error("Ошибка получения информации об аудио: %s", e)
        return None


async def convert_to_vertical(
    input_path: str,
    output_path: str,
    width: int = OUTPUT_WIDTH,
    height: int = OUTPUT_HEIGHT,
) -> bool:
    """
    Конвертирует видео в вертикальный формат 9:16 (1080x1920).

    Использует pad + scale + crop для сохранения пропорций:
    - Масштабирует видео так, чтобы заполнить кадр 9:16
    - Обрезает лишнее (crop по центру)

    Args:
        input_path: путь к исходному видео
        output_path: путь для выходного видео
        width: ширина выходного видео
        height: высота выходного видео

    Returns:
        True если успешно
    """
    # Фильтр: масштабируем так чтобы заполнить кадр, потом обрезаем по центру
    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"setsar=1"
    )

    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", input_path,
            "-vf", scale_filter,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-r", str(OUTPUT_FPS),
            "-an",  # Без аудио (аудио добавляется отдельно)
            "-pix_fmt", "yuv420p",
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=60
        )

        if process.returncode != 0:
            error_text = stderr.decode("utf-8", errors="replace")
            logger.error("Ошибка конвертации в 9:16: %s", error_text)
            return False

        return True

    except asyncio.TimeoutError:
        logger.error("Таймаут конвертации в 9:16")
        return False
    except Exception as e:
        logger.error("Ошибка конвертации: %s", e)
        return False
EOF
echo "✅ bot/services/converter.py"

# ============================================================
# bot/services/effects.py
# ============================================================
echo "📝 Создаю bot/services/effects.py..."
cat << 'EOF' > bot/services/effects.py
# -*- coding: utf-8 -*-
"""
FFmpeg фильтры для каждого стиля эдита.

Стили:
- Hype: быстрые нарезки, зум, тряска, вспышки яркости
- Sad: замедление, размытие, обесцвечивание, зернистость
- Chill: плавные переходы, тёплые тона, мягкий зум
- Glitch: RGB-сдвиг, шум, смещение
"""


def get_style_filters(style: str, segment_index: int = 0) -> str:
    """
    Возвращает строку FFmpeg-фильтров для заданного стиля.

    Args:
        style: ключ стиля (hype/sad/chill/glitch)
        segment_index: индекс текущего сегмента (для вариации эффектов)

    Returns:
        Строка FFmpeg video filter complex
    """
    filters = {
        "hype": _get_hype_filters,
        "sad": _get_sad_filters,
        "chill": _get_chill_filters,
        "glitch": _get_glitch_filters,
    }

    builder = filters.get(style, _get_chill_filters)
    return builder(segment_index)


def _get_hype_filters(segment_index: int) -> str:
    """
    Hype-стиль: энергичный, агрессивный.
    - Ускорение (1.2x)
    - Зум (случайный на основе индекса сегмента)
    - Тряска камеры
    - Вспышки яркости
    - Повышенная контрастность и насыщенность
    """
    # Разные зум-значения для разных сегментов
    zoom_values = [1.05, 1.1, 1.15, 1.08, 1.12]
    zoom = zoom_values[segment_index % len(zoom_values)]

    # Тряска через случайное смещение
    shake_x = (segment_index % 3) * 2 + 2  # 2-6 пикселей
    shake_y = ((segment_index + 1) % 3) * 2 + 2

    filters = [
        # Ускорение видео
        f"setpts=PTS/{1.2}",
        # Зум через масштабирование и обрезку
        f"scale=iw*{zoom}:ih*{zoom}",
        "crop=iw/{0}:ih/{0}".format(zoom),
        # Тряска камеры — смещение по X и Y
        f"crop=iw-{shake_x * 2}:ih-{shake_y * 2}:"
        f"{shake_x}+{shake_x}*sin(n*0.5):"
        f"{shake_y}+{shake_y}*cos(n*0.7)",
        # Повышенная контрастность и насыщенность
        "eq=contrast=1.3:brightness=0.05:saturation=1.4",
        # Резкость
        "unsharp=5:5:1.5:5:5:0.5",
    ]

    return ",".join(filters)


def _get_sad_filters(segment_index: int) -> str:
    """
    Sad-стиль: меланхоличный, замедленный.
    - Замедление (0.85x)
    - Лёгкое размытие
    - Обесцвечивание
    - Зернистость плёнки
    - Пониженная яркость
    """
    # Разная степень обесцвечивания
    sat_values = [0.3, 0.4, 0.35, 0.45, 0.25]
    saturation = sat_values[segment_index % len(sat_values)]

    filters = [
        # Замедление
        "setpts=PTS/0.85",
        # Обесцвечивание и тёмные тона
        f"eq=saturation={saturation}:brightness=-0.05:contrast=1.1",
        # Лёгкое размытие (мечтательный эффект)
        "gblur=sigma=1.2",
        # Виньетирование (затемнение краёв)
        "vignette=PI/4",
        # Зернистость плёнки
        "noise=alls=15:allf=t+u",
    ]

    return ",".join(filters)


def _get_chill_filters(segment_index: int) -> str:
    """
    Chill-стиль: спокойный, расслабляющий.
    - Нормальная скорость
    - Тёплые тона (оранжево-жёлтый оттенок)
    - Мягкий зум
    - Плавные переходы (fade)
    - Слегка повышенная яркость
    """
    # Мягкий зум
    zoom_values = [1.02, 1.03, 1.04, 1.025, 1.035]
    zoom = zoom_values[segment_index % len(zoom_values)]

    filters = [
        # Мягкий зум
        f"scale=iw*{zoom}:ih*{zoom}",
        "crop=iw/{0}:ih/{0}".format(zoom),
        # Тёплые тона: усиление красного/жёлтого через кривые
        "colorbalance=rs=0.1:gs=0.05:bs=-0.1:rm=0.08:gm=0.03:bm=-0.05",
        # Мягкая яркость и контраст
        "eq=brightness=0.04:contrast=1.05:saturation=1.15",
        # Лёгкое смягчение
        "gblur=sigma=0.4",
    ]

    return ",".join(filters)


def _get_glitch_filters(segment_index: int) -> str:
    """
    Glitch-стиль: киберпанковый, искажённый.
    - RGB-сдвиг
    - Цифровой шум
    - Смещение (displacement)
    - Высокая контрастность
    - Инверсия цветов на некоторых сегментах
    """
    # RGB-сдвиг — разные направления для разных сегментов
    shift_x = (segment_index % 5 + 1) * 3
    shift_y = ((segment_index + 2) % 5 + 1) * 2

    filters_list = [
        # RGB-сдвиг: разделяем каналы и сдвигаем
        f"rgbashift=rh={shift_x}:rv={shift_y}:bh=-{shift_x}:bv=-{shift_y}",
        # Цифровой шум
        "noise=alls=30:allf=t",
        # Высокая контрастность, яркие цвета
        "eq=contrast=1.5:saturation=1.6:brightness=0.02",
    ]

    # Инверсия цветов на каждом 3-м сегменте
    if segment_index % 3 == 0:
        filters_list.append("negate")

    # Добавляем хроматические аберрации через лёгкий блюр по каналам
    filters_list.append("unsharp=7:7:2.0:7:7:0")

    return ",".join(filters_list)


def get_transition_filter(style: str, duration: float = 0.3) -> str:
    """
    Возвращает фильтр перехода между клипами для заданного стиля.

    Args:
        style: ключ стиля
        duration: длительность перехода в секундах

    Returns:
        Строка FFmpeg xfade фильтра
    """
    transitions = {
        "hype": "fade",           # Быстрый фейд
        "sad": "fadeblack",       # Фейд через чёрный
        "chill": "smoothleft",    # Плавный сдвиг
        "glitch": "pixelize",     # Пиксельный переход
    }
    transition = transitions.get(style, "fade")
    return f"xfade=transition={transition}:duration={duration}"
EOF
echo "✅ bot/services/effects.py"

# ============================================================
# bot/services/video_editor.py
# ============================================================
echo "📝 Создаю bot/services/video_editor.py..."
cat << 'EOF' > bot/services/video_editor.py
# -*- coding: utf-8 -*-
"""
Главный видеоредактор.
Принимает клипы, аудио, стиль и биты, создаёт финальный эдит через FFmpeg.

Процесс:
1. Нарезка клипов по временным меткам битов
2. Применение стилевых эффектов к каждому сегменту
3. Конвертация каждого сегмента в 9:16
4. Конкатенация всех сегментов
5. Наложение аудио-дорожки
6. Наложение текста (опционально)
7. Вывод финального видео 1080x1920
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from bot.config import OUTPUT_WIDTH, OUTPUT_HEIGHT, OUTPUT_FPS, TEMP_DIR
from bot.services.effects import get_style_filters
from bot.services.converter import get_video_duration, convert_to_vertical

logger = logging.getLogger(__name__)


async def create_edit(
    clips: list[str],
    music_path: str,
    style: str,
    beats: list[float],
    output_path: str,
    text_overlay: str | None = None,
) -> str:
    """
    Создаёт финальный аниме-эдит.

    Args:
        clips: список путей к видео-клипам
        music_path: путь к аудио-файлу
        style: стиль эдита (hype/sad/chill/glitch)
        beats: список временных меток битов
        output_path: путь для выходного файла
        text_overlay: текст для наложения (или None)

    Returns:
        Путь к готовому видео

    Raises:
        RuntimeError: если FFmpeg вернул ошибку
    """
    temp_segments: list[str] = []

    try:
        # Шаг 1: Определяем длительности для нарезки из битов
        cut_points = _calculate_cut_points(beats, len(clips))
        logger.info("Точки нарезки: %s", cut_points[:10])

        # Шаг 2: Нарезаем и применяем эффекты к каждому сегменту
        segment_index = 0
        for clip_idx, clip_path in enumerate(clips):
            clip_duration = await get_video_duration(clip_path)
            if clip_duration is None:
                clip_duration = 10.0  # Фоллбэк

            # Определяем сколько сегментов вырезать из этого клипа
            segments_per_clip = max(1, len(cut_points) // len(clips))
            start_seg = clip_idx * segments_per_clip
            end_seg = min(start_seg + segments_per_clip, len(cut_points))

            if clip_idx == len(clips) - 1:
                # Последний клип забирает оставшиеся сегменты
                end_seg = len(cut_points)

            for seg_idx in range(start_seg, end_seg):
                seg_duration = cut_points[seg_idx]

                # Вычисляем начальную позицию в клипе
                # Распределяем сегменты равномерно по длительности клипа
                segments_in_this_clip = end_seg - start_seg
                local_idx = seg_idx - start_seg
                start_time = (local_idx / max(segments_in_this_clip, 1)) * max(
                    clip_duration - seg_duration, 0
                )

                # Ограничиваем start_time
                if start_time + seg_duration > clip_duration:
                    start_time = max(0, clip_duration - seg_duration)

                # Создаём временный файл для сегмента
                seg_filename = f"seg_{segment_index:04d}.mp4"
                seg_path = str(TEMP_DIR / seg_filename)

                # Получаем фильтры стиля
                style_filter = get_style_filters(style, segment_index)

                # Собираем FFmpeg-команду для сегмента
                success = await _cut_and_apply_effects(
                    input_path=clip_path,
                    output_path=seg_path,
                    start_time=start_time,
                    duration=seg_duration,
                    style_filter=style_filter,
                    segment_index=segment_index,
                )

                if success and Path(seg_path).exists():
                    temp_segments.append(seg_path)
                    segment_index += 1

        if not temp_segments:
            raise RuntimeError("Не удалось создать ни одного сегмента")

        logger.info("Создано %d сегментов", len(temp_segments))

        # Шаг 3: Конвертируем все сегменты в вертикальный формат
        vertical_segments: list[str] = []
        for i, seg_path in enumerate(temp_segments):
            vert_path = str(TEMP_DIR / f"vert_{i:04d}.mp4")
            success = await convert_to_vertical(seg_path, vert_path)
            if success:
                vertical_segments.append(vert_path)
            else:
                # Если конвертация не удалась, используем оригинал
                vertical_segments.append(seg_path)

        # Шаг 4: Конкатенация сегментов
        concat_path = str(TEMP_DIR / "concat_result.mp4")
        await _concatenate_segments(vertical_segments, concat_path)

        # Шаг 5: Наложение аудио
        audio_path = str(TEMP_DIR / "with_audio.mp4")
        await _add_audio(concat_path, music_path, audio_path)

        # Шаг 6: Наложение текста (если есть)
        if text_overlay:
            await _add_text_overlay(audio_path, output_path, text_overlay)
        else:
            # Просто копируем файл с аудио как финальный
            await _copy_file(audio_path, output_path)

        if not Path(output_path).exists():
            raise RuntimeError("Финальный файл не создан")

        logger.info("Эдит успешно создан: %s", output_path)
        return output_path

    finally:
        # Очищаем временные сегменты
        _cleanup_temp(temp_segments)
        # Очищаем все файлы в TEMP_DIR
        for f in TEMP_DIR.glob("*.mp4"):
            try:
                f.unlink()
            except OSError:
                pass
        for f in TEMP_DIR.glob("*.txt"):
            try:
                f.unlink()
            except OSError:
                pass


def _calculate_cut_points(beats: list[float], num_clips: int) -> list[float]:
    """
    Вычисляет длительности сегментов из временных меток битов.
    Берёт интервалы между битами и группирует их для создания
    динамичной нарезки.

    Args:
        beats: временные метки битов
        num_clips: количество клипов

    Returns:
        Список длительностей сегментов в секундах
    """
    if len(beats) < 2:
        # Если битов мало — делаем равномерные сегменты
        return [1.0] * max(num_clips * 3, 5)

    # Вычисляем интервалы между битами
    intervals: list[float] = []
    for i in range(1, len(beats)):
        interval = beats[i] - beats[i - 1]
        # Фильтруем слишком короткие и слишком длинные интервалы
        if 0.2 <= interval <= 3.0:
            intervals.append(round(interval, 3))

    if not intervals:
        return [0.5] * max(num_clips * 3, 5)

    # Группируем по 1-2 бита для каждого сегмента (для динамики)
    cut_points: list[float] = []
    i = 0
    while i < len(intervals):
        # Чередуем: один бит, два бита, один бит...
        if i % 3 == 0 and i + 1 < len(intervals):
            # Объединяем два интервала
            cut_points.append(intervals[i] + intervals[i + 1])
            i += 2
        else:
            cut_points.append(intervals[i])
            i += 1

    # Минимум сегментов = количество клипов * 2
    min_segments = num_clips * 2
    while len(cut_points) < min_segments and intervals:
        cut_points.extend(intervals[: min_segments - len(cut_points)])

    return cut_points


async def _run_ffmpeg(args: list[str], timeout: int = 120) -> tuple[bool, str]:
    """
    Запускает FFmpeg как подпроцесс асинхронно.

    Args:
        args: аргументы FFmpeg (без «ffmpeg» в начале)
        timeout: таймаут в секундах

    Returns:
        Кортеж (успех, stderr)
    """
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args

    logger.debug("FFmpeg команда: %s", " ".join(cmd))

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )

        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            logger.error("FFmpeg ошибка (код %d): %s", process.returncode, stderr_text)
            return False, stderr_text

        return True, ""

    except asyncio.TimeoutError:
        logger.error("FFmpeg таймаут (%d сек)", timeout)
        try:
            process.kill()
        except ProcessLookupError:
            pass
        return False, "Таймаут выполнения"
    except Exception as e:
        logger.error("Ошибка запуска FFmpeg: %s", e)
        return False, str(e)


async def _cut_and_apply_effects(
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float,
    style_filter: str,
    segment_index: int,
) -> bool:
    """
    Вырезает сегмент из клипа и применяет стилевые фильтры.

    Args:
        input_path: путь к исходному клипу
        output_path: путь для выходного сегмента
        start_time: начало нарезки (секунды)
        duration: длительность сегмента (секунды)
        style_filter: строка FFmpeg-фильтров
        segment_index: индекс сегмента

    Returns:
        True если успешно
    """
    args = [
        "-ss", f"{start_time:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-vf", style_filter,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-an",  # Убираем аудио из сегментов
        "-r", str(OUTPUT_FPS),
        output_path,
    ]

    success, error = await _run_ffmpeg(args, timeout=60)

    if not success:
        logger.warning(
            "Не удалось обработать сегмент %d: %s. Пробуем без фильтров...",
            segment_index, error,
        )
        # Фоллбэк: вырезаем без эффектов
        fallback_args = [
            "-ss", f"{start_time:.3f}",
            "-i", input_path,
            "-t", f"{duration:.3f}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-an",
            "-r", str(OUTPUT_FPS),
            output_path,
        ]
        success, _ = await _run_ffmpeg(fallback_args, timeout=60)

    return success


async def _concatenate_segments(segments: list[str], output_path: str) -> bool:
    """
    Конкатенация видео-сегментов через FFmpeg concat demuxer.

    Args:
        segments: список путей к сегментам
        output_path: путь для выходного файла

    Returns:
        True если успешно
    """
    # Создаём файл со списком сегментов для concat demuxer
    concat_list_path = str(TEMP_DIR / "concat_list.txt")

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for seg in segments:
            # Экранируем одинарные кавычки в путях
            safe_path = seg.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    args = [
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "21",
        "-r", str(OUTPUT_FPS),
        "-pix_fmt", "yuv420p",
        output_path,
    ]

    success, error = await _run_ffmpeg(args, timeout=120)

    if not success:
        logger.error("Ошибка конкатенации: %s", error)
        # Фоллбэк: копируем первый сегмент
        if segments:
            success, _ = await _run_ffmpeg(
                ["-i", segments[0], "-c", "copy", output_path],
                timeout=30,
            )

    return success


async def _add_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> bool:
    """
    Накладывает аудио-дорожку на видео.
    Обрезает аудио по длительности видео.

    Args:
        video_path: путь к видео
        audio_path: путь к аудио
        output_path: путь для выходного файла

    Returns:
        True если успешно
    """
    # Получаем длительность видео для обрезки аудио
    video_duration = await get_video_duration(video_path)
    duration_args = []
    if video_duration:
        duration_args = ["-t", f"{video_duration:.3f}"]

    args = [
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        *duration_args,
        output_path,
    ]

    success, error = await _run_ffmpeg(args, timeout=60)

    if not success:
        logger.error("Ошибка наложения аудио: %s", error)
        # Фоллбэк: копируем видео без аудио
        await _copy_file(video_path, output_path)

    return success


async def _add_text_overlay(
    input_path: str,
    output_path: str,
    text: str,
) -> bool:
    """
    Накладывает текст на видео (название аниме).
    Белый текст с чёрной тенью внизу экрана.

    Args:
        input_path: путь к видео
        output_path: путь для выходного файла
        text: текст для наложения

    Returns:
        True если успешно
    """
    # Экранируем спецсимволы для FFmpeg drawtext
    safe_text = text.replace("'", "\\'").replace(":", "\\:")
    safe_text = safe_text.replace("\\", "\\\\").replace('"', '\\"')

    # Фильтр drawtext: белый текст с тенью, внизу по центру
    drawtext_filter = (
        f"drawtext=text='{safe_text}'"
        ":fontsize=42"
        ":fontcolor=white"
        ":borderw=3"
        ":bordercolor=black"
        ":x=(w-text_w)/2"
        ":y=h-text_h-80"
        ":shadowcolor=black@0.6"
        ":shadowx=2:shadowy=2"
    )

    args = [
        "-i", input_path,
        "-vf", drawtext_filter,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "21",
        "-c:a", "copy",
        output_path,
    ]

    success, error = await _run_ffmpeg(args, timeout=60)

    if not success:
        logger.warning("Ошибка наложения текста: %s. Копируем без текста.", error)
        await _copy_file(input_path, output_path)

    return success


async def _copy_file(src: str, dst: str) -> bool:
    """Копирует файл через FFmpeg (stream copy)."""
    success, _ = await _run_ffmpeg(
        ["-i", src, "-c", "copy", dst],
        timeout=30,
    )
    return success


def _cleanup_temp(files: list[str]) -> None:
    """Удаляет временные файлы."""
    for f in files:
        try:
            Path(f).unlink(missing_ok=True)
        except OSError as e:
            logger.debug("Не удалось удалить %s: %s", f, e)
EOF
echo "✅ bot/services/video_editor.py"

# ============================================================
# bot/database/__init__.py
# ============================================================
echo "📝 Создаю bot/database/__init__.py..."
cat << 'EOF' > bot/database/__init__.py
# -*- coding: utf-8 -*-
"""Пакет базы данных."""
EOF
echo "✅ bot/database/__init__.py"

# ============================================================
# bot/database/models.py
# ============================================================
echo "📝 Создаю bot/database/models.py..."
cat << 'EOF' > bot/database/models.py
# -*- coding: utf-8 -*-
"""
Модели базы данных SQLite через aiosqlite.

Таблицы:
- users: информация о пользователях (user_id, username, created_at)
- edits: история созданных эдитов (edit_id, user_id, style, created_at, file_path)
"""

import aiosqlite
import logging
from datetime import datetime

from bot.config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Инициализация базы данных: создаёт таблицы, если их нет.
    Вызывается при старте бота.
    """
    # Создаём директорию для БД, если нет
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Таблица эдитов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                edit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                style       TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                file_path   TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.commit()
        logger.info("Таблицы БД созданы/проверены: %s", DB_PATH)


async def save_user(user_id: int, username: str = "") -> None:
    """
    Сохраняет или обновляет пользователя в базе.

    Args:
        user_id: Telegram user ID
        username: Telegram username
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
                """,
                (user_id, username, datetime.utcnow().isoformat()),
            )
            await db.commit()
    except Exception as e:
        logger.error("Ошибка сохранения пользователя %d: %s", user_id, e)


async def save_edit(user_id: int, style: str, file_path: str) -> int | None:
    """
    Сохраняет запись о созданном эдите.

    Args:
        user_id: Telegram user ID
        style: стиль эдита
        file_path: путь к выходному файлу

    Returns:
        ID созданной записи или None при ошибке
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                """
                INSERT INTO edits (user_id, style, file_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, style, file_path, datetime.utcnow().isoformat()),
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error("Ошибка сохранения эдита: %s", e)
        return None


async def get_user_edits(user_id: int, limit: int = 10) -> list[dict]:
    """
    Получает список эдитов пользователя.

    Args:
        user_id: Telegram user ID
        limit: максимум записей

    Returns:
        Список словарей с информацией об эдитах
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT edit_id, style, created_at, file_path
                FROM edits
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "edit_id": row["edit_id"],
                    "style": row["style"],
                    "created_at": row["created_at"],
                    "file_path": row["file_path"],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error("Ошибка получения эдитов пользователя %d: %s", user_id, e)
        return []


async def get_stats() -> dict:
    """
    Получает общую статистику бота.

    Returns:
        Словарь: total_users, total_edits, edits_by_style
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            # Общее число пользователей
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]

            # Общее число эдитов
            cursor = await db.execute("SELECT COUNT(*) FROM edits")
            total_edits = (await cursor.fetchone())[0]

            # Эдиты по стилям
            cursor = await db.execute(
                "SELECT style, COUNT(*) as cnt FROM edits GROUP BY style"
            )
            style_rows = await cursor.fetchall()
            edits_by_style = {row[0]: row[1] for row in style_rows}

            return {
                "total_users": total_users,
                "total_edits": total_edits,
                "edits_by_style": edits_by_style,
            }
    except Exception as e:
        logger.error("Ошибка получения статистики: %s", e)
        return {"total_users": 0, "total_edits": 0, "edits_by_style": {}}
EOF
echo "✅ bot/database/models.py"

# ============================================================
# bot/utils/__init__.py
# ============================================================
echo "📝 Создаю bot/utils/__init__.py..."
cat << 'EOF' > bot/utils/__init__.py
# -*- coding: utf-8 -*-
"""Пакет вспомогательных утилит."""
EOF
echo "✅ bot/utils/__init__.py"

# ============================================================
# bot/utils/helpers.py
# ============================================================
echo "📝 Создаю bot/utils/helpers.py..."
cat << 'EOF' > bot/utils/helpers.py
# -*- coding: utf-8 -*-
"""
Вспомогательные утилиты.
Проверка размера файлов, генерация уникальных имён, очистка старых файлов.
"""

import logging
import time
import uuid
from pathlib import Path

from bot.config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def generate_unique_filename(prefix: str, extension: str) -> str:
    """
    Генерирует уникальное имя файла на основе UUID и timestamp.

    Args:
        prefix: префикс имени (например, "clip", "music", "edit")
        extension: расширение файла (например, ".mp4", ".mp3")

    Returns:
        Уникальное имя файла вида "prefix_timestamp_uuid.ext"
    """
    timestamp = int(time.time())
    short_uuid = uuid.uuid4().hex[:8]
    # Нормализуем расширение
    if not extension.startswith("."):
        extension = f".{extension}"
    return f"{prefix}_{timestamp}_{short_uuid}{extension}"


def check_file_size(file_size: int | None, max_size_mb: int) -> bool:
    """
    Проверяет, что размер файла не превышает лимит.

    Args:
        file_size: размер файла в байтах (может быть None)
        max_size_mb: максимальный размер в мегабайтах

    Returns:
        True если файл в пределах лимита
    """
    if file_size is None:
        return True  # Если размер неизвестен — пропускаем
    max_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_bytes


def cleanup_files(file_paths: list[str]) -> int:
    """
    Удаляет список файлов. Пропускает несуществующие.

    Args:
        file_paths: список путей к файлам для удаления

    Returns:
        Количество успешно удалённых файлов
    """
    deleted = 0
    for path_str in file_paths:
        try:
            path = Path(path_str)
            if path.exists():
                path.unlink()
                deleted += 1
                logger.debug("Удалён файл: %s", path_str)
        except OSError as e:
            logger.warning("Не удалось удалить %s: %s", path_str, e)
    return deleted


def cleanup_old_outputs(max_age_hours: int = 24) -> int:
    """
    Удаляет выходные файлы старше заданного возраста.
    Используется для экономии места на диске (важно для Termux).

    Args:
        max_age_hours: максимальный возраст файла в часах

    Returns:
        Количество удалённых файлов
    """
    deleted = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    try:
        for file_path in OUTPUT_DIR.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted += 1
                    logger.debug("Удалён старый файл: %s", file_path)
    except OSError as e:
        logger.error("Ошибка очистки старых файлов: %s", e)

    if deleted:
        logger.info("Очищено %d старых файлов из %s", deleted, OUTPUT_DIR)

    return deleted


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в читаемый формат (ММ:СС).

    Args:
        seconds: длительность в секундах

    Returns:
        Строка вида "1:23"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в читаемый формат.

    Args:
        size_bytes: размер в байтах

    Returns:
        Строка вида "12.3 МБ"
    """
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} МБ"
EOF
echo "✅ bot/utils/helpers.py"

# ============================================================
# Финал
# ============================================================
echo ""
echo "🎉 =============================="
echo "   Все файлы успешно созданы!"
echo "=============================== 🎉"
echo ""
echo "📂 Структура проекта:"
echo "   $PROJECT_DIR/"
echo "   ├── bot/"
echo "   │   ├── __init__.py"
echo "   │   ├── config.py"
echo "   │   ├── main.py"
echo "   │   ├── handlers/"
echo "   │   │   ├── __init__.py"
echo "   │   │   ├── start.py"
echo "   │   │   ├── upload.py"
echo "   │   │   └── edit.py"
echo "   │   ├── keyboards/"
echo "   │   │   ├── __init__.py"
echo "   │   │   └── inline.py"
echo "   │   ├── services/"
echo "   │   │   ├── __init__.py"
echo "   │   │   ├── beat_detector.py"
echo "   │   │   ├── converter.py"
echo "   │   │   ├── effects.py"
echo "   │   │   └── video_editor.py"
echo "   │   ├── database/"
echo "   │   │   ├── __init__.py"
echo "   │   │   └── models.py"
echo "   │   └── utils/"
echo "   │       ├── __init__.py"
echo "   │       └── helpers.py"
echo "   ├── media/"
echo "   │   ├── clips/"
echo "   │   ├── music/"
echo "   │   ├── output/"
echo "   │   └── temp/"
echo "   ├── requirements.txt"
echo "   └── .env.example"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "  1️⃣  Установи зависимости:"
echo "      pip install -r requirements.txt"
echo ""
echo "  2️⃣  Создай .env файл:"
echo "      cp .env.example .env"
echo "      nano .env"
echo "      # Вставь свой BOT_TOKEN от @BotFather"
echo ""
echo "  3️⃣  Убедись, что FFmpeg установлен:"
echo "      pkg install ffmpeg"
echo ""
echo "  4️⃣  Запусти бота:"
echo "      python -m bot.main"
echo ""
echo "🚀 Удачи!"
