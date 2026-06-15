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
    mode = data.get("mode", "manual")
    clips = data.get("clips", [])
    music_path = data.get("music_path")
    style = data.get("style")
    text_overlay = data.get("text_overlay")
    ai_prompt = data.get("ai_prompt")
    color_theme = None

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

    downloaded_raw_files = []

    try:
        if mode == "auto":
            if not ai_prompt:
                raise ValueError("Описание для ИИ не найдено!")

            # Шаг 0.1: Парсим промпт через Gemini
            await bot.edit_message_text(
                "🤖 ИИ-Режиссер анализирует запрос через Gemini...",
                chat_id=chat_id,
                message_id=progress_msg.message_id,
            )
            from bot.services.ai_service import parse_prompt_with_gemini
            ai_config = await parse_prompt_with_gemini(ai_prompt)
            logger.info("Gemini parsed config: %s", ai_config)

            style = ai_config.get("style", "hype")
            text_overlay = ai_config.get("text_overlay")
            video_query = ai_config.get("video_search_query")
            music_query = ai_config.get("music_search_query")
            color_theme = ai_config.get("color_theme")

            if not video_query or not music_query:
                raise RuntimeError("ИИ не смог определить запросы для поиска видео/музыки")

            # Шаг 0.2: Скачиваем видео
            await bot.edit_message_text(
                f"🔍 Ищу и скачиваю видео-материалы по запросу:\n«{video_query}»...",
                chat_id=chat_id,
                message_id=progress_msg.message_id,
            )
            from bot.services.downloader import download_video_clips, download_audio_track
            raw_video = await download_video_clips(video_query)
            if not raw_video:
                raise RuntimeError(f"Не удалось найти или скачать видео-пак по запросу: {video_query}")
            downloaded_raw_files.append(raw_video)

            # Шаг 0.3: Скачиваем музыку
            await bot.edit_message_text(
                f"🎵 Ищу и скачиваю фоновую музыку:\n«{music_query}»...",
                chat_id=chat_id,
                message_id=progress_msg.message_id,
            )
            raw_music = await download_audio_track(music_query)
            if not raw_music:
                raise RuntimeError(f"Не удалось найти или скачать фоновую музыку по запросу: {music_query}")
            downloaded_raw_files.append(raw_music)
            music_path = raw_music

            # Шаг 0.4: Авто-нарезка по вектору движения
            await bot.edit_message_text(
                "✂️ Детектор движения нарезает лучшие экшен-кадры...",
                chat_id=chat_id,
                message_id=progress_msg.message_id,
            )
            from bot.services.scene_detector import extract_smart_clips
            clips = await extract_smart_clips(raw_video, max_clips=5)
            if not clips:
                raise RuntimeError("Не удалось нарезать сцены из видео-пака")

        elif mode == "local":
            if not clips:
                raise ValueError("Не выбран файл для нарезки!")
            raw_video = clips[0]

            await bot.edit_message_text(
                "✂️ Анализирую фильм и вырезаю лучшие экшен-моменты...",
                chat_id=chat_id,
                message_id=progress_msg.message_id,
            )
            from bot.services.scene_detector import extract_smart_clips
            clips = await extract_smart_clips(raw_video, max_clips=5)
            if not clips:
                raise RuntimeError("Не удалось нарезать сцены из видеофайла")

        # Шаг 1: Детекция битов (или оригинальный звук)
        if music_path == "original":
            # Для оригинального звука используем равномерную нарезку по размеру нарезанных сцен
            beats = [i * 2.5 for i in range(len(clips) + 1)]
        else:
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
            color_theme=color_theme,
        )

        if not result or not Path(result).exists():
            raise FileNotFoundError("Выходной файл не создан")

        # Шаг 3: Отправка результата
        await bot.edit_message_text(
            "📤 Отправляю готовое видео...",
            chat_id=chat_id,
            message_id=progress_msg.message_id,
        )

        # Генерация ИИ-описания для видео
        caption = f"🎬 <b>Аниме-эдит готов!</b>\n"
        if mode == "auto":
            try:
                from bot.services.ai_service import generate_video_description
                ai_desc = await generate_video_description(style, text_overlay)
                caption += f"\n📝 <i>ИИ-Описание:</i>\n{ai_desc}\n"
            except Exception as e:
                logger.warning("Ошибка генерации ИИ-описания: %s", e)
        
        caption += (
            f"\n🎨 Стиль: {STYLES.get(style, style)}\n"
            f"📹 Клипов: {len(clips)}\n"
            f"🎵 Битов: {len(beats)}"
        )

        video_file = FSInputFile(result, filename=f"anime_edit_{style}.mp4")
        await bot.send_video(
            chat_id=chat_id,
            video=video_file,
            caption=caption,
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
        # Очищаем временные файлы (клипы и музыку), не затрагивая исходники в media/raw
        temp_files = []
        for c in clips:
            if "media/raw" not in str(c):
                temp_files.append(c)
        if music_path and music_path != "original" and "media/raw" not in str(music_path):
            temp_files.append(music_path)
        
        # Также очищаем скачанные исходные файлы
        temp_files.extend(downloaded_raw_files)
        cleanup_files(temp_files)
        await state.clear()

