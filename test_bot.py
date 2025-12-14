#!/usr/bin/env python3
"""
Тесты для Telegram бота.
"""

import sys
from pathlib import Path
import tempfile
import asyncio

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from telegram.ext import Application
from bot import handlers, utils
from bot.config import settings


def test_utils():
    """Тест вспомогательных функций."""
    print("🧪 Тестирование утилит...")
    
    # Тест валидации расширений
    is_valid, error = utils.validate_file_extension("test.wav")
    assert is_valid == True
    assert error is None
    
    is_valid, error = utils.validate_file_extension("test.txt")
    assert is_valid == False
    assert error is not None
    
    # Тест генерации имени файла
    filename = utils.generate_temp_filename("test.wav", 12345)
    assert filename.startswith("12345_")
    assert filename.endswith(".wav")
    
    print("  ✅ Утилиты работают корректно")


def test_file_operations():
    """Тест операций с файлами."""
    print("\n🧪 Тестирование операций с файлами...")
    
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(suffix=".wav", dir=settings.TEMP_DIR) as tmp:
        file_path = Path(tmp.name)
        
        # Тест размера файла
        size_mb = utils.get_file_size_mb(file_path)
        assert size_mb >= 0
        
        # Тест валидации размера (маленький файл должен проходить)
        is_valid, error = utils.validate_file_size(file_path)
        assert is_valid == True
        
        # Тест форматирования размера
        formatted = utils.format_file_size(1024)
        assert "KB" in formatted
        
        # Тест форматирования длительности
        formatted = utils.format_duration(65.5)
        assert "мин" in formatted
    
    print("  ✅ Операции с файлами работают корректно")


def test_config():
    """Тест конфигурации."""
    print("\n🧪 Тестирование конфигурации...")
    
    assert hasattr(settings, "BOT_TOKEN")
    assert hasattr(settings, "API_URL")
    assert hasattr(settings, "MAX_FILE_SIZE_MB")
    
    # Проверяем создание директорий
    assert settings.TEMP_DIR.exists()
    
    print("  ✅ Конфигурация загружена корректно")


async def test_api_client():
    """Тест API клиента."""
    print("\n🧪 Тестирование API клиента...")
    
    from bot.api_client import APIClient, check_api_health
    
    # Проверяем доступность API
    available, message = await check_api_health()
    print(f"  API доступен: {available}")
    print(f"  Сообщение: {message}")
    
    # Тест получения методов
    try:
        async with APIClient() as client:
            methods = await client.get_available_methods()
            if methods:
                print(f"  ✅ Получены методы: {list(methods.get('available_methods', []))}")
            else:
                print("  ⚠  Не удалось получить методы (возможно, API не запущен)")
    except Exception as e:
        print(f"  ⚠  Ошибка при тесте API клиента: {e}")


def test_handlers():
    """Тест обработчиков."""
    print("\n🧪 Тестирование обработчиков...")
    
    # Проверяем, что обработчики можно импортировать
    assert hasattr(handlers, 'start_command')
    assert hasattr(handlers, 'handle_audio_message')
    assert hasattr(handlers, 'handle_callback_query')
    
    print("  ✅ Обработчики импортируются корректно")


async def main():
    """Запуск всех тестов."""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ TELEGRAM БОТА")
    print("=" * 70)
    
    tests = [
        ("Утилиты", test_utils),
        ("Операции с файлами", test_file_operations),
        ("Конфигурация", test_config),
        ("API клиент", test_api_client),
        ("Обработчики", test_handlers),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            print(f"  ✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 Результаты: {passed} пройдено, {failed} провалено")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠  Тестирование прервано пользователем")
        exit_code = 1
    
    sys.exit(exit_code)