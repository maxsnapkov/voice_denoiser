"""
Конфигурация приложения.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Основные настройки
    APP_NAME: str = "Voice Denoiser API"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Настройки сервера
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Лимиты файлов
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    MAX_UPLOAD_FILES: int = int(os.getenv("MAX_UPLOAD_FILES", "10"))
    ALLOWED_EXTENSIONS: List[str] = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"]
    
    # Настройки обработки аудио
    DEFAULT_SAMPLE_RATE: int = 16000
    DEFAULT_METHOD: str = "noisereduce"
    
    # Пути
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "processed"
    
    # CORS настройки (для веб-интерфейса)
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Создаем необходимые директории
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# Создаем экземпляр настроек
settings = Settings()

# Экспортируем настройки
__all__ = ["settings"]