"""
Конфигурация Telegram бота.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class BotSettings(BaseSettings):
    """Настройки Telegram бота."""
    __version__: str = "0.0.1"
    # Основные настройки
    BOT_TOKEN:str = os.getenv("BOT_TOKEN", "any")
    BOT_USERNAME:str = os.getenv("BOT_USERNAME", "any")
    
    # Настройки API
    API_URL:str = os.getenv("API_URL", "http://localhost:8000")
    API_TIMEOUT:int = int(os.getenv("API_TIMEOUT", "60"))
    
    # Настройки обработки
    MAX_FILE_SIZE_MB:int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FORMATS: List[str] = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"]
    
    # Настройки сообщений
    WELCOME_MESSAGE: str = (
        "Я бот для очистки голосовых сообщений от шума.\n\n"
        "Отправьте мне голосовое сообщение или аудиофайл, и я очищу его от фонового шума.\n\n"
        "📌 Поддерживаемые форматы: WAV, MP3, OGG, FLAC, M4A, AAC\n"
        f"📏 Максимальный размер: {MAX_FILE_SIZE_MB} MB\n\n"
        "Используйте /help для списка команд."
    )
    
    HELP_MESSAGE: str = (
        "📚 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/methods - Показать доступные методы очистки\n"
        "/settings - Настройки очистки\n"
        "/status - Статус работы бота\n"
        "/cancel - Отменить текущую операцию\n\n"
        "🎤 Отправьте голосовое сообщение или аудиофайл для очистки."
    )
    
    # Настройки хранения
    TEMP_DIR: Path = Path(__file__).parent.parent / "temp"
    MAX_TEMP_FILES: int = 100  # Максимальное количество временных файлов
    TEMP_FILE_LIFETIME: int = 3600  # Время жизни временных файлов в секундах (1 час)
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[Path] = Path(__file__).parent.parent / "logs" / "bot.log"
    
    # Администраторы (опционально)
    ADMIN_IDS: list = []
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Создаем необходимые директории
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        if self.LOG_FILE:
            self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Получаем username бота из токена
        if not self.BOT_USERNAME and self.BOT_TOKEN:
            from telegram import Bot
            try:
                bot = Bot(self.BOT_TOKEN)
                self.BOT_USERNAME = bot.get_me().username
            except:
                pass


# Создаем экземпляр настроек
settings = BotSettings()

# Экспортируем настройки
__all__ = ["settings"]