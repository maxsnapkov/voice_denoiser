"""
Вспомогательные функции для бота.
"""

import os
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import logging
from datetime import datetime
import asyncio

from telegram import Update, Message
from telegram.ext import ContextTypes

from .config import settings

logger = logging.getLogger(__name__)


def get_file_size_mb(file_path: Path) -> float:
    """
    Получает размер файла в мегабайтах.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Размер в MB
    """
    return file_path.stat().st_size / (1024 * 1024)


def validate_file_size(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Проверяет размер файла.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        tuple[валиден_ли, сообщение_об_ошибке]
    """
    file_size_mb = get_file_size_mb(file_path)
    
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        return False, (
            f"❌ Файл слишком большой ({file_size_mb:.1f} MB).\n"
            f"Максимальный размер: {settings.MAX_FILE_SIZE_MB} MB."
        )
    
    return True, None


def validate_file_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет расширение файла.
    
    Args:
        filename: Имя файла
        
    Returns:
        tuple[валиден_ли, сообщение_об_ошибке]
    """
    ext = Path(filename).suffix.lower()
    
    if ext not in settings.SUPPORTED_FORMATS:
        return False, (
            f"❌ Неподдерживаемый формат файла: {ext}\n"
            f"Поддерживаемые форматы: {', '.join(settings.SUPPORTED_FORMATS)}"
        )
    
    return True, None


def generate_temp_filename(original_filename: str, user_id: int) -> str:
    """
    Генерирует уникальное имя для временного файла.
    
    Args:
        original_filename: Исходное имя файла
        user_id: ID пользователя
        
    Returns:
        Уникальное имя файла
    """
    timestamp = int(datetime.now().timestamp())
    hash_input = f"{user_id}_{original_filename}_{timestamp}"
    file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    ext = Path(original_filename).suffix
    return f"{user_id}_{file_hash}{ext}"


def cleanup_temp_files():
    """
    Очищает старые временные файлы.
    """
    try:
        current_time = datetime.now().timestamp()
        
        for file_path in settings.TEMP_DIR.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > settings.TEMP_FILE_LIFETIME:
                    file_path.unlink()
                    logger.info(f"Cleaned up temp file: {file_path.name}")
        
        # Считаем количество файлов
        file_count = len(list(settings.TEMP_DIR.iterdir()))
        
        if file_count > settings.MAX_TEMP_FILES:
            # Удаляем самые старые файлы
            files = sorted(
                settings.TEMP_DIR.iterdir(),
                key=lambda x: x.stat().st_mtime
            )
            
            for file_path in files[:file_count - settings.MAX_TEMP_FILES]:
                file_path.unlink()
                logger.info(f"Removed old file (max limit): {file_path.name}")
                
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")


def format_file_size(bytes_size: int) -> str:
    """
    Форматирует размер файла в читаемый вид.
    
    Args:
        bytes_size: Размер в байтах
        
    Returns:
        Форматированная строка
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в читаемый вид.
    
    Args:
        seconds: Длительность в секундах
        
    Returns:
        Форматированная строка
    """
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} мин {secs:.0f} сек"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} час {minutes} мин"


async def send_large_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    max_length: int = 4000
) -> Message:
    """
    Отправляет длинное сообщение, разбивая его на части.
    
    Args:
        update: Объект Update
        context: Контекст
        text: Текст сообщения
        max_length: Максимальная длина одной части
        
    Returns:
        Последнее отправленное сообщение
    """
    if len(text) <= max_length:
        return await update.effective_chat.send_message(text)
    
    messages = []
    current_chunk = ""
    
    # Разбиваем текст на строки
    lines = text.split('\n')
    
    for line in lines:
        # Проверяем, не превысит ли добавление строки максимальную длину
        if len(current_chunk) + len(line) + 1 > max_length:
            # Отправляем текущий чанк
            if current_chunk:
                msg = await update.effective_chat.send_message(current_chunk)
                messages.append(msg)
                current_chunk = ""
        
        # Добавляем строку к текущему чанку
        if current_chunk:
            current_chunk += "\n" + line
        else:
            current_chunk = line
    
    # Отправляем остаток
    if current_chunk:
        msg = await update.effective_chat.send_message(current_chunk)
        messages.append(msg)
    
    return messages[-1] if messages else None


async def download_file_from_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> Optional[Tuple[Path, str]]:
    """
    Скачивает файл из сообщения Telegram.
    
    Args:
        update: Объект Update
        context: Контекст
        
    Returns:
        tuple[путь_к_файлу, имя_файла] или None
    """
    message = update.message or update.channel_post
    if not message:
        return None
    
    # Получаем информацию о файле
    file_obj = None
    filename = None
    
    if message.voice:
        file_obj = message.voice
        filename = "voice_message.ogg"
    elif message.audio:
        file_obj = message.audio
        filename = message.audio.file_name or "audio_file.mp3"
    elif message.document:
        # Проверяем, что это аудио файл
        mime_type = message.document.mime_type or ""
        if not mime_type.startswith("audio/"):
            return None
        
        file_obj = message.document
        filename = message.document.file_name or "audio_file"
    
    if not file_obj or not filename:
        return None
    
    # Создаем временный файл
    temp_filename = generate_temp_filename(filename, update.effective_user.id)
    temp_path = settings.TEMP_DIR / temp_filename
    
    try:
        # Скачиваем файл
        file = await file_obj.get_file()
        await file.download_to_drive(temp_path)
        
        return temp_path, filename
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        # Удаляем временный файл в случае ошибки
        if temp_path.exists():
            temp_path.unlink()
        return None


def get_user_settings(user_id: int) -> dict:
    """
    Получает настройки пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Словарь с настройками
    """
    # В реальном приложении здесь была бы база данных
    # Сейчас используем простой словарь в контексте
    return {
        "method": "noisereduce",
        "sample_rate": 16000,
        "voice_type": "broadband",
        "format": "wav",
        "auto_delete": True
    }


def save_user_settings(user_id: int, settings: dict):
    """
    Сохраняет настройки пользователя.
    
    Args:
        user_id: ID пользователя
        settings: Настройки для сохранения
    """
    # В реальном приложении здесь была бы база данных
    # Сейчас просто логируем
    logger.info(f"Settings saved for user {user_id}: {settings}")


async def show_typing_indicator(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    interval: float = 5.0
):
    """
    Показывает индикатор набора текста.
    
    Args:
        update: Объект Update
        context: Контекст
        interval: Интервал в секундах
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Ждем указанный интервал
    await asyncio.sleep(min(interval, 5.0))


async def show_uploading_indicator(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Показывает индикатор загрузки файла.
    
    Args:
        update: Объект Update
        context: Контекст
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_audio"
    )


async def show_processing_indicator(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Показывает индикатор обработки.
    
    Args:
        update: Объект Update
        context: Контекст
    """
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="upload_audio"  # Используем тот же индикатор
    )


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        True если администратор
    """
    return user_id in settings.ADMIN_IDS