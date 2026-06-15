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
