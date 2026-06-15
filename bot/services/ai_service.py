# -*- coding: utf-8 -*-
"""
ИИ-сервис на базе Google Gemini.
Парсит текстовые запросы пользователя в структурированные параметры для видеоредактора.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


async def parse_prompt_with_gemini(user_prompt: str) -> dict:
    """
    Разбирает текстовый запрос пользователя с помощью Google Gemini
    и возвращает JSON-структуру параметров для сборки эдита.

    Args:
        user_prompt: текст запроса пользователя (например: "сделай грустный эдит по Канеки под грустный рэп")

    Returns:
        Словарь с ключами:
        - video_search_query: поисковый запрос для YouTube (клипы)
        - music_search_query: поисковый запрос для YouTube (музыка)
        - style: стиль (hype/sad/chill/glitch)
        - text_overlay: текст для наложения (str или None)
        - color_theme: описание цветовой гаммы (для тонких настроек фильтров)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY не задан в переменных окружения")

    system_instruction = (
        "You are an AI video director for an Anime Edit Telegram Bot.\n"
        "Your task is to parse the user's natural language request for an anime video edit into a structured JSON config.\n"
        "The output MUST be a valid JSON object containing exactly the following keys:\n"
        "- 'video_search_query': a specific English search term for YouTube to find raw anime clips. "
        "For example, if the user asks for Kaneki, use 'Ken Kaneki Tokyo Ghoul raw clips' or 'Kaneki edit pack'. "
        "Always append 'raw clips' or 'edit pack' for better search results. Do not include words like 'anime' or 'video'.\n"
        "- 'music_search_query': a search term for YouTube to find the background audio (e.g. 'phonk slow down' or 'sad lofi instrumental').\n"
        "- 'style': one of the following styles: 'hype', 'sad', 'chill', 'glitch'. Map the user's request mood to one of these.\n"
        "- 'text_overlay': a short text string (up to 30 characters) to be displayed on the video (e.g., character name or key phrase). Return null if not specified or implied.\n"
        "- 'color_theme': a short description of the color vibe requested (e.g., 'neon red', 'dark contrast', 'warm vintage', 'black and white').\n"
        "Ensure the output is ONLY the JSON object, with no markdown code blocks or wrapper text."
    )

    prompt = f"User Request: {user_prompt}"

    # 1. Попытка использовать новый SDK google-genai
    try:
        from google import genai
        logger.info("Использование нового SDK google-genai")
        client = genai.Client(api_key=api_key)
        
        # Настройка конфигурации генерации
        config = {
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=config
        )
        result_text = response.text.strip()
        return json.loads(result_text)
        
    except Exception as e:
        logger.warning("Не удалось использовать новый SDK google-genai, пробуем устаревший google-generativeai. Ошибка: %s", e)
        
        # 2. Фолбэк на старый SDK google-generativeai
        try:
            import google.generativeai as legacy_genai
            logger.info("Использование устаревшего SDK google-generativeai")
            legacy_genai.configure(api_key=api_key)
            
            model = legacy_genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=system_instruction
            )
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2
                }
            )
            result_text = response.text.strip()
            return json.loads(result_text)
            
        except Exception as ex:
            logger.error("Все SDK Gemini вернули ошибку: %s", ex)
            raise RuntimeError(f"Не удалось подключиться к ИИ Gemini: {ex}")


async def generate_video_description(style: str, text_overlay: str | None) -> str:
    """
    Генерирует описание (подпись к видео) для соцсетей (TikTok/Shorts)
    на основе стиля и текста наложения.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return f"🎬 Аниме-эдит в стиле {style}!"

    prompt = f"Напиши короткую крутую подпись к аниме-видео для TikTok/Shorts. Стиль видео: {style}."
    if text_overlay:
        prompt += f" Текст на видео: {text_overlay}."
    prompt += " Добавь смайлики и подходящие популярные хэштеги (на русском и английском)."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config={"temperature": 0.7}
        )
        return response.text.strip()
    except Exception:
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return f"🎬 Аниме-эдит в стиле {style}!\n\n#anime #amv #edit"
