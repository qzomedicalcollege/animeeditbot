# -*- coding: utf-8 -*-
"""
Умный детектор сцен на базе FFmpeg.
Анализирует видео, находит переходы между сценами и вырезает самые динамичные фрагменты
для автоматического создания эдита. Поддерживает быстрый анализ длинных фильмов.
"""

import asyncio
import logging
import os
import re
import math
import struct
import wave
from pathlib import Path
from bot.config import TEMP_DIR, CLIPS_DIR

logger = logging.getLogger(__name__)


async def extract_smart_clips(video_path: str, max_clips: int = 5) -> list[str]:
    """
    Анализирует видео, находит стыки сцен и вырезает лучшие фрагменты.
    Автоматически переключается на оптимизированный алгоритм для длинных видео.
    """
    # Получаем общую длительность исходного видео
    duration = await _get_duration(video_path)
    if duration is None:
        duration = 30.0

    if duration > 180.0:
        return await _extract_smart_clips_long(video_path, duration, max_clips)
    else:
        return await _extract_smart_clips_short(video_path, duration, max_clips)


async def _find_loud_segments(video_path: str, duration: float, num_segments: int = 8) -> list[float]:
    """
    Извлекает аудиодорожку и находит стартовые таймкоды самых громких и динамичных сцен.
    """
    temp_wav = str(TEMP_DIR / "temp_movie_audio.wav")
    
    # Быстрое извлечение пережатого аудио (mono, 8000Hz, 16-bit PCM)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "8000", "-ac", "1",
        temp_wav
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await asyncio.wait_for(proc.wait(), timeout=60)
        
        if not os.path.exists(temp_wav):
            logger.warning("Аудиодорожка не извлечена, возвращаем пустой список сегментов")
            return []
            
        # Анализируем RMS громкости во временных окнах
        with wave.open(temp_wav, "rb") as w:
            nchannels, sampwidth, framerate, nframes = w.getparams()[:4]
            if nframes == 0:
                return []
            
            chunk_seconds = 5
            frames_per_chunk = chunk_seconds * framerate
            bytes_per_sample = sampwidth
            
            chunk_rms = []
            
            for i in range(0, nframes, frames_per_chunk):
                frames_to_read = min(frames_per_chunk, nframes - i)
                data = w.readframes(frames_to_read)
                if not data:
                    break
                
                fmt = f"<{len(data) // bytes_per_sample}h"
                try:
                    samples = struct.unpack(fmt, data)
                except Exception:
                    continue
                
                if not samples:
                    continue
                    
                sq_sum = sum(s*s for s in samples)
                rms = math.sqrt(sq_sum / len(samples))
                time_sec = i / float(framerate)
                chunk_rms.append((time_sec, rms))
                
        try:
            os.unlink(temp_wav)
        except OSError:
            pass
            
        # Объединяем 5-секундные чанки в 15-секундные окна
        window_rms = []
        for idx in range(len(chunk_rms) - 2):
            t = chunk_rms[idx][0]
            avg_rms = sum(chunk_rms[idx + k][1] for k in range(3)) / 3.0
            window_rms.append((t, avg_rms))
            
        # Сортируем окна по громкости
        window_rms.sort(key=lambda x: x[1], reverse=True)
        
        # Выбираем непересекающиеся окна (минимум 45 секунд между ними)
        selected_starts = []
        for start_t, rms in window_rms:
            if any(abs(start_t - s) < 45 for s in selected_starts):
                continue
            # Избегаем самого начала фильма (заставки) и титров в конце
            if start_t < 45 or start_t > duration - 90:
                continue
            selected_starts.append(start_t)
            if len(selected_starts) >= num_segments:
                break
                
        selected_starts.sort()
        return selected_starts
        
    except Exception as e:
        logger.error("Ошибка при анализе громкости аудио: %s", e)
        if os.path.exists(temp_wav):
            try:
                os.unlink(temp_wav)
            except OSError:
                pass
        return []


