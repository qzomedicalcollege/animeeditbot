# -*- coding: utf-8 -*-
"""
Модели базы данных SQLite через aiosqlite.

Таблицы:
- users: информация о пользователях (user_id, username, created_at)
- edits: история созданных эдитов (edit_id, user_id, style, created_at, file_path)
"""

import aiosqlite
import logging
from datetime import datetime

from bot.config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Инициализация базы данных: создаёт таблицы, если их нет.
    Вызывается при старте бота.
    """
    # Создаём директорию для БД, если нет
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Таблица эдитов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                edit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                style       TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                file_path   TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        await db.commit()
        logger.info("Таблицы БД созданы/проверены: %s", DB_PATH)


async def save_user(user_id: int, username: str = "") -> None:
    """
    Сохраняет или обновляет пользователя в базе.

    Args:
        user_id: Telegram user ID
        username: Telegram username
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
                """,
                (user_id, username, datetime.utcnow().isoformat()),
            )
            await db.commit()
    except Exception as e:
        logger.error("Ошибка сохранения пользователя %d: %s", user_id, e)


async def save_edit(user_id: int, style: str, file_path: str) -> int | None:
    """
    Сохраняет запись о созданном эдите.

    Args:
        user_id: Telegram user ID
        style: стиль эдита
        file_path: путь к выходному файлу

    Returns:
        ID созданной записи или None при ошибке
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                """
                INSERT INTO edits (user_id, style, file_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, style, file_path, datetime.utcnow().isoformat()),
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error("Ошибка сохранения эдита: %s", e)
        return None


async def get_user_edits(user_id: int, limit: int = 10) -> list[dict]:
    """
    Получает список эдитов пользователя.

    Args:
        user_id: Telegram user ID
        limit: максимум записей

    Returns:
        Список словарей с информацией об эдитах
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT edit_id, style, created_at, file_path
                FROM edits
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {
                    "edit_id": row["edit_id"],
                    "style": row["style"],
                    "created_at": row["created_at"],
                    "file_path": row["file_path"],
                }
                for row in rows
            ]
    except Exception as e:
        logger.error("Ошибка получения эдитов пользователя %d: %s", user_id, e)
        return []


async def get_stats() -> dict:
    """
    Получает общую статистику бота.

    Returns:
        Словарь: total_users, total_edits, edits_by_style
    """
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            # Общее число пользователей
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]

            # Общее число эдитов
            cursor = await db.execute("SELECT COUNT(*) FROM edits")
            total_edits = (await cursor.fetchone())[0]

            # Эдиты по стилям
            cursor = await db.execute(
                "SELECT style, COUNT(*) as cnt FROM edits GROUP BY style"
            )
            style_rows = await cursor.fetchall()
            edits_by_style = {row[0]: row[1] for row in style_rows}

            return {
                "total_users": total_users,
                "total_edits": total_edits,
                "edits_by_style": edits_by_style,
            }
    except Exception as e:
        logger.error("Ошибка получения статистики: %s", e)
        return {"total_users": 0, "total_edits": 0, "edits_by_style": {}}
