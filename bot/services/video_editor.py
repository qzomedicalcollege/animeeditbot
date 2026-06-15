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
    color_theme: str | None = None,
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
                style_filter = get_style_filters(style, segment_index, color_theme)

                # Собираем FFmpeg-команду для сегмента
                success = await _cut_and_apply_effects(
                    input_path=clip_path,
                    output_path=seg_path,
                    start_time=start_time,
                    duration=seg_duration,
                    style_filter=style_filter,
                    segment_index=segment_index,
                    keep_audio=(music_path == "original"),
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
        await _concatenate_segments(vertical_segments, concat_path, keep_audio=(music_path == "original"))

        # Шаг 5: Наложение аудио
        audio_path = str(TEMP_DIR / "with_audio.mp4")
        if music_path == "original":
            await _copy_file(concat_path, audio_path)
        else:
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
    динамичной нарезки. Максимальная общая длительность ограничена 20 секундами.

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

    # Ограничиваем общую длительность 20 секундами (идеально для Shorts/TikTok)
    limited_cuts: list[float] = []
    total_duration = 0.0
    for cut in cut_points:
        if total_duration + cut > 20.0:
            break
        limited_cuts.append(cut)
        total_duration += cut

    # Если получилось слишком мало сегментов, добавляем хотя бы минимальные
    min_segments = num_clips * 2
    if len(limited_cuts) < min_segments:
        # Сбрасываем и режем по 0.5-1.0 сек до 20 секунд
        limited_cuts = []
        total_duration = 0.0
        for _ in range(min_segments):
            dur = 1.0
            if total_duration + dur > 20.0:
                break
            limited_cuts.append(dur)
            total_duration += dur

    return limited_cuts



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
    keep_audio: bool = False,
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
        keep_audio: нужно ли сохранять оригинальный звук

    Returns:
        True если успешно
    """
    audio_args = ["-c:a", "aac", "-b:a", "128k"] if keep_audio else ["-an"]
    
    args = [
        "-ss", f"{start_time:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-vf", style_filter,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "28",  # Было 23, увеличили для сжатия
        *audio_args,
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
            "-crf", "28",
            *audio_args,
            "-r", str(OUTPUT_FPS),
            output_path,
        ]
        success, _ = await _run_ffmpeg(fallback_args, timeout=60)

    return success


async def _concatenate_segments(segments: list[str], output_path: str, keep_audio: bool = False) -> bool:
    """
    Конкатенация видео-сегментов через FFmpeg concat demuxer.

    Args:
        segments: список путей к сегментам
        output_path: путь для выходного файла
        keep_audio: сохранено ли аудио в сегментах

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

    audio_args = ["-c:a", "aac", "-b:a", "128k"] if keep_audio else []

    args = [
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",  # Было 21
        "-r", str(OUTPUT_FPS),
        "-pix_fmt", "yuv420p",
        *audio_args,
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
        "-crf", "26",  # Было 21
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
