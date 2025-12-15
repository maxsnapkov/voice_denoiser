"""
Pydantic схемы для API.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime


class DenoiseMethod(str, Enum):
    """Доступные методы очистки."""
    BANDPASS = "bandpass"
    SPECTRAL_SUBTRACTION = "spectral_subtraction"
    WIENER = "wiener"
    NOISEREDUCE = "noisereduce"
    ADAPTIVE = "adaptive"


class AudioInfo(BaseModel):
    """Информация об аудиофайле."""
    filename: str
    duration: float = Field(..., description="Длительность в секундах")
    sample_rate: Union[int, str] = Field(..., description="Частота дискретизации")
    channels: int = Field(..., description="Количество каналов")
    size_bytes: int = Field(..., description="Размер файла в байтах")
    format: str = Field(..., description="Формат файла")
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "audio.wav",
                "duration": 5.25,
                "sample_rate": 16000,
                "channels": 1,
                "size_bytes": 168000,
                "format": "WAV"
            }
        }


class DenoiseRequest(BaseModel):
    """Запрос на очистку аудио."""
    method: DenoiseMethod = Field(
        default=DenoiseMethod.ADAPTIVE,
        description="Метод очистки аудио"
    )
    sample_rate: Optional[int] = Field(
        default=None,
        ge=8000,
        le=48000,
        description="Целевая частота дискретизации (если None - исходная)"
    )
    voice_type: Optional[str] = Field(
        default="broadband",
        description="Тип голоса для полосовой фильтрации (male/female/broadband)"
    )
    
    @validator('voice_type')
    def validate_voice_type(cls, v):
        if v not in ['male', 'female', 'broadband']:
            raise ValueError('voice_type должен быть одним из: male, female, broadband')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "method": "adaptive",
                "sample_rate": 16000,
                "voice_type": "broadband"
            }
        }


class DenoiseResponse(BaseModel):
    """Ответ после очистки аудио."""
    request_id: str = Field(..., description="ID запроса")
    filename: str = Field(..., description="Имя обработанного файла")
    original_info: AudioInfo = Field(..., description="Информация об исходном файле")
    method: str = Field(..., description="Использованный метод")
    processing_time: float = Field(..., description="Время обработки в секундах")
    download_url: str = Field(..., description="URL для скачивания обработанного файла")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "req_123456",
                "filename": "cleaned_audio.wav",
                "original_info": {
                    "filename": "audio.wav",
                    "duration": 5.25,
                    "sample_rate": 16000,
                    "channels": 1,
                    "size_bytes": 168000,
                    "format": "WAV"
                },
                "method": "adaptive",
                "processing_time": 1.23,
                "download_url": "/api/download/cleaned_audio.wav",
                "timestamp": "2024-01-15T12:30:45.123456"
            }
        }


class ErrorResponse(BaseModel):
    """Схема для ошибок API."""
    error: str = Field(..., description="Текст ошибки")
    detail: Optional[str] = Field(None, description="Детали ошибки")
    request_id: Optional[str] = Field(None, description="ID запроса")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "File not found",
                "detail": "The requested audio file was not found",
                "request_id": "req_123456"
            }
        }


class HealthCheck(BaseModel):
    """Схема для проверки здоровья API."""
    status: str = Field(..., description="Статус API")
    version: str = Field(..., description="Версия API")
    timestamp: datetime = Field(default_factory=datetime.now)
    uptime: float = Field(..., description="Время работы в секундах")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T12:30:45.123456",
                "uptime": 3600.5
            }
        }


class BatchProcessResponse(BaseModel):
    """Ответ для пакетной обработки."""
    request_id: str = Field(..., description="ID запроса")
    total_files: int = Field(..., description="Общее количество файлов")
    processed_files: int = Field(..., description="Количество обработанных файлов")
    failed_files: int = Field(..., description="Количество файлов с ошибками")
    processing_time: float = Field(..., description="Общее время обработки")
    results: List[Dict[str, Any]] = Field(..., description="Результаты по каждому файлу")
    download_urls: List[str] = Field(..., description="URL для скачивания обработанных файлов")
    
    class Config:
        schema_extra = {
            "example": {
                "request_id": "batch_req_123456",
                "total_files": 3,
                "processed_files": 3,
                "failed_files": 0,
                "processing_time": 3.45,
                "results": [
                    {"filename": "audio1.wav", "status": "success"},
                    {"filename": "audio2.wav", "status": "success"},
                    {"filename": "audio3.wav", "status": "success"}
                ],
                "download_urls": [
                    "/api/download/cleaned_audio1.wav",
                    "/api/download/cleaned_audio2.wav",
                    "/api/download/cleaned_audio3.wav"
                ]
            }
        }