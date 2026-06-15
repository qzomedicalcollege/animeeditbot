# -*- coding: utf-8 -*-
"""
Загрузчик медиафайлов с YouTube через yt-dlp.
Используется для автоматического поиска и скачивания клипов и музыки по промптам.
"""

import asyncio
import logging
from pathlib import Path
from bot.config import TEMP_DIR

logger = logging.getLogger(__name__)


async def download_video_clips(query: str, output_dir: Path = TEMP_DIR) -> str | None:
    """
    Ищет и скачивает короткий ролик (edit pack) с YouTube по запросу.
    Ограничивает длительность до 3 минут (180 сек), чтобы скачивание шло быстро.

    Args:
        query: поисковый запрос (например: "Ken Kaneki raw clips")
        output_dir: директория для сохранения

    Returns:
        Путь к скачанному файлу или None в случае ошибки
    """
    # Шаблон имени файла: pack_ID.mp4
    output_template = str(output_dir / "pack_%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--max-duration", "180",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings"
    ]

    logger.info("Поиск и скачивание видео с YouTube: %s", query)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.error("Ошибка скачивания видео через yt-dlp: %s", err_msg)
            return None

        # Ищем скачанный файл в директории
        downloaded_files = list(output_dir.glob("pack_*.mp4"))
        if downloaded_files:
            # Сортируем по времени изменения (берем самый свежий)
            downloaded_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            logger.info("Видео успешно скачано: %s", downloaded_files[0])
            return str(downloaded_files[0])

        logger.error("Файл pack_*.mp4 не найден после работы yt-dlp")
        return None

    except Exception as e:
        logger.error("Исключение при скачивании видео с YouTube: %s", e)
        return None


async def download_audio_track(query: str, output_dir: Path = TEMP_DIR) -> str | None:
    """
    Ищет и скачивает аудиодорожку с YouTube по запросу, конвертирует в MP3.
    Ограничивает длительность до 4 минут (240 сек).

    Args:
        query: поисковый запрос музыки (например: "phonk slow down")
        output_dir: директория для сохранения

    Returns:
        Путь к скачанному аудиофайлу или None в случае ошибки
    """
    output_template = str(output_dir / "audio_%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        f"ytsearch1:{query}",
        "--max-duration", "240",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "-o", output_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings"
    ]

    logger.info("Поиск и скачивание аудио с YouTube: %s", query)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.error("Ошибка скачивания аудио через yt-dlp: %s", err_msg)
            return None

        # Ищем скачанный файл MP3
        downloaded_files = list(output_dir.glob("audio_*.mp3"))
        if downloaded_files:
            downloaded_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            logger.info("Аудио успешно скачано: %s", downloaded_files[0])
            return str(downloaded_files[0])

        logger.error("Файл audio_*.mp3 не найден после работы yt-dlp")
        return None

    except Exception as e:
        logger.error("Исключение при скачивании аудио с YouTube: %s", e)
        return None
