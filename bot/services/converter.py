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
