# -*- coding: utf-8 -*-
"""
Обработчик загрузки видео и аудио файлов.
FSM-состояния для пошагового процесса: клипы → музыка → стиль → генерация.
"""

import logging
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import (
    CLIPS_DIR,
    MUSIC_DIR,
    MAX_CLIPS_PER_EDIT,
    MAX_VIDEO_DURATION,
    MAX_FILE_SIZE_MB,
)
from bot.keyboards.inline import (
    get_upload_clips_keyboard,
    get_style_keyboard,
    get_cancel_keyboard,
    get_mode_keyboard,
)
from bot.services.converter import get_video_duration
from bot.utils.helpers import generate_unique_filename, check_file_size

logger = logging.getLogger(__name__)

router = Router(name="upload")


# === FSM-состояния ===
class EditStates(StatesGroup):
    """Состояния конечного автомата для создания эдита."""
    waiting_mode = State()       # Выбор режима (manual / auto / local)
    waiting_local_file = State() # Ожидание выбора локального видеофайла
    waiting_ai_prompt = State()  # Ожидание ввода текстового промпта
    waiting_clips = State()      # Ожидание загрузки клипов
    waiting_music = State()      # Ожидание загрузки музыки
    waiting_style = State()      # Ожидание выбора стиля
    waiting_text = State()       # Ожидание текста для наложения
    processing = State()         # Обработка видео


# === Начало создания эдита ===
@router.callback_query(F.data == "create_edit")
async def start_edit_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало процесса создания эдита — переход к выбору режима."""
    await state.clear()
    await state.update_data(
        mode=None,
        clips=[],
        music_path=None,
        style=None,
        text_overlay=None,
        ai_prompt=None
    )
    await state.set_state(EditStates.waiting_mode)

    await callback.message.edit_text(
        "🎬 <b>Выбери режим создания эдита:</b>\n\n"
        "📥 <b>Ручной режим:</b> Вы сами отправляете видео-нарезки и фоновый трек.\n\n"
        "🤖 <b>ИИ-Режиссер (Авто):</b> Вы пишите текстовый промпт, а ИИ автоматически находит клипы на YouTube, подбирает музыку, режет в ритм и накладывает эффекты!",
        reply_markup=get_mode_keyboard(),
    )
    await callback.answer()




# === Выбор ручного режима ===
@router.callback_query(F.data == "mode_manual", EditStates.waiting_mode)
async def handle_mode_manual(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к ручному режиму — загрузке клипов."""
    await state.update_data(mode="manual")
    await state.set_state(EditStates.waiting_clips)

    await callback.message.edit_text(
        "📹 <b>Шаг 1/4 — Загрузка клипов</b>\n\n"
        f"Отправь мне видео-клипы (до {MAX_CLIPS_PER_EDIT} штук).\n"
        f"Каждый клип должен быть не длиннее {MAX_VIDEO_DURATION} сек.\n\n"
        "Когда загрузишь все клипы, нажми <b>«✅ Готово»</b> 👇",
        reply_markup=get_upload_clips_keyboard(),
    )
    await callback.answer()


