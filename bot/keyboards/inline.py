# -*- coding: utf-8 -*-
"""
Инлайн-клавиатуры бота.
Главное меню, выбор стиля, подтверждение, отмена.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import STYLES


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Создать эдит", callback_data="create_edit")
    )
    builder.row(
        InlineKeyboardButton(text="📖 Помощь", callback_data="help_info")
    )
    return builder.as_markup()


def get_mode_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора режима создания эдита."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Загрузить файлы вручную", callback_data="mode_manual")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Использовать ИИ-режиссер (Авто)", callback_data="mode_auto")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()



def get_upload_clips_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время загрузки клипов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="clips_done")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля эдита."""
    builder = InlineKeyboardBuilder()
    for style_key, style_name in STYLES.items():
        builder.row(
            InlineKeyboardButton(
                text=style_name,
                callback_data=f"style:{style_key}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения / пропуска текста."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏩ Пропустить", callback_data="skip_text")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

