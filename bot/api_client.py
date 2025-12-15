"""
Клиент для работы с API Voice Denoiser.
"""

import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO
import json
import logging

from .config import settings

logger = logging.getLogger(__name__)


class APIClient:
    """Асинхронный клиент для работы с API."""
    
    def __init__(self, base_url: str = None, timeout: int = None):
        """
        Инициализация клиента.
        
        Args:
            base_url: Базовый URL API
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url or settings.API_URL
        self.timeout = timeout or settings.API_TIMEOUT
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Создает сессию при входе в контекстный менеджер."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": f"VoiceDenoiserBot/{settings.__version__}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает сессию при выходе из контекстного менеджера."""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """
        Проверяет доступность API.
        
        Returns:
            True если API доступен
        """
        try:
            async with self.session.get(f"{self.base_url}/api/health") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_available_methods(self) -> Dict[str, Any]:
        """
        Получает список доступных методов очистки.
        
        Returns:
            Словарь с методами
        """
        try:
            async with self.session.get(f"{self.base_url}/api/methods") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get methods: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting methods: {e}")
            return {}
    
    async def denoise_audio(
        self,
        audio_file: BinaryIO,
        filename: str,
        method: str = "noisereduce",
        sample_rate: Optional[int] = None,
        voice_type: Optional[str] = "broadband"
    ) -> Dict[str, Any]:
        """
        Отправляет аудио на очистку.
        
        Args:
            audio_file: Файловый объект с аудио
            filename: Имя файла
            method: Метод очистки
            sample_rate: Целевая частота дискретизации
            voice_type: Тип голоса
            
        Returns:
            Результат обработки
        """
        # Подготавливаем данные формы
        data = aiohttp.FormData()
        data.add_field(
            "audio_file",
            audio_file,
            filename=filename,
            content_type="audio/wav"
        )
        data.add_field("method", method)
        logger.info(method)
        
        if sample_rate:
            data.add_field("sample_rate", str(sample_rate))
        
        if method == "bandpass":
            data.add_field("voice_type", voice_type)
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/denoise",
                data=data
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Denoise failed: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Denoise request timed out")
            raise Exception("Request timeout")
        except Exception as e:
            logger.error(f"Denoise error: {e}")
            raise
    
    async def download_audio(self, url: str) -> bytes:
        """
        Скачивает обработанное аудио.
        
        Args:
            url: URL для скачивания
            
        Returns:
            Байты аудиофайла
        """
        try:
            # Если URL относительный, добавляем базовый URL
            if url.startswith("/"):
                url = f"{self.base_url}{url}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Download failed: {response.status}")
                    raise Exception(f"Download failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Получает статистику API.
        
        Returns:
            Статистика API
        """
        try:
            async with self.session.get(f"{self.base_url}/api/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    async def batch_denoise(
        self,
        files: list,
        method: str = "noisereduce"
    ) -> Dict[str, Any]:
        """
        Пакетная обработка файлов.
        
        Args:
            files: Список файлов (кортежи (имя, файловый объект))
            method: Метод очистки
            
        Returns:
            Результат пакетной обработки
        """
        data = aiohttp.FormData()
        data.add_field("method", method)
        
        for filename, file_obj in files:
            data.add_field(
                "audio_files",
                file_obj,
                filename=filename,
                content_type="audio/wav"
            )
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/denoise/batch",
                data=data
            ) as response:
                
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Batch denoise failed: {response.status} - {error_text}")
                    raise Exception(f"API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Batch denoise error: {e}")
            raise


# Создаем глобальный экземпляр клиента
api_client = APIClient()

# Утилиты для работы с API
async def check_api_health() -> tuple[bool, str]:
    """
    Проверяет доступность API и возвращает статус.
    
    Returns:
        tuple[доступен_ли, сообщение]
    """
    try:
        async with api_client as client:
            if await client.health_check():
                return True, "✅ API доступен"
            else:
                return False, "❌ API недоступен"
    except Exception as e:
        return False, f"❌ Ошибка подключения к API: {str(e)}"


async def get_methods_list() -> str:
    """
    Получает список методов и форматирует его для сообщения.
    
    Returns:
        Форматированная строка со списком методов
    """
    try:
        async with api_client as client:
            methods_data = await client.get_available_methods()
            
            if not methods_data:
                return "Не удалось получить список методов"
            
            methods = methods_data.get("available_methods", [])
            descriptions = methods_data.get("descriptions", {})
            default_method = methods_data.get("default_method", "noisereduce")
            
            result = "📋 Доступные методы очистки:\n\n"
            
            for method in methods:
                desc = descriptions.get(method, "Описание отсутствует")
                if method == default_method:
                    result += f"• <b>{method}</b> (по умолчанию)\n"
                else:
                    result += f"• <b>{method}</b>\n"
                result += f"  <i>{desc}</i>\n\n"
            
            return result
            
    except Exception as e:
        return f"❌ Ошибка при получении методов: {str(e)}"

async def process_audio_with_progress(
    file_path: Path,
    filename: str,
    method: str = "noisereduce",
    **kwargs
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Обрабатывает аудиофайл с показом прогресса.
    
    Args:
        file_path: Путь к файлу
        filename: Имя файла
        method: Метод очистки
        **kwargs: Дополнительные параметры
        
    Returns:
        tuple[аудио_данные, сообщение_об_ошибке]
    """
    try:
        # Открываем файл для отправки
        with open(file_path, 'rb') as f:
            async with api_client as client:
                # Отправляем на обработку
                result = await client.denoise_audio(
                    f,
                    filename,
                    method=method,
                    **kwargs
                )
                
                # Скачиваем результат
                download_url = result.get("download_url")
                if not download_url:
                    return None, "❌ Не удалось получить ссылку для скачивания"
                
                audio_data = await client.download_audio(download_url)
                
                # Формируем информацию о результате
                processing_time = result.get("processing_time", 0)
                original_info = result.get("original_info", {})
                
                info_message = (
                    f"✅ Обработка завершена!\n\n"
                    f"📊 Результаты:\n"
                    f"• Метод: <b>{result.get('method', 'unknown')}</b>\n"
                    f"• Время обработки: <b>{processing_time:.2f} сек</b>\n"
                    f"• Длительность: <b>{original_info.get('duration', 0):.2f} сек</b>\n"
                    f"• Частота: <b>{original_info.get('sample_rate', 0)} Гц</b>"
                )
                
                return audio_data, info_message
                
    except asyncio.TimeoutError:
        return None, "❌ Превышено время ожидания ответа от сервера"
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return None, f"❌ Ошибка обработки: {str(e)}"