# === Выбор ИИ-режима ===
@router.callback_query(F.data == "mode_auto", EditStates.waiting_mode)
async def handle_mode_auto(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к ИИ-режиму — ожидание ввода промпта."""
    await state.update_data(mode="auto")
    await state.set_state(EditStates.waiting_ai_prompt)

    await callback.message.edit_text(
        "🤖 <b>ИИ-Режиссер: Ввод промпта</b>\n\n"
        "Опиши эдит, который ты хочешь получить.\n"
        "Например:\n"
        "• <i>«крутой эдит с Зеницу, под динамичный фонк»</i>\n"
        "• <i>«грустный эдит про Канеки, музыка лоу-фай»</i>\n"
        "• <i>«эдит с боем Наруто и Саске, рок-музыка»</i>\n\n"
        "ИИ сам найдет видео и трек на YouTube, вырежет лучшие кадры и смонтирует ролик!",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


# === Выбор локального режима ===
@router.callback_query(F.data == "mode_local", EditStates.waiting_mode)
@router.callback_query(F.data == "refresh_files", EditStates.waiting_local_file)
async def handle_mode_local(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к выбору локального файла."""
    from bot.config import RAW_DIR
    from bot.keyboards.inline import get_local_files_keyboard
    await state.update_data(mode="local")
    await state.set_state(EditStates.waiting_local_file)

    supported_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".3gp"}
    video_files = []
    if RAW_DIR.exists():
        video_files = [
            str(f) for f in RAW_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

    video_files.sort()
    await state.update_data(local_files=video_files)

    if not video_files:
        await callback.message.edit_text(
            "🎬 <b>Нарезка локального фильма</b>\n\n"
            "⚠️ <b>В папке нет подходящих видеофайлов!</b>\n\n"
            "Пожалуйста, скопируйте видеофайлы (фильмы, серии аниме в форматах .mp4, .mkv) "
            "в папку проекта <code>media/raw</code> на вашем устройстве.\n\n"
            "После копирования нажмите кнопку <b>«🔄 Обновить список»</b> 👇",
            reply_markup=get_local_files_keyboard([]),
        )
    else:
        await callback.message.edit_text(
            "🎬 <b>Нарезка локального фильма</b>\n\n"
            f"Найдено видеофайлов: {len(video_files)}\n"
            "Выберите файл для создания нарезки 👇",
            reply_markup=get_local_files_keyboard(video_files),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("select_file:"), EditStates.waiting_local_file)
async def handle_local_file_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор локального видеофайла."""
    data = await state.get_data()
    video_files = data.get("local_files", [])
    
    try:
        idx = int(callback.data.split(":")[1])
        selected_file = video_files[idx]
    except (IndexError, ValueError) as e:
        logger.error("Ошибка выбора файла: %s", e)
        await callback.answer("❌ Ошибка выбора файла. Попробуйте обновить список.", show_alert=True)
        return

    filename = Path(selected_file).name
    await state.update_data(clips=[selected_file])
    await state.set_state(EditStates.waiting_music)

    from bot.keyboards.inline import get_local_music_keyboard
    await callback.message.edit_text(
        f"📁 Выбран файл: <b>{filename}</b>\n\n"
        "🎵 <b>Шаг 2/4 — Загрузка музыки</b>\n\n"
        "Отправьте аудио-файл (.mp3, .wav и т.д.) или нажмите кнопку <b>«🔊 Оригинальный звук фильма»</b> 👇",
        reply_markup=get_local_music_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "music_original", EditStates.waiting_music)
async def handle_original_music(callback: CallbackQuery, state: FSMContext) -> None:
    """Использование оригинального звука видео вместо наложения музыки."""
    await state.update_data(music_path="original")
    await state.set_state(EditStates.waiting_style)

    await callback.message.edit_text(
        "🔊 Выбран оригинальный звук фильма.\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )
    await callback.answer()


# === Ввод промпта ИИ ===
@router.message(EditStates.waiting_ai_prompt, F.text)
async def handle_ai_prompt_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Получение промпта для ИИ и запуск генерации."""
    prompt = message.text.strip()
    if len(prompt) < 5:
        await message.answer("⚠️ Описание слишком короткое! Напиши хотя бы несколько слов.")
        return

    await state.update_data(ai_prompt=prompt)
    
    # Чтобы не дублировать код генерации, импортируем его из edit
    from bot.handlers.edit import _start_generation
    await _start_generation(message, state, bot, reply_to_message=True)


# === Загрузка видео-клипов ===

@router.message(EditStates.waiting_clips, F.video)
async def handle_video_upload(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка загруженного видео-клипа."""
    data = await state.get_data()
    clips: list[str] = data.get("clips", [])

    # Проверка количества клипов
    if len(clips) >= MAX_CLIPS_PER_EDIT:
        await message.answer(
            f"⚠️ Максимум {MAX_CLIPS_PER_EDIT} клипов! "
            "Нажми <b>«✅ Готово»</b>, чтобы продолжить.",
            reply_markup=get_upload_clips_keyboard(),
        )
        return

    video = message.video

    # Проверка размера файла
    if not check_file_size(video.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Проверка длительности
    if video.duration and video.duration > MAX_VIDEO_DURATION:
        await message.answer(
            f"⚠️ Клип слишком длинный ({video.duration} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    # Скачиваем файл
    filename = generate_unique_filename("clip", ".mp4")
    file_path = CLIPS_DIR / filename

    try:
        file = await bot.get_file(video.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания видео: %s", e)
        await message.answer("❌ Ошибка при скачивании видео. Попробуй ещё раз.")
        return

    # Дополнительная проверка длительности через FFmpeg
    duration = await get_video_duration(str(file_path))
    if duration is not None and duration > MAX_VIDEO_DURATION:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Клип слишком длинный ({duration:.1f} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    clips.append(str(file_path))
    await state.update_data(clips=clips)

    await message.answer(
        f"✅ Клип #{len(clips)} загружен!\n"
        f"Всего клипов: {len(clips)}/{MAX_CLIPS_PER_EDIT}\n\n"
        "Загрузи ещё или нажми <b>«✅ Готово»</b>.",
        reply_markup=get_upload_clips_keyboard(),
    )


@router.message(EditStates.waiting_clips, F.document)
async def handle_video_as_document(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка видео, отправленного как документ."""
    doc = message.document

    # Проверяем что это видео по mime-type
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        await message.answer("⚠️ Отправь видео-файл, а не документ другого типа.")
        return

    # Проверка размера
    if not check_file_size(doc.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Скачиваем
    ext = Path(doc.file_name).suffix if doc.file_name else ".mp4"
    filename = generate_unique_filename("clip", ext)
    file_path = CLIPS_DIR / filename

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания документа: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    # Проверка длительности
    duration = await get_video_duration(str(file_path))
    if duration is not None and duration > MAX_VIDEO_DURATION:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Клип слишком длинный ({duration:.1f} сек)! "
            f"Максимум {MAX_VIDEO_DURATION} сек."
        )
        return

    data = await state.get_data()
    clips: list[str] = data.get("clips", [])

    if len(clips) >= MAX_CLIPS_PER_EDIT:
        file_path.unlink(missing_ok=True)
        await message.answer(
            f"⚠️ Максимум {MAX_CLIPS_PER_EDIT} клипов!",
            reply_markup=get_upload_clips_keyboard(),
        )
        return

    clips.append(str(file_path))
    await state.update_data(clips=clips)

    await message.answer(
        f"✅ Клип #{len(clips)} загружен!\n"
        f"Всего клипов: {len(clips)}/{MAX_CLIPS_PER_EDIT}\n\n"
        "Загрузи ещё или нажми <b>«✅ Готово»</b>.",
        reply_markup=get_upload_clips_keyboard(),
    )


@router.message(EditStates.waiting_clips)
async def handle_invalid_clip(message: Message) -> None:
    """Подсказка, если пользователь отправил не видео."""
    await message.answer(
        "⚠️ Отправь видео-файл! Принимаются .mp4, .mov, .avi и другие форматы."
    )


# === Завершение загрузки клипов → переход к музыке ===
@router.callback_query(F.data == "clips_done", EditStates.waiting_clips)
async def clips_done(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь закончил загрузку клипов, переход к загрузке музыки."""
    data = await state.get_data()
    clips = data.get("clips", [])

    if not clips:
        await callback.answer("❌ Загрузи хотя бы один клип!", show_alert=True)
        return

    await state.set_state(EditStates.waiting_music)

    await callback.message.edit_text(
        f"📹 Загружено клипов: {len(clips)}\n\n"
        "🎵 <b>Шаг 2/4 — Загрузка музыки</b>\n\n"
        "Отправь мне аудио-файл (трек для эдита).\n"
        "Поддерживаются: .mp3, .wav, .ogg, .m4a",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


# === Загрузка аудио ===
@router.message(EditStates.waiting_music, F.audio)
async def handle_audio_upload(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка загруженного аудио-файла."""
    audio = message.audio

    # Проверка размера
    if not check_file_size(audio.file_size, MAX_FILE_SIZE_MB):
        await message.answer(
            f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ."
        )
        return

    # Скачиваем аудио
    ext = ".mp3"
    if audio.file_name:
        ext = Path(audio.file_name).suffix or ".mp3"
    filename = generate_unique_filename("music", ext)
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(audio.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания аудио: %s", e)
        await message.answer("❌ Ошибка при скачивании аудио. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music, F.voice)
async def handle_voice_as_music(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка голосового сообщения как аудио."""
    voice = message.voice

    filename = generate_unique_filename("music", ".ogg")
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(voice.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания голосового: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music, F.document)
async def handle_audio_as_document(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка аудио, отправленного как документ."""
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("audio/"):
        await message.answer("⚠️ Отправь аудио-файл (.mp3, .wav, .ogg, .m4a).")
        return

    if not check_file_size(doc.file_size, MAX_FILE_SIZE_MB):
        await message.answer(f"⚠️ Файл слишком большой! Максимум {MAX_FILE_SIZE_MB} МБ.")
        return

    ext = Path(doc.file_name).suffix if doc.file_name else ".mp3"
    filename = generate_unique_filename("music", ext)
    file_path = MUSIC_DIR / filename

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=file_path)
    except Exception as e:
        logger.error("Ошибка скачивания документа: %s", e)
        await message.answer("❌ Ошибка при скачивании. Попробуй ещё раз.")
        return

    await state.update_data(music_path=str(file_path))
    await state.set_state(EditStates.waiting_style)

    await message.answer(
        "🎵 Аудио загружено!\n\n"
        "🎨 <b>Шаг 3/4 — Выбор стиля</b>\n\n"
        "Выбери стиль для своего эдита 👇",
        reply_markup=get_style_keyboard(),
    )


@router.message(EditStates.waiting_music)
async def handle_invalid_music(message: Message) -> None:
    """Подсказка, если отправлено не аудио."""
    await message.answer(
        "⚠️ Отправь аудио-файл! Принимаются .mp3, .wav, .ogg, .m4a."
    )


# === Отмена ===
@router.callback_query(F.data == "cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена текущего процесса создания эдита."""
    # Очищаем загруженные файлы
    data = await state.get_data()
    for clip_path in data.get("clips", []):
        Path(clip_path).unlink(missing_ok=True)
    music = data.get("music_path")
    if music:
        Path(music).unlink(missing_ok=True)

    await state.clear()

    await callback.message.edit_text(
        "❌ Создание эдита отменено.\n\n"
        "Нажми /start, чтобы начать заново."
    )
    await callback.answer("Отменено")
