#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов проекта.
"""

import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_core_tests():
    """Запускает тесты core модулей."""
    print("🔬 Тестирование core модулей...")
    
    try:
        from test_core import main as test_core_main
        return test_core_main() == 0
    except ImportError:
        print("  ⚠  Файл тестов core не найден")
        return False
    except Exception as e:
        print(f"  ❌ Ошибка при запуске тестов core: {e}")
        return False


def run_script_tests():
    """Запускает тесты скриптов."""
    print("\n📜 Тестирование скриптов...")
    
    tests = [
        ("demo_cli.py --help", "Проверка справки CLI"),
        ("download_model.py --list", "Проверка списка моделей"),
        ("train.py --dry-run", "Проверка тренера (dry-run)"),
    ]
    
    all_passed = True
    
    for script_args, description in tests:
        print(f"  {description}...")
        
        try:
            # Имитируем запуск через командную строку
            import subprocess
            result = subprocess.run(
                [sys.executable, f"scripts/{script_args.split()[0]}"] + script_args.split()[1:],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            if result.returncode == 0:
                print("    ✓ Успешно")
            else:
                print(f"    ❌ Ошибка (код: {result.returncode})")
                if result.stderr:
                    print(f"       {result.stderr}...")
                all_passed = False
                
        except Exception as e:
            print(f"    ❌ Ошибка выполнения: {e}")
            all_passed = False
    
    return all_passed


def run_integration_test():
    """Запускает интеграционный тест."""
    print("\n🔗 Интеграционный тест...")
    
    try:
        import tempfile
        import numpy as np
        from app.core import AudioIO, Denoiser
        
        # Создаем тестовый файл
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            input_path = tmp.name
        
        # Генерируем тестовый сигнал
        sr = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration))
        test_audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(len(t))
        
        # Сохраняем
        AudioIO.save_audio(test_audio, input_path, sr)
        
        # Обрабатываем
        denoiser = Denoiser(verbose=False)
        result = denoiser.denoise(input_path, method='bandpass')
        
        # Проверяем
        assert 'audio' in result
        assert result['sample_rate'] == sr
        assert result['method'] == 'bandpass'
        
        print("    ✓ Интеграционный тест пройден")
        
        # Удаляем временный файл
        import os
        os.unlink(input_path)
        
        return True
        
    except Exception as e:
        print(f"    ❌ Интеграционный тест провален: {e}")
        return False


def main():
    """Основная функция."""
    print("=" * 70)
    print("ЗАПУСК ТЕСТОВ VOICE DENOISER")
    print("=" * 70)
    
    tests = [
        ("Core модули", run_core_tests),
        ("Скрипты", run_script_tests),
        ("Интеграция", run_integration_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ Неожиданная ошибка: {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 70)
    
    all_passed = True
    for test_name, success in results:
        status = "✓ ПРОЙДЕН" if success else "✗ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
        return 1


if __name__ == "__main__":
    sys.exit(main())