async def _extract_smart_clips_long(video_path: str, duration: float, max_clips: int = 5) -> list[str]:
    """
    Оптимизированный метод для длинных видео:
    1. Находит самые громкие участки фильма (где происходит экшен / диалоги).
    2. Извлекает короткие субклипы.
    3. Ищет точные переходы сцен внутри этих субклипов.
    4. Вырезает финальные сцены.
    """
    clips_paths: list[str] = []
    
    logger.info("Длинное видео (%.1f сек). Запуск поиска экшен-моментов...", duration)
    starts = await _find_loud_segments(video_path, duration, num_segments=max_clips * 2)
    
    if not starts:
        # Равномерные интервалы, если аудио-анализ не дал результатов
        step = duration / (max_clips + 1)
        starts = [step * (i + 0.5) for i in range(max_clips)]
        
    starts = starts[:max_clips * 2]
    
    for idx, start_t in enumerate(starts):
        subclip_name = f"subclip_{idx}_{os.path.basename(video_path)}"
        subclip_path = str(TEMP_DIR / subclip_name)
        
        # Быстрое вырезание субклипа в 15 секунд без перекодирования
        cut_cmd = [
            "ffmpeg", "-y", "-ss", f"{start_t:.3f}",
            "-i", video_path,
            "-t", "15.0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            subclip_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cut_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        
        if not Path(subclip_path).exists() or Path(subclip_path).stat().st_size < 1000:
            continue
            
        # Сверхбыстрый детектор стыков на 15-секундном фрагменте
        cmd = [
            "ffmpeg", "-i", subclip_path,
            "-filter_complex", "select='gt(scene,0.18)',metadata=print:file=-",
            "-f", "null", "-"
        ]
        
        pts_time = 2.0 # По умолчанию
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=8)
            output = stderr.decode("utf-8", errors="replace") + stdout.decode("utf-8", errors="replace")
            timestamps = re.findall(r"pts_time:([\d\.]+)", output)
            
            if timestamps:
                pts_time = float(timestamps[0])
                if len(timestamps) > 1 and pts_time < 0.5:
                    pts_time = float(timestamps[1])
        except Exception as e:
            logger.warning("Ошибка детекции стыков на субклипе: %s", e)
            
        try:
            os.unlink(subclip_path)
        except OSError:
            pass
            
        abs_start = start_t + pts_time
        
        # Нарезаем качественный финальный клип 2.5 сек с перекодированием
        clip_name = f"local_clip_{idx:02d}_{os.path.basename(video_path)}"
        clip_path = str(CLIPS_DIR / clip_name)
        
        final_cut_cmd = [
            "ffmpeg", "-y", "-ss", f"{abs_start:.3f}",
            "-i", video_path,
            "-t", "2.5",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-an",
            clip_path
        ]
        
        final_proc = await asyncio.create_subprocess_exec(
            *final_cut_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await final_proc.wait()
        
        if Path(clip_path).exists() and Path(clip_path).stat().st_size > 1000:
            clips_paths.append(clip_path)
            logger.info("Вырезан клип %d: старт %.2f", len(clips_paths), abs_start)
            
            if len(clips_paths) >= max_clips:
                break
                
    return clips_paths


async def _extract_smart_clips_short(video_path: str, duration: float, max_clips: int = 5) -> list[str]:
    """
    Классический метод детекции сцен для коротких роликов (до 3 минут).
    Анализирует видео целиком.
    """
    clips_paths: list[str] = []
    
    cmd = [
        "ffmpeg", "-i", video_path,
        "-filter_complex", "select='gt(scene,0.22)',metadata=print:file=-",
        "-f", "null", "-"
    ]
    
    logger.info("Запуск анализа сцен для короткого видео: %s", video_path)
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        
        output = stderr.decode("utf-8", errors="replace") + stdout.decode("utf-8", errors="replace")
        
        timestamps = re.findall(r"pts_time:([\d\.]+)", output)
        scores = re.findall(r"select_score:([\d\.]+)", output)
        
        scene_cuts = []
        for i in range(min(len(timestamps), len(scores))):
            scene_cuts.append({
                "time": float(timestamps[i]),
                "score": float(scores[i])
            })
            
        logger.info("Обнаружено %d переходов между сценами", len(scene_cuts))
        
        intervals = []
        if not scene_cuts:
            step = duration / (max_clips + 1)
            for i in range(max_clips):
                start = step * (i + 0.5)
                intervals.append({"start": start, "duration": min(2.5, step), "score": 1.0})
        else:
            cuts = [0.0] + [c["time"] for c in scene_cuts] + [duration]
            for i in range(len(cuts) - 1):
                start = cuts[i]
                end = cuts[i+1]
                scene_duration = end - start
                
                if scene_duration >= 1.0:
                    clip_dur = min(scene_duration, 3.0)
                    score = scene_cuts[i]["score"] if i < len(scene_cuts) else 0.5
                    intervals.append({
                        "start": start + 0.1,
                        "duration": clip_dur,
                        "score": score
                    })
                    
        intervals.sort(key=lambda x: x["score"], reverse=True)
        top_intervals = intervals[:max_clips]
        top_intervals.sort(key=lambda x: x["start"])
        
        for idx, inter in enumerate(top_intervals):
            clip_name = f"auto_clip_{idx:02d}_{os.path.basename(video_path)}"
            clip_path = str(CLIPS_DIR / clip_name)
            
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
        logger.error("Ошибка при умной нарезке сцен (короткое видео): %s", e)
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
