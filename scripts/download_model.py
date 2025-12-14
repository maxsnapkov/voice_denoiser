#!/usr/bin/env python3
"""
Скрипт для загрузки предобученных моделей и дополнительных данных.
В текущей реализации используем алгоритмические методы,
но оставляем возможность для будущих ML-моделей.
"""

import argparse
import sys
from pathlib import Path
import urllib.request
import zipfile
import hashlib
import json
import shutil

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core import __version__


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Загрузка предобученных моделей для денойзера'
    )
    
    parser.add_argument('--list', '-l',
                       action='store_true',
                       help='Показать список доступных моделей')
    
    parser.add_argument('--download', '-d',
                       type=str,
                       choices=['all', 'example_data', 'noise_profiles', 'pretrained_models'],
                       help='Загрузить указанный набор данных')
    
    parser.add_argument('--output-dir', '-o',
                       type=str,
                       default='./data/models',
                       help='Директория для сохранения (по умолчанию: ./data/models)')
    
    parser.add_argument('--force', '-f',
                       action='store_true',
                       help='Перезаписать существующие файлы')
    
    return parser.parse_args()


# Конфигурация моделей и данных для загрузки
MODEL_CONFIG = {
    "example_data": {
        "url": "https://github.com/voice-audio-processing/example-data/archive/refs/heads/main.zip",
        "description": "Примеры аудиофайлов для тестирования",
        "files": [
            "clean_speech.wav",
            "noisy_speech.wav",
            "background_noise.wav"
        ],
        "checksum": "a1b2c3d4e5f67890"  # Пример, в реальности нужно актуальное значение
    },
    "noise_profiles": {
        "url": "https://zenodo.org/record/1234567/files/noise_profiles.zip",
        "description": "Предобученные профили шумов",
        "files": [
            "white_noise.npy",
            "pink_noise.npy",
            "street_noise.npy",
            "office_noise.npy"
        ],
        "checksum": "f0e1d2c3b4a59687"
    },
    "pretrained_models": {
        "url": "https://storage.yandexcloud.net/voice-denoising/models/pretrained.zip",
        "description": "Предобученные нейросетевые модели (для будущих версий)",
        "files": [
            "unet_denoiser.pth",
            "conv_tasnet.pth",
            "demucs.pth"
        ],
        "checksum": "0987654321abcdef"
    }
}


def print_banner():
    """Печать баннера."""
    banner = f"""
╔══════════════════════════════════════════════════════════╗
║         ЗАГРУЗЧИК МОДЕЛЕЙ - Voice Denoiser v{__version__}        ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def list_available_models():
    """Показать список доступных моделей."""
    print("\n📦 Доступные модели и данные для загрузки:")
    print("─" * 60)
    
    for model_id, config in MODEL_CONFIG.items():
        print(f"\n🔹 {model_id.upper().replace('_', ' ')}:")
        print(f"   Описание: {config['description']}")
        print(f"   Файлы: {', '.join(config['files'])}")
        print(f"   Размер: ~10-50 МБ")
    
    print("\n💡 Использование:")
    print("   python scripts/download_model.py --download example_data")
    print("   python scripts/download_model.py --download all")
    print()


def download_file(url: str, output_path: Path, force: bool = False) -> bool:
    """
    Загружает файл по URL.
    
    Args:
        url: URL для загрузки
        output_path: Путь для сохранения
        force: Перезаписать существующий файл
        
    Returns:
        True если успешно
    """
    if output_path.exists() and not force:
        print(f"  ✓ Файл уже существует: {output_path}")
        return True
    
    try:
        # Создаем директорию, если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"  📥 Загрузка {url}...")
        
        # Загрузка с прогресс-баром
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size) if total_size > 0 else 0
            print(f"  ⏳ Прогресс: {percent:.1f}% ({downloaded/1024/1024:.1f} МБ)", end='\r')
        
        urllib.request.urlretrieve(url, output_path, report_progress)
        print()  # Новая строка после прогресс-бара
        
        return True
        
    except Exception as e:
        print(f"\n  ❌ Ошибка загрузки: {e}")
        return False


def extract_zip(zip_path: Path, extract_dir: Path, force: bool = False) -> bool:
    """
    Распаковывает ZIP архив.
    
    Args:
        zip_path: Путь к ZIP архиву
        extract_dir: Директория для распаковки
        force: Перезаписать существующие файлы
        
    Returns:
        True если успешно
    """
    if not zip_path.exists():
        print(f"  ❌ ZIP файл не найден: {zip_path}")
        return False
    
    try:
        # Создаем директорию, если нужно
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  📦 Распаковка {zip_path.name}...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Получаем список файлов
            file_list = zip_ref.namelist()
            
            # Распаковываем с прогрессом
            total_files = len(file_list)
            for i, file_name in enumerate(file_list, 1):
                # Пропускаем директории
                if file_name.endswith('/'):
                    continue
                
                # Извлекаем файл
                try:
                    zip_ref.extract(file_name, extract_dir)
                    print(f"    Извлечено: {file_name} ({i}/{total_files})", end='\r')
                except:
                    pass
            
            print()  # Новая строка
        
        return True
        
    except Exception as e:
        print(f"\n  ❌ Ошибка распаковки: {e}")
        return False


def verify_checksum(file_path: Path, expected_checksum: str) -> bool:
    """
    Проверяет контрольную сумму файла.
    
    Args:
        file_path: Путь к файлу
        expected_checksum: Ожидаемая контрольная сумма
        
    Returns:
        True если совпадает
    """
    if not file_path.exists():
        return False
    
    try:
        # Вычисляем SHA-256
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Читаем файл блоками
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_checksum = sha256_hash.hexdigest()[:16]
        return actual_checksum == expected_checksum
        
    except:
        return False


def download_model(model_id: str, output_dir: Path, force: bool = False) -> bool:
    """
    Загружает указанную модель.
    
    Args:
        model_id: Идентификатор модели
        output_dir: Директория для сохранения
        force: Перезаписать существующие файлы
        
    Returns:
        True если успешно
    """
    if model_id not in MODEL_CONFIG:
        print(f"❌ Неизвестная модель: {model_id}")
        return False
    
    config = MODEL_CONFIG[model_id]
    
    print(f"\n🔽 Загрузка: {model_id}")
    print(f"   {config['description']}")
    
    # Создаем временную директорию
    temp_dir = output_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Путь для ZIP файла
    zip_path = temp_dir / f"{model_id}.zip"
    
    try:
        # Загружаем ZIP архив
        if not download_file(config['url'], zip_path, force):
            return False
        
        # Проверяем контрольную сумму
        if config.get('checksum'):
            print("  🔍 Проверка контрольной суммы...")
            if not verify_checksum(zip_path, config['checksum']):
                print("  ❌ Контрольная сумма не совпадает!")
                return False
            print("  ✓ Контрольная сумма верна")
        
        # Распаковываем
        if not extract_zip(zip_path, output_dir / model_id, force):
            return False
        
        # Удаляем временные файлы
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Проверяем извлеченные файлы
        model_dir = output_dir / model_id
        extracted_files = list(model_dir.rglob("*"))
        
        print(f"\n  📁 Файлы сохранены в: {model_dir}")
        for file_path in extracted_files[:10]:  # Показываем первые 10 файлов
            if file_path.is_file():
                print(f"    • {file_path.relative_to(model_dir)}")
        
        if len(extracted_files) > 10:
            print(f"    ... и еще {len(extracted_files) - 10} файлов")
        
        print(f"\n✅ {model_id} успешно загружена!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при загрузке {model_id}: {e}")
        # Очищаем временные файлы
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False


def create_example_structure(output_dir: Path):
    """
    Создает примерную структуру данных, если загрузка недоступна.
    
    Args:
        output_dir: Директория для создания примеров
    """
    print("\n📝 Создание примерной структуры данных...")
    
    example_dir = output_dir / "examples"
    example_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем простые текстовые файлы с инструкциями
    readme_content = """# Примеры данных для Voice Denoiser

Эта директория содержит примеры аудиофайлов для тестирования системы очистки.

## Как добавить свои файлы:
1. Поместите аудиофайлы в соответствующие поддиректории
2. Поддерживаемые форматы: WAV, MP3, FLAC, OGG
3. Рекомендуемая частота дискретизации: 16000 Гц

## Структура:
- clean/     - Чистые аудиозаписи
- noisy/     - Зашумленные записи
- noise/     - Образцы шумов
- results/   - Результаты обработки
"""
    
    with open(example_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Создаем поддиректории
    for subdir in ["clean", "noisy", "noise", "results"]:
        (example_dir / subdir).mkdir(exist_ok=True)
    
    print(f"  ✅ Создана структура в: {example_dir}")
    print(f"  📋 Откройте {example_dir}/README.md для инструкций")


def main():
    """Основная функция."""
    args = parse_arguments()
    
    print_banner()
    
    # Показать список моделей
    if args.list:
        list_available_models()
        return 0
    
    # Создаем выходную директорию
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Загрузка указанной модели
    if args.download:
        if args.download == "all":
            success = True
            for model_id in MODEL_CONFIG.keys():
                if not download_model(model_id, output_dir, args.force):
                    success = False
                    print(f"\n⚠  Пропускаем {model_id} и продолжаем...")
            
            if not success:
                print("\n⚠  Некоторые модели не удалось загрузить.")
                print("   Создаем базовую структуру данных...")
                create_example_structure(output_dir)
        
        else:
            if not download_model(args.download, output_dir, args.force):
                print(f"\n⚠  Не удалось загрузить {args.download}.")
                print("   Создаем базовую структуру...")
                create_example_structure(output_dir)
    
    else:
        # Если не указаны аргументы, показываем справку
        print("ℹ️  Используйте --list для просмотра доступных моделей")
        print("   или --download для загрузки конкретной модели")
        print("\nПример: python scripts/download_model.py --download example_data")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())