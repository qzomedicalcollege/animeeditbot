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
