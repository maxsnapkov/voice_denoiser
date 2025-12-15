"""
Зависимости (Dependency Injection) для API.
"""

from fastapi import Depends, HTTPException, UploadFile, File
from typing import List, Optional
import uuid
from pathlib import Path
import time

from ..config import settings
from ..core import Denoiser, AudioIO
from .errors import (
    FileTooLargeError,
    UnsupportedFormatError,
    ProcessingError
)


def get_denoiser() -> Denoiser:
    """Зависимость для получения экземпляра Denoiser."""
    return Denoiser(verbose=False)


def validate_file_extension(filename: str) -> bool:
    """Проверяет расширение файла."""
    ext = Path(filename).suffix.lower()
    return ext in settings.ALLOWED_EXTENSIONS


def validate_file_size(file_size: int) -> bool:
    """Проверяет размер файла."""
    max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Конвертируем в байты
    return file_size <= max_size


async def validate_upload_file(
    file: UploadFile,
    max_size_mb: Optional[int] = None
) -> UploadFile:
    """
    Валидация загружаемого файла.
    
    Args:
        file: Загружаемый файл
        max_size_mb: Максимальный размер в MB (если None - из настроек)
        
    Returns:
        Валидированный файл
        
    Raises:
        HTTPException: Если файл не проходит валидацию
    """
    # Проверка имени файла
    if not file.filename:
        raise UnsupportedFormatError(
            "unknown",
            settings.ALLOWED_EXTENSIONS
        )
    
    # Проверка расширения
    if not validate_file_extension(file.filename):
        raise UnsupportedFormatError(
            file.filename,
            settings.ALLOWED_EXTENSIONS
        )
    
    # Проверка размера
    max_size = max_size_mb or settings.MAX_FILE_SIZE_MB
    max_size_bytes = max_size * 1024 * 1024
    
    # Получаем размер файла
    content = await file.read()
    file_size = len(content)
    
    # Возвращаем курсор в начало
    await file.seek(0)
    
    if file_size > max_size_bytes:
        raise FileTooLargeError(max_size)
    
    return file


async def save_upload_file(
    file: UploadFile,
    upload_dir: Path = settings.UPLOAD_DIR
) -> Path:
    """
    Сохраняет загруженный файл на диск.
    
    Args:
        file: Загруженный файл
        upload_dir: Директория для сохранения
        
    Returns:
        Путь к сохраненному файлу
    """
    # Генерируем уникальное имя файла
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = upload_dir / unique_filename
    
    # Сохраняем файл
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    return file_path


async def process_audio_file(
    file_path: Path,
    denoiser: Denoiser,
    method: str = "adaptive",
    sample_rate: Optional[int] = None,
    voice_type: str = "broadband"
) -> dict:
    """
    Обрабатывает аудиофайл с помощью денойзера.
    
    Args:
        file_path: Путь к аудиофайлу
        denoiser: Экземпляр Denoiser
        method: Метод очистки
        sample_rate: Целевая частота дискретизации
        voice_type: Тип голоса
        
    Returns:
        Результаты обработки
        
    Raises:
        ProcessingError: Если обработка не удалась
    """
    try:
        # Параметры для метода
        kwargs = {}
        if method == "bandpass":
            kwargs["voice_type"] = voice_type
            
        
        # Обработка
        result = denoiser.denoise(
            file_path,
            sr=sample_rate,
            method=method,
            **kwargs
        )
        
        # Ресемплируем если нужно
        if sample_rate and sample_rate != result["sample_rate"]:
            from ..core import AudioIO
            result["audio"] = AudioIO.resample_audio(
                result["audio"],
                result["sample_rate"],
                sample_rate
            )
            result["sample_rate"] = sample_rate
        
        return result
        
    except Exception as e:
        raise ProcessingError(f"Failed to process audio: {str(e)}")


async def save_processed_audio(
    audio_data: dict,
    original_filename: str,
    processed_dir: Path = settings.PROCESSED_DIR
) -> Path:
    """
    Сохраняет обработанное аудио.
    
    Args:
        audio_data: Результаты обработки от Denoiser
        original_filename: Исходное имя файла
        processed_dir: Директория для сохранения
        
    Returns:
        Путь к сохраненному файлу
    """
    # Генерируем имя файла
    original_stem = Path(original_filename).stem
    method = audio_data.get("method", "denoised")
    output_filename = f"{original_stem}_{method}.wav"
    output_path = processed_dir / output_filename
    
    # Сохраняем
    from ..core import AudioIO
    AudioIO.save_audio(
        audio_data["audio"],
        output_path,
        audio_data["sample_rate"]
    )
    
    return output_path


def get_audio_info(file_path: Path) -> dict:
    """
    Получает информацию об аудиофайле.
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        Информация об аудио
    """
    return AudioIO.get_audio_info(file_path)


def generate_request_id() -> str:
    """Генерирует уникальный ID запроса."""
    return f"req_{uuid.uuid4().hex[:8]}"


def timing() -> float:
    """Возвращает текущее время для замера продолжительности."""
    return time.time()