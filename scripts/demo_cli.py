#!/usr/bin/env python3
"""
Консольный интерфейс для демонстрации работы денойзера.
Позволяет обрабатывать аудиофайлы из командной строки.
"""

import argparse
import sys
from pathlib import Path
import time
import numpy as np

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core import denoise_file, Denoiser, AudioIO


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Очистка аудиофайлов от шума',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s input.wav output.wav
  %(prog)s input.wav output.wav --method bandpass
  %(prog)s input.wav output.wav --method noisereduce --verbose
  %(prog)s input.wav output.wav --voice-type female --plot
        """
    )
    
    # Обязательные аргументы
    parser.add_argument('input', help='Путь к входному аудиофайлу')
    parser.add_argument('output', help='Путь для сохранения очищенного файла')
    
    # Опциональные аргументы
    parser.add_argument('--method', '-m', 
                       choices=['bandpass', 'spectral_subtraction', 'wiener', 
                                'noisereduce', 'adaptive'],
                       default='noisereduce',
                       help='Метод очистки (по умолчанию: noisereduce)')
    
    parser.add_argument('--voice-type', '-vt',
                       choices=['male', 'female', 'broadband'],
                       default='broadband',
                       help='Тип голоса для полосовой фильтрации')
    
    parser.add_argument('--sample-rate', '-sr',
                       type=int, default=16000,
                       help='Целевая частота дискретизации (по умолчанию: 16000)')
    
    parser.add_argument('--plot', '-p',
                       action='store_true',
                       help='Показать графики до/после обработки')
    
    parser.add_argument('--compare', '-c',
                       action='store_true',
                       help='Сохранить сравнение (исходный + очищенный в один файл)')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Подробный вывод')
    
    parser.add_argument('--list-methods',
                       action='store_true',
                       help='Показать список доступных методов и выйти')
    
    parser.add_argument('--version',
                       action='store_true',
                       help='Показать версию и выйти')
    
    return parser.parse_args()


def print_banner():
    """Печать красивого баннера."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║           VOICE DENOISER - Очистка аудио от шума         ║
║                    (консольная версия)                   ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def list_methods():
    """Вывод списка доступных методов с описанием."""
    denoiser = Denoiser(verbose=False)
    
    print("\nДоступные методы очистки:")
    print("─" * 60)
    
    for method in denoiser.get_available_methods():
        description = denoiser.get_method_description(method)
        print(f"  • {method:25} - {description}")
    
    print("\nРекомендации:")
    print("  - adaptive     : Автоматический выбор")
    print("  - bandpass     : Для удаления внеполосных шумов")
    print("  - noisereduce  : Для сложных нестационарных шумов")
    print()


def show_version():
    """Показать версию проекта."""
    import importlib.metadata
    
    try:
        version = importlib.metadata.version('voice_denoiser')
    except:
        version = "1.0.0 (development)"
    
    print(f"\nVoice Denoiser v{version}")
    print("Магистерский проект по очистке голосовых сообщений от шума")
    print()


def plot_comparison(input_audio, output_audio, sr, input_path, output_path):
    """Визуализация сравнения исходного и очищенного аудио."""
    try:
        import matplotlib.pyplot as plt
        import librosa.display
    except ImportError:
        print("⚠  Для построения графиков установите matplotlib и librosa")
        print("   pip install matplotlib librosa")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Обрезаем для визуализации (первые 5 секунд)
    max_samples = min(len(input_audio), len(output_audio), 5 * sr)
    time_axis = np.arange(max_samples) / sr
    
    # 1. Временные графики
    axes[0, 0].plot(time_axis, input_audio[:max_samples], 'r', alpha=0.7, label='Исходный')
    axes[0, 0].plot(time_axis, output_audio[:max_samples], 'b', alpha=0.5, label='Очищенный')
    axes[0, 0].set_title('Временная область')
    axes[0, 0].set_xlabel('Время (сек)')
    axes[0, 0].set_ylabel('Амплитуда')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Спектрограммы исходного
    D_input = librosa.stft(input_audio[:max_samples])
    S_db_input = librosa.amplitude_to_db(np.abs(D_input), ref=np.max)
    librosa.display.specshow(S_db_input, sr=sr, x_axis='time', y_axis='log', ax=axes[0, 1])
    axes[0, 1].set_title('Спектрограмма исходного')
    
    # 3. Спектрограммы очищенного
    D_output = librosa.stft(output_audio[:max_samples])
    S_db_output = librosa.amplitude_to_db(np.abs(D_output), ref=np.max)
    librosa.display.specshow(S_db_output, sr=sr, x_axis='time', y_axis='log', ax=axes[1, 0])
    axes[1, 0].set_title('Спектрограмма очищенного')
    
    # 4. Разностная спектрограмма (удаленный шум)
    diff_spec = np.abs(D_input) - np.abs(D_output)
    librosa.display.specshow(
        librosa.amplitude_to_db(np.abs(diff_spec), ref=np.max),
        sr=sr, x_axis='time', y_axis='log', ax=axes[1, 1]
    )
    axes[1, 1].set_title('Разностная спектрограмма (удаленный шум)')
    
    plt.tight_layout()
    
    # Сохраняем график
    plot_path = Path(output_path).with_suffix('.comparison.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"  📊 График сохранен: {plot_path}")
    
    plt.show()


def save_comparison_audio(input_audio, output_audio, sr, output_path):
    """Сохраняет исходное и очищенное аудио в один файл (левый/правый канал)."""
    # Обеспечиваем одинаковую длину
    min_len = min(len(input_audio), len(output_audio))
    
    # Создаем стерео файл: левый канал - исходный, правый - очищенный
    stereo_audio = np.vstack([
        input_audio[:min_len],
        output_audio[:min_len]
    ]).T
    
    # Сохраняем
    comparison_path = Path(output_path).with_stem(
        Path(output_path).stem + "_comparison"
    )
    
    AudioIO.save_audio(stereo_audio, comparison_path, sr)
    
    return comparison_path


def main():
    """Основная функция CLI."""
    args = parse_arguments()
    
    # Специальные флаги
    if args.version:
        show_version()
        return 0
    
    if args.list_methods:
        list_methods()
        return 0
    
    # Проверка входного файла
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Ошибка: Файл '{args.input}' не найден")
        return 1
    
    # Создаем выходную директорию, если нужно
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Печать баннера
    if args.verbose:
        print_banner()
    
    print(f"🔊 Обработка аудиофайла:")
    print(f"   Вход:  {input_path}")
    print(f"   Выход: {output_path}")
    print(f"   Метод: {args.method}")
    
    if args.verbose:
        # Получаем информацию о файле
        try:
            info = AudioIO.get_audio_info(input_path)
            print(f"\n📋 Информация о файле:")
            print(f"   Длительность: {info['duration']:.2f} сек")
            print(f"   Частота: {info['sample_rate']} Гц")
            print(f"   Каналы: {info['channels']}")
            print(f"   Размер: {info['size_bytes'] / 1024:.1f} КБ")
        except:
            pass
    
    # Обработка файла
    print("\n🔄 Обработка...")
    start_time = time.time()
    
    try:
        # Параметры для метода
        kwargs = {}
        if args.method == 'bandpass':
            kwargs['voice_type'] = args.voice_type
        
        # Выполняем очистку
        result = denoise_file(
            input_path=input_path,
            output_path=output_path,
            method=args.method,
            **kwargs
        )
        
        processing_time = time.time() - start_time
        
        # Вывод результатов
        print(f"\n✅ Обработка завершена успешно!")
        print(f"   Метод: {result['method']}")
        print(f"   Время обработки: {processing_time:.2f} сек")
        print(f"   Исходный размер: {result['original_shape']}")
        print(f"   Конечный размер: {result['denoised_shape']}")
        
        # Загружаем оба аудио для сравнения
        if args.plot or args.compare:
            input_audio, sr = AudioIO.load_audio(input_path, sr=args.sample_rate)
            output_audio, _ = AudioIO.load_audio(output_path, sr=args.sample_rate)
        
        # Построение графиков
        if args.plot:
            print("\n📈 Построение графиков сравнения...")
            plot_comparison(input_audio, output_audio, sr, args.input, args.output)
        
        # Сохранение сравнения
        if args.compare:
            print("\n🔊 Создание файла сравнения...")
            comparison_path = save_comparison_audio(input_audio, output_audio, sr, args.output)
            print(f"   Файл сравнения сохранен: {comparison_path}")
            print("   Используйте наушники: левый канал - исходный, правый - очищенный")
        
        # Итоговое сообщение
        print(f"\n🎉 Файл успешно обработан и сохранен: {output_path}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Ошибка при обработке файла: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())