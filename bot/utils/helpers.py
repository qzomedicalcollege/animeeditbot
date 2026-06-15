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
