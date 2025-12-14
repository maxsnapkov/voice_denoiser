"""
Маршруты (эндпоинты) API.
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import shutil
from pathlib import Path
import time

from ..config import settings
from ..core import Denoiser, AudioIO
from . import schemas, errors
from .dependencies import (
    get_denoiser,
    validate_upload_file,
    save_upload_file,
    process_audio_file,
    save_processed_audio,
    get_audio_info,
    generate_request_id,
    timing
)

app = FastAPI()
router = APIRouter(prefix=settings.API_PREFIX, tags=["audio"])

# Глобальные переменные для состояния приложения
start_time = time.time()


@router.get("/health", response_model=schemas.HealthCheck)
async def health_check():
    """Проверка здоровья API."""
    return schemas.HealthCheck(
        status="healthy",
        version=settings.APP_VERSION,
        uptime=time.time() - start_time
    )


@router.get("/methods")
async def get_available_methods(denoiser: Denoiser = Depends(get_denoiser)):
    """Возвращает список доступных методов очистки."""
    methods = denoiser.get_available_methods()
    descriptions = {
        method: denoiser.get_method_description(method)
        for method in methods
    }
    
    return {
        "available_methods": methods,
        "descriptions": descriptions,
        "default_method": settings.DEFAULT_METHOD
    }


@router.post("/denoise", response_model=schemas.DenoiseResponse)
async def denoise_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    method: schemas.DenoiseMethod = Form(schemas.DenoiseMethod.ADAPTIVE),
    sample_rate: Optional[int] = Form(None),
    voice_type: Optional[str] = Form("broadband"),
    denoiser: Denoiser = Depends(get_denoiser),
    request_id: str = Depends(generate_request_id),
    start_time: float = Depends(timing)
):
    """
    Очищает аудиофайл от шума.
    
    Поддерживаемые форматы: WAV, MP3, OGG, FLAC, M4A, AAC
    Максимальный размер файла: 50MB
    """
    # Валидация файла
    validated_file = await validate_upload_file(audio_file)
    
    # Сохраняем загруженный файл
    upload_path = await save_upload_file(validated_file)
    
    # Получаем информацию об исходном файле
    original_info = get_audio_info(upload_path)
    
    # Обрабатываем аудио
    result = await process_audio_file(
        upload_path,
        denoiser,
        method.value,
        sample_rate,
        voice_type
    )
    
    # Сохраняем обработанный файл
    processed_path = await save_processed_audio(
        result,
        validated_file.filename
    )
    
    # Формируем URL для скачивания
    download_url = f"{settings.API_PREFIX}/download/{processed_path.name}"
    
    # Вычисляем время обработки
    processing_time = time.time() - start_time
    
    # Очищаем временные файлы (в фоновом режиме)
    background_tasks.add_task(cleanup_temp_file, upload_path)
    
    # Формируем ответ
    audio_info = schemas.AudioInfo(**original_info)
    
    return schemas.DenoiseResponse(
        request_id=request_id,
        filename=processed_path.name,
        original_info=audio_info,
        method=result["method"],
        processing_time=processing_time,
        download_url=download_url
    )


@router.post("/denoise/batch", response_model=schemas.BatchProcessResponse)
async def denoise_batch(
    background_tasks: BackgroundTasks,
    audio_files: List[UploadFile] = File(..., description="Список аудиофайлов"),
    method: schemas.DenoiseMethod = Form(schemas.DenoiseMethod.ADAPTIVE),
    sample_rate: Optional[int] = Form(None),
    denoiser: Denoiser = Depends(get_denoiser),
    request_id: str = Depends(generate_request_id),
    start_time: float = Depends(timing)
):
    """
    Пакетная обработка нескольких аудиофайлов.
    
    Максимальное количество файлов: 10
    Максимальный размер каждого файла: 50MB
    """
    # Проверяем количество файлов
    if len(audio_files) > settings.MAX_UPLOAD_FILES:
        raise errors.APIError(
            status_code=400,
            error="Too many files",
            detail=f"Maximum {settings.MAX_UPLOAD_FILES} files allowed"
        )
    
    results = []
    download_urls = []
    temp_files = []
    
    for audio_file in audio_files:
        try:
            # Валидация файла
            validated_file = await validate_upload_file(audio_file)
            
            # Сохраняем загруженный файл
            upload_path = await save_upload_file(validated_file)
            temp_files.append(upload_path)
            
            # Обрабатываем аудио
            result = await process_audio_file(
                upload_path,
                denoiser,
                method.value,
                sample_rate
            )
            
            # Сохраняем обработанный файл
            processed_path = await save_processed_audio(
                result,
                validated_file.filename
            )
            
            # Формируем URL для скачивания
            download_url = f"{settings.API_PREFIX}/download/{processed_path.name}"
            download_urls.append(download_url)
            
            results.append({
                "filename": validated_file.filename,
                "status": "success",
                "processed_filename": processed_path.name,
                "processing_time": result["processing_time"]
            })
            
        except Exception as e:
            results.append({
                "filename": audio_file.filename,
                "status": "failed",
                "error": str(e)
            })
    
    # Очищаем временные файлы (в фоновом режиме)
    for temp_file in temp_files:
        background_tasks.add_task(cleanup_temp_file, temp_file)
    
    # Вычисляем общее время обработки
    total_processing_time = time.time() - start_time
    
    return schemas.BatchProcessResponse(
        request_id=request_id,
        total_files=len(audio_files),
        processed_files=len([r for r in results if r["status"] == "success"]),
        failed_files=len([r for r in results if r["status"] == "failed"]),
        processing_time=total_processing_time,
        results=results,
        download_urls=download_urls
    )


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    Скачивание обработанного аудиофайла.
    
    Args:
        filename: Имя файла для скачивания
    """
    file_path = settings.PROCESSED_DIR / filename
    
    # Проверяем существование файла
    if not file_path.exists():
        raise errors.FileNotFoundError(filename)
    
    # Проверяем безопасность пути
    try:
        file_path.resolve().relative_to(settings.PROCESSED_DIR.resolve())
    except ValueError:
        raise errors.APIError(
            status_code=400,
            error="Invalid filename",
            detail="Filename contains invalid path characters"
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/wav"
    )


@router.get("/info/{filename}")
async def get_file_info(filename: str):
    """
    Получение информации об обработанном файле.
    
    Args:
        filename: Имя файла
    """
    file_path = settings.PROCESSED_DIR / filename
    
    # Проверяем существование файла
    if not file_path.exists():
        raise errors.FileNotFoundError(filename)
    
    # Получаем информацию
    info = get_audio_info(file_path)
    
    return info


@router.delete("/cleanup")
async def cleanup_processed_files(days_old: int = 7):
    """
    Очистка старых обработанных файлов.
    
    Args:
        days_old: Удалять файлы старше N дней (по умолчанию 7)
    """
    import datetime
    
    deleted_files = []
    current_time = datetime.datetime.now()
    
    for file_path in settings.PROCESSED_DIR.iterdir():
        if file_path.is_file():
            # Получаем время последнего изменения
            mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            age = current_time - mtime
            
            # Удаляем если старый
            if age.days > days_old:
                file_path.unlink()
                deleted_files.append(file_path.name)
    
    return {
        "status": "success",
        "deleted_files": deleted_files,
        "deleted_count": len(deleted_files),
        "days_old": days_old
    }


# Вспомогательные функции
async def cleanup_temp_file(file_path: Path):
    """
    Удаляет временный файл.
    
    Args:
        file_path: Путь к временному файлу
    """
    try:
        if file_path.exists():
            file_path.unlink()
    except:
        pass  # Игнорируем ошибки при удалении


@router.get("/stats")
async def get_stats():
    """Получение статистики API."""
    import os
    
    # Статистика по директориям
    upload_count = len(list(settings.UPLOAD_DIR.iterdir()))
    processed_count = len(list(settings.PROCESSED_DIR.iterdir()))
    
    # Размеры директорий
    def get_dir_size(dir_path: Path) -> int:
        total = 0
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total
    
    upload_size_mb = get_dir_size(settings.UPLOAD_DIR) / (1024 * 1024)
    processed_size_mb = get_dir_size(settings.PROCESSED_DIR) / (1024 * 1024)
    
    return {
        "uptime_seconds": time.time() - start_time,
        "uploaded_files": upload_count,
        "processed_files": processed_count,
        "upload_dir_size_mb": round(upload_size_mb, 2),
        "processed_dir_size_mb": round(processed_size_mb, 2),
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS
    }


# Регистрация обработчиков ошибок
@app.exception_handler(errors.APIError)
async def api_error_handler(request, exc: errors.APIError):
    """Обработчик для APIError."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().dict()
    )


@app.exception_handler(errors.APIError)
async def generic_error_handler(request, exc: Exception):
    """Обработчик для общих ошибок."""
    error_response = errors.handle_generic_error(exc)
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )