"""
Точка входа FastAPI приложения.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path

from .config import settings
from .api.routes import router

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Voice Denoiser API - REST API для очистки голосовых сообщений от шума.
    
    ## Возможности:
    * Очистка аудиофайлов от шума
    * Поддержка различных методов обработки
    * Пакетная обработка файлов
    * Скачивание обработанных файлов
    
    ## Поддерживаемые форматы:
    * WAV, MP3, OGG, FLAC, M4A, AAC
    
    ## Ограничения:
    * Максимальный размер файла: 50MB
    * Максимальное количество файлов в пакетном запросе: 10
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/processed", StaticFiles(directory=settings.PROCESSED_DIR), name="processed")

# Подключаем роутеры
app.include_router(router)

# Middleware для логирования
@app.middleware("http")
async def log_requests(request, call_next):
    """Middleware для логирования запросов."""
    import time
    import logging
    
    logger = logging.getLogger("api")
    
    start_time = time.time()
    
    # Логируем входящий запрос
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Обрабатываем запрос
    response = await call_next(request)
    
    # Логируем время выполнения
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    # Добавляем время выполнения в заголовки
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# События жизненного цикла
@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения."""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} запущен")
    print(f"📁 Загрузки: {settings.UPLOAD_DIR}")
    print(f"📁 Обработанные файлы: {settings.PROCESSED_DIR}")
    print(f"🌐 Документация: http://{settings.HOST}:{settings.PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Действия при остановке приложения."""
    print("👋 Приложение остановлено")


# Корневой эндпоинт
@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
        "endpoints": [
            {"path": "/api/health", "method": "GET", "description": "Проверка здоровья"},
            {"path": "/api/denoise", "method": "POST", "description": "Очистка аудио"},
            {"path": "/api/methods", "method": "GET", "description": "Доступные методы"},
            {"path": "/api/stats", "method": "GET", "description": "Статистика API"}
        ]
    }


if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )