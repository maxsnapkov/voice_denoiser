#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы core модулей.
"""

import sys
from pathlib import Path

# Добавляем путь к core
sys.path.insert(0, str(Path(__file__).parent))

from app.core import AudioIO, Denoiser, create_denoiser
import numpy as np
import tempfile

def test_audio_io():
    """Тест модуля AudioIO."""
    print("Тестирование AudioIO...")
    
    # Создаем тестовый сигнал
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    test_audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # Ля первой октавы
    
    # Сохраняем временный файл
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_path = tmp.name
    
    # Тест сохранения
    AudioIO.save_audio(test_audio, tmp_path, sr=sr)
    print(f"  ✓ Файл сохранен: {tmp_path}")
    
    # Тест загрузки
    loaded_audio, loaded_sr = AudioIO.load_audio(tmp_path)
    print(f"  ✓ Файл загружен: форма={loaded_audio.shape}, sr={loaded_sr}")
    
    # Тест информации
    info = AudioIO.get_audio_info(tmp_path)
    print(f"  ✓ Информация получена: длительность={info['duration']:.2f} сек")
    
    # Удаляем временный файл
    Path(tmp_path).unlink()
    print("  ✓ Временный файл удален")
    
    return True

def test_denoiser():
    """Тест модуля Denoiser."""
    print("\nТестирование Denoiser...")
    
    # Создаем тестовый сигнал с шумом
    sr = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Чистый сигнал + шум
    clean = 0.3 * np.sin(2 * np.pi * 440 * t)
    noise = 0.1 * np.random.randn(len(t))
    noisy = clean + noise
    
    # Создаем денойзер
    denoiser = Denoiser(verbose=False)
    
    # Тестируем все методы
    for method in denoiser.get_available_methods():
        print(f"  Тестируем метод: {method}")
        
        try:
            result = denoiser.denoise(noisy, sr=sr, method=method)
            
            # Проверяем результаты
            assert 'audio' in result
            assert 'method' in result
            assert result['method'] == method
            
            # Проверяем, что сигнал изменился (не идентичен исходному)
            assert not np.array_equal(noisy, result['audio'])
            
            print(f"    ✓ Успешно")
            
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
            return False
    
    return True

def test_integration():
    """Интеграционный тест."""
    print("\nИнтеграционный тест...")
    
    # Создаем тестовый файл
    sr = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Сигнал с шумом
    clean = 0.5 * np.sin(2 * np.pi * 880 * t)  # Ля второй октавы
    noise = 0.2 * np.random.randn(len(t))
    test_audio = clean + noise
    
    # Временные файлы
    with tempfile.NamedTemporaryFile(suffix='_input.wav', delete=False) as tmp_in:
        input_path = tmp_in.name
    
    with tempfile.NamedTemporaryFile(suffix='_output.wav', delete=False) as tmp_out:
        output_path = tmp_out.name
    
    try:
        # Сохраняем входной файл
        AudioIO.save_audio(test_audio, input_path, sr=sr)
        
        # Обрабатываем
        from app.core import denoise_file
        result = denoise_file(input_path, output_path, method="bandpass")
        
        # Проверяем
        assert Path(output_path).exists()
        assert result['processing_time'] > 0
        
        print(f"  ✓ Файл обработан: {result['processing_time']:.2f} сек")
        print(f"  ✓ Использован метод: {result['method']}")
        
        return True
        
    finally:
        # Удаляем временные файлы
        for path in [input_path, output_path]:
            if Path(path).exists():
                Path(path).unlink()
        print("  ✓ Временные файлы удалены")

def main():
    """Основная функция тестирования."""
    print("=" * 50)
    print("Тестирование core модулей")
    print("=" * 50)
    
    tests = [
        ("AudioIO", test_audio_io),
        ("Denoiser", test_denoiser),
        ("Интеграция", test_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ✗ Неожиданная ошибка: {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    print("\n" + "=" * 50)
    print("Результаты тестирования:")
    print("=" * 50)
    
    all_passed = True
    for test_name, success in results:
        status = "✓ ПРОЙДЕН" if success else "✗ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
    print("=" * 50)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())