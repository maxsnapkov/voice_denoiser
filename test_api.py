#!/usr/bin/env python3
"""
Тесты для FastAPI сервера.
"""

import sys
from pathlib import Path
import tempfile
import numpy as np

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from app.main import app
from app.core import AudioIO


def test_health_check():
    """Тест проверки здоровья API."""
    client = TestClient(app)
    
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "version" in data
    assert "uptime" in data


def test_get_methods():
    """Тест получения списка методов."""
    client = TestClient(app)
    
    response = client.get("/api/methods")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "available_methods" in data
    assert "descriptions" in data
    assert "default_method" in data
    
    # Проверяем наличие основных методов
    methods = data["available_methods"]
    assert "adaptive" in methods
    assert "bandpass" in methods


def test_denoise_single_file():
    """Тест очистки одного файла."""
    client = TestClient(app)
    
    # Создаем тестовый аудиофайл
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        # Генерируем тестовый сигнал
        sr = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        test_audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(len(t))
        
        # Сохраняем
        AudioIO.save_audio(test_audio, tmp.name, sr)
        
        # Читаем файл для отправки
        tmp.seek(0)
        files = {"audio_file": ("test.wav", tmp.read(), "audio/wav")}
    
    # Отправляем запрос
    response = client.post(
        "/api/denoise",
        files=files,
        data={"method": "bandpass"}
    )
    
    # Проверяем ответ
    assert response.status_code == 200
    data = response.json()
    
    assert "request_id" in data
    assert "filename" in data
    assert "original_info" in data
    assert "method" in data
    assert "processing_time" in data
    assert "download_url" in data
    
    # Проверяем, что файл можно скачать
    filename = data["filename"]
    download_response = client.get(f"/api/download/{filename}")
    assert download_response.status_code == 200


def test_denoise_with_parameters():
    """Тест очистки с различными параметрами."""
    client = TestClient(app)
    
    # Создаем тестовый аудиофайл
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sr = 16000
        duration = 0.5
        t = np.linspace(0, duration, int(sr * duration))
        test_audio = 0.3 * np.sin(2 * np.pi * 880 * t)
        
        AudioIO.save_audio(test_audio, tmp.name, sr)
        tmp.seek(0)
        files = {"audio_file": ("test_params.wav", tmp.read(), "audio/wav")}
    
    # Тестируем разные методы
    for method in ["bandpass", "spectral_subtraction", "adaptive"]:
        response = client.post(
            "/api/denoise",
            files=files,
            data={
                "method": method,
                "sample_rate": 16000,
                "voice_type": "broadband"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == method


def test_invalid_file_format():
    """Тест с неподдерживаемым форматом файла."""
    client = TestClient(app)
    
    # Создаем файл с неподдерживаемым расширением
    files = {"audio_file": ("test.txt", b"not an audio file", "text/plain")}
    
    response = client.post("/api/denoise", files=files)
    
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_file_too_large():
    """Тест с файлом превышающим максимальный размер."""
    client = TestClient(app)
    
    # Создаем большой файл (больше 50MB)
    large_data = b"0" * (51 * 1024 * 1024)  # 51MB
    files = {"audio_file": ("large.wav", large_data, "audio/wav")}
    
    response = client.post("/api/denoise", files=files)
    
    assert response.status_code == 413
    data = response.json()
    assert "File too large" in data["error"]


def test_batch_denoise():
    """Тест пакетной обработки файлов."""
    client = TestClient(app)
    
    # Создаем несколько тестовых файлов
    files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sr = 16000
            duration = 0.3
            t = np.linspace(0, duration, int(sr * duration))
            test_audio = 0.4 * np.sin(2 * np.pi * 440 * (i+1) * t)
            
            AudioIO.save_audio(test_audio, tmp.name, sr)
            tmp.seek(0)
            
            files.append(("audio_files", (f"test_{i}.wav", tmp.read(), "audio/wav")))
    
    # Отправляем запрос
    response = client.post(
        "/api/denoise/batch",
        files=files,
        data={"method": "adaptive"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "request_id" in data
    assert "total_files" in data
    assert "processed_files" in data
    assert "failed_files" in data
    assert "processing_time" in data
    assert "results" in data
    assert "download_urls" in data
    
    assert data["total_files"] == 3
    assert data["processed_files"] + data["failed_files"] == 3


def test_get_stats():
    """Тест получения статистики."""
    client = TestClient(app)
    
    response = client.get("/api/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "uptime_seconds" in data
    assert "uploaded_files" in data
    assert "processed_files" in data
    assert "max_file_size_mb" in data
    assert "allowed_extensions" in data


def test_root_endpoint():
    """Тест корневого эндпоинта."""
    client = TestClient(app)
    
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "app" in data
    assert "version" in data
    assert "docs" in data
    assert "api_prefix" in data
    assert "endpoints" in data


def main():
    """Запуск всех тестов."""
    print("🧪 Запуск тестов API...")
    
    tests = [
        ("Проверка здоровья", test_health_check),
        ("Получение методов", test_get_methods),
        ("Очистка одного файла", test_denoise_single_file),
        ("Очистка с параметрами", test_denoise_with_parameters),
        ("Неподдерживаемый формат", test_invalid_file_format),
        ("Слишком большой файл", test_file_too_large),
        ("Пакетная обработка", test_batch_denoise),
        ("Статистика", test_get_stats),
        ("Корневой эндпоинт", test_root_endpoint),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"  ✅ {test_name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")
            failed += 1
    
    print(f"\n📊 Результаты: {passed} пройдено, {failed} провалено")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())