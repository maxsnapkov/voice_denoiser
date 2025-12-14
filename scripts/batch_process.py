#!/usr/bin/env python3
"""
Скрипт для пакетной обработки аудиофайлов.
Позволяет обработать все файлы в директории.
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time
import json
from datetime import datetime

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core import denoise_file, AudioIO


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Пакетная обработка аудиофайлов'
    )
    
    parser.add_argument('input_dir',
                       help='Директория с входными аудиофайлами')
    
    parser.add_argument('output_dir',
                       help='Директория для сохранения результатов')
    
    parser.add_argument('--method', '-m',
                       default='noisereduce',
                       choices=['bandpass', 'spectral_subtraction', 'wiener', 
                                'noisereduce', 'adaptive'],
                       help='Метод очистки (по умолчанию: noisereduce)')
    
    parser.add_argument('--extensions', '-ext',
                       nargs='+',
                       default=['.wav', '.mp3', '.flac', '.ogg'],
                       help='Расширения файлов для обработки')
    
    parser.add_argument('--recursive', '-r',
                       action='store_true',
                       help='Рекурсивный поиск файлов')
    
    parser.add_argument('--workers', '-w',
                       type=int,
                       default=2,
                       help='Количество потоков для обработки (по умолчанию: 2)')
    
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Показать список файлов без обработки')
    
    parser.add_argument('--report', '-rep',
                       action='store_true',
                       help='Создать отчет о обработке')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Подробный вывод')
    
    return parser.parse_args()


def find_audio_files(input_dir: Path, extensions: list, recursive: bool) -> list:
    """
    Находит все аудиофайлы в директории.
    
    Args:
        input_dir: Директория для поиска
        extensions: Список расширений
        recursive: Рекурсивный поиск
        
    Returns:
        Список путей к файлам
    """
    audio_files = []
    
    if recursive:
        # Рекурсивный поиск
        for ext in extensions:
            pattern = f"**/*{ext}"
            files = list(input_dir.glob(pattern))
            audio_files.extend(files)
    else:
        # Поиск только в текущей директории
        for ext in extensions:
            pattern = f"*{ext}"
            files = list(input_dir.glob(pattern))
            audio_files.extend(files)
    
    # Убираем дубликаты и сортируем
    audio_files = sorted(set(audio_files))
    
    return audio_files


def process_single_file(input_file: Path, output_dir: Path, method: str, verbose: bool) -> dict:
    """
    Обрабатывает один аудиофайл.
    
    Args:
        input_file: Путь к входному файлу
        output_dir: Директория для сохранения
        method: Метод очистки
        verbose: Подробный вывод
        
    Returns:
        Результаты обработки
    """
    try:
        # Создаем путь для выходного файла
        output_file = output_dir / f"{input_file.stem}_denoised{input_file.suffix}"
        
        # Обрабатываем
        start_time = time.time()
        result = denoise_file(input_file, output_file, method=method)
        processing_time = time.time() - start_time
        
        # Собираем статистику
        file_stats = {
            'input_file': str(input_file),
            'output_file': str(output_file),
            'method': method,
            'processing_time': processing_time,
            'original_shape': result['original_shape'],
            'denoised_shape': result['denoised_shape'],
            'success': True,
            'error': None
        }
        
        if verbose:
            print(f"  ✅ Обработан: {input_file.name} "
                  f"({processing_time:.2f} сек)")
        
        return file_stats
        
    except Exception as e:
        if verbose:
            print(f"  ❌ Ошибка: {input_file.name} - {e}")
        
        return {
            'input_file': str(input_file),
            'output_file': None,
            'method': method,
            'processing_time': 0,
            'success': False,
            'error': str(e)
        }


def create_report(results: list, output_dir: Path, method: str):
    """
    Создает отчет о пакетной обработке.
    
    Args:
        results: Результаты обработки
        output_dir: Директория для отчета
        method: Использованный метод
    """
    # Статистика
    total_files = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_files - successful
    
    total_time = sum(r['processing_time'] for r in results if r['success'])
    avg_time = total_time / successful if successful > 0 else 0
    
    # Создаем отчет
    report = {
        'batch_processing_report': {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'input_dir': str(results[0]['input_file'].parent) if results else '',
            'output_dir': str(output_dir),
            'statistics': {
                'total_files': total_files,
                'successful': successful,
                'failed': failed,
                'success_rate': f"{(successful/total_files*100):.1f}%" if total_files > 0 else "0%",
                'total_processing_time': total_time,
                'average_processing_time': avg_time,
                'processing_speed': f"{total_time/max(total_files, 1):.3f} сек/файл"
            },
            'files': results
        }
    }
    
    # Сохраняем JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"batch_report_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Создаем текстовую сводку
    summary_file = output_dir / f"summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("ОТЧЕТ О ПАКЕТНОЙ ОБРАБОТКЕ\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Дата обработки:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Метод очистки:   {method}\n")
        f.write(f"Входная директория:  {report['batch_processing_report']['input_dir']}\n")
        f.write(f"Выходная директория: {output_dir}\n\n")
        
        f.write("СТАТИСТИКА:\n")
        f.write("-" * 70 + "\n")
        f.write(f"Всего файлов:     {total_files}\n")
        f.write(f"Успешно:          {successful}\n")
        f.write(f"Неудачно:         {failed}\n")
        f.write(f"Успешность:       {report['batch_processing_report']['statistics']['success_rate']}\n")
        f.write(f"Общее время:      {total_time:.2f} сек\n")
        f.write(f"Среднее время:    {avg_time:.2f} сек/файл\n\n")
        
        if failed > 0:
            f.write("НЕУДАЧНЫЕ ФАЙЛЫ:\n")
            f.write("-" * 70 + "\n")
            for result in results:
                if not result['success']:
                    f.write(f"• {Path(result['input_file']).name}: {result['error']}\n")
    
    print(f"\n📊 Отчет сохранен: {report_file}")
    print(f"📋 Сводка сохранена: {summary_file}")
    
    return report


def main():
    """Основная функция."""
    args = parse_arguments()
    
    print("=" * 70)
    print("ПАКЕТНАЯ ОБРАБОТКА АУДИОФАЙЛОВ")
    print("=" * 70)
    
    # Проверяем директории
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"❌ Входная директория не найдена: {input_dir}")
        return 1
    
    # Создаем выходную директорию
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Находим файлы
    print(f"\n🔍 Поиск аудиофайлов в {input_dir}...")
    audio_files = find_audio_files(input_dir, args.extensions, args.recursive)
    
    if not audio_files:
        print("❌ Не найдено аудиофайлов для обработки")
        return 1
    
    print(f"   Найдено файлов: {len(audio_files)}")
    
    # Показываем список файлов для dry-run
    if args.dry_run:
        print("\n📋 Список файлов для обработки:")
        for file in audio_files:
            info = AudioIO.get_audio_info(file)
            print(f"  • {file.name} ({info['duration']:.1f} сек, {info['sample_rate']} Гц)")
        
        print(f"\n⚠  Dry-run режим. Обработка не выполнена.")
        return 0
    
    # Обработка файлов
    print(f"\n🔄 Начинаю обработку {len(audio_files)} файлов...")
    print(f"   Метод: {args.method}")
    print(f"   Потоков: {args.workers}")
    
    start_time = time.time()
    results = []
    
    # Многопоточная обработка
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Создаем задачи
        futures = []
        for audio_file in audio_files:
            future = executor.submit(
                process_single_file,
                audio_file,
                output_dir,
                args.method,
                args.verbose
            )
            futures.append(future)
        
        # Собираем результаты
        for i, future in enumerate(futures, 1):
            try:
                result = future.result()
                results.append(result)
                
                # Прогресс
                if not args.verbose:
                    progress = i / len(futures) * 100
                    print(f"  Прогресс: {progress:5.1f}% ({i}/{len(futures)})", end='\r')
            except Exception as e:
                print(f"  ❌ Ошибка в потоке: {e}")
                results.append({
                    'input_file': str(audio_files[i-1]),
                    'success': False,
                    'error': str(e)
                })
    
    if not args.verbose:
        print()  # Новая строка после прогресс-бара
    
    total_time = time.time() - start_time
    
    # Статистика
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\n✅ Обработка завершена!")
    print(f"   Успешно: {successful} файлов")
    print(f"   Неудачно: {failed} файлов")
    print(f"   Общее время: {total_time:.2f} сек")
    print(f"   Среднее время: {total_time/len(results):.2f} сек/файл")
    
    # Создаем отчет
    if args.report:
        print(f"\n📊 Создание отчета...")
        create_report(results, output_dir, args.method)
    
    # Показываем неудачные файлы
    if failed > 0:
        print(f"\n⚠  Неудачные файлы:")
        for result in results:
            if not result['success']:
                print(f"  • {Path(result['input_file']).name}: {result['error']}")
    
    print(f"\n🎉 Пакетная обработка завершена!")
    print(f"   Результаты сохранены в: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())