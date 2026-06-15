# -*- coding: utf-8 -*-
"""
Умный детектор сцен на базе FFmpeg.
Анализирует видео, находит переходы между сценами и вырезает самые динамичные фрагменты
для автоматического создания эдита.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from bot.config import TEMP_DIR, CLIPS_DIR

logger = logging.getLogger(__name__)


async def extract_smart_clips(video_path: str, max_clips: int = 5) -> list[str]:
    """
    Анализирует длинное видео, находит стыки сцен и вырезает
    до max_clips лучших фрагментов (длительностью по 1.5 - 3.0 сек).
    Использует сверхбыструю нарезку через -c copy (без перекодирования).

    Args:
        video_path: путь к исходному видеофайлу
        max_clips: сколько клипов нужно получить

    Returns:
        Список путей к вырезанным клипам
    """
    clips_paths: list[str] = []
    
    # 1. Запуск детекции переходов сцен через FFmpeg
    # Фильтр select=gt(scene,0.2) находит кадры, где изменение картинки больше 20%
    # Выводим информацию в лог
    cmd = [
        "ffmpeg", "-i", video_path,
        "-filter_complex", "select='gt(scene,0.22)',metadata=print:file=-",
        "-f", "null", "-"
    ]
    
    logger.info("Запуск анализа сцен для: %s", video_path)
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Ждем выполнения с таймаутом 30 секунд
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        
        output = stderr.decode("utf-8", errors="replace") + stdout.decode("utf-8", errors="replace")
        
        # Парсим вывод на наличие временных меток и оценок изменений
        # Формат: pts_time:12.3456 и select_score:0.2567
        timestamps = re.findall(r"pts_time:([\d\.]+)", output)
        scores = re.findall(r"select_score:([\d\.]+)", output)
        
        scene_cuts = []
        for i in range(min(len(timestamps), len(scores))):
            scene_cuts.append({
                "time": float(timestamps[i]),
                "score": float(scores[i])
            })
            
        logger.info("Обнаружено %d переходов между сценами", len(scene_cuts))
        
        # Получаем общую длительность исходного видео через ffprobe
        duration = await _get_duration(video_path)
        if duration is None:
            duration = 30.0 # фоллбэк
            
        # Формируем интервалы между стыками сцен
        intervals = []
        
        # Если переходы не найдены, создаем равномерную сетку
        if not scene_cuts:
            step = duration / (max_clips + 1)
            for i in range(max_clips):
                start = step * (i + 0.5)
                intervals.append({"start": start, "duration": min(2.5, step), "score": 1.0})
        else:
            # Добавляем начало и конец видео для полноты картины
            cuts = [0.0] + [c["time"] for c in scene_cuts] + [duration]
            
            for i in range(len(cuts) - 1):
                start = cuts[i]
                end = cuts[i+1]
                scene_duration = end - start
                
                # Игнорируем слишком короткие сцены (< 1 сек) и берем только информативные
                if scene_duration >= 1.0:
                    # Если сцена слишком длинная (> 4 сек), берем только её начало
                    clip_dur = min(scene_duration, 3.0)
                    # Оценка сцены равна оценке перехода на ее границе (или 0.5 по умолчанию)
                    score = scene_cuts[i]["score"] if i < len(scene_cuts) else 0.5
                    
                    intervals.append({
                        "start": start + 0.1,  # Сдвигаем на 0.1 сек вперед, чтобы не захватывать стык
                        "duration": clip_dur,
                        "score": score
                    })
                    
        # Сортируем интервалы по динамике (score) и берем лучшие
        # Чтобы эдит не состоял из сцен, идущих подряд в одном месте, 
        # отсортируем обратно по времени, но отберем топ по score
        intervals.sort(key=lambda x: x["score"], reverse=True)
        top_intervals = intervals[:max_clips]
        top_intervals.sort(key=lambda x: x["start"]) # Сортируем по хронологии
        
        # 2. Нарезаем видео на фрагменты без перекодирования (-c copy)
        for idx, inter in enumerate(top_intervals):
            clip_name = f"auto_clip_{idx:02d}_{os.path.basename(video_path)}"
            clip_path = str(CLIPS_DIR / clip_name)
            
            # Команда быстрой нарезки
            cut_cmd = [
                "ffmpeg", "-y", "-ss", f"{inter['start']:.3f}",
                "-i", video_path,
                "-t", f"{inter['duration']:.3f}",
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                clip_path
            ]
            
            cut_proc = await asyncio.create_subprocess_exec(
                *cut_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await cut_proc.wait()
            
            if Path(clip_path).exists() and Path(clip_path).stat().st_size > 1000:
                clips_paths.append(clip_path)
                logger.info("Вырезан авто-клип %d: старт %.2f, длит %.2f", idx, inter['start'], inter['duration'])
                
        # Если почему-то нарезать не удалось, делаем фоллбэк на нарезку по времени
        if not clips_paths:
            logger.warning("Не удалось нарезать сцены по стыкам, делаем простую разбивку")
            step = duration / max_clips
            for idx in range(max_clips):
                start = idx * step
                clip_path = str(CLIPS_DIR / f"fallback_clip_{idx:02d}.mp4")
                cut_cmd = [
                    "ffmpeg", "-y", "-ss", f"{start:.3f}",
                    "-i", video_path,
                    "-t", "2.0",
                    "-c", "copy",
                    clip_path
                ]
                cut_proc = await asyncio.create_subprocess_exec(*cut_cmd)
                await cut_proc.wait()
                if Path(clip_path).exists():
                    clips_paths.append(clip_path)

        return clips_paths

    except Exception as e:
        logger.error("Ошибка при умной нарезке сцен: %s", e)
        return []


async def _get_duration(video_path: str) -> float | None:
    """Вспомогательная функция получения длительности через ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        val = stdout.decode().strip()
        return float(val) if val else None
    except Exception:
        return None
