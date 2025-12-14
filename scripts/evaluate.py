#!/usr/bin/env python3
"""
Скрипт для оценки качества работы денойзера.
Сравнивает исходные и очищенные файлы, вычисляет метрики.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
import json
from datetime import datetime

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core import AudioIO, Denoiser


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Оценка качества работы денойзера'
    )
    
    parser.add_argument('--clean', '-c',
                       required=True,
                       help='Путь к чистому аудиофайлу (референс)')
    
    parser.add_argument('--noisy', '-n',
                       required=True,
                       help='Путь к зашумленному аудиофайлу')
    
    parser.add_argument('--output', '-o',
                       default='./evaluation_results',
                       help='Директория для сохранения результатов')
    
    parser.add_argument('--methods',
                       nargs='+',
                       default=['bandpass', 'spectral_subtraction', 'adaptive'],
                       help='Методы для оценки')
    
    parser.add_argument('--plot',
                       action='store_true',
                       help='Создать графики сравнения')
    
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Подробный вывод')
    
    return parser.parse_args()


def calculate_metrics(clean: np.ndarray, denoised: np.ndarray, sr: int) -> dict:
    """
    Вычисляет метрики качества.
    
    Args:
        clean: Чистый сигнал (референс)
        denoised: Очищенный сигнал
        sr: Частота дискретизации
        
    Returns:
        Словарь с метриками
    """
    # Обрезаем до одинаковой длины
    min_len = min(len(clean), len(denoised))
    clean = clean[:min_len]
    denoised = denoised[:min_len]
    
    # 1. MSE (Mean Squared Error)
    mse = np.mean((clean - denoised) ** 2)
    
    # 2. SNR (Signal-to-Noise Ratio)
    signal_power = np.mean(clean ** 2)
    noise_power = np.mean((clean - denoised) ** 2)
    snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
    
    # 3. PSNR (Peak Signal-to-Noise Ratio)
    max_signal = np.max(np.abs(clean))
    psnr = 10 * np.log10((max_signal ** 2) / (mse + 1e-10))
    
    # 4. SI-SNR (Scale-Invariant SNR)
    # Выравнивание по масштабу
    alpha = np.dot(clean, denoised) / (np.dot(clean, clean) + 1e-10)
    target_scaled = alpha * clean
    
    # Сигнал и шум
    signal_est = target_scaled
    noise_est = denoised - target_scaled
    
    si_snr = 10 * np.log10(
        np.dot(signal_est, signal_est) / (np.dot(noise_est, noise_est) + 1e-10) + 1e-10
    )
    
    # 5. SNR улучшение (по сравнению с зашумленным)
    noisy_signal = clean + (denoised - clean)  # Имитация исходного зашумленного
    original_noise_power = np.mean((clean - noisy_signal) ** 2)
    snr_improvement = snr - 10 * np.log10(signal_power / (original_noise_power + 1e-10))
    
    return {
        'MSE': float(mse),
        'SNR_dB': float(snr),
        'PSNR_dB': float(psnr),
        'SI_SNR_dB': float(si_snr),
        'SNR_improvement_dB': float(snr_improvement),
        'length_samples': min_len,
        'duration_seconds': min_len / sr
    }


def evaluate_method(clean_audio: np.ndarray, noisy_audio: np.ndarray, 
                   sr: int, method: str, denoiser: Denoiser) -> dict:
    """
    Оценивает качество работы конкретного метода.
    
    Args:
        clean_audio: Чистый аудиосигнал
        noisy_audio: Зашумленный аудиосигнал
        sr: Частота дискретизации
        method: Метод очистки
        denoiser: Экземпляр Denoiser
        
    Returns:
        Результаты оценки
    """
    print(f"  📊 Оценка метода: {method}")
    
    # Очищаем аудио
    result = denoiser.denoise(noisy_audio, sr=sr, method=method)
    denoised_audio = result['audio']
    
    # Вычисляем метрики
    metrics = calculate_metrics(clean_audio, denoised_audio, sr)
    
    # Добавляем информацию о методе
    metrics.update({
        'method': method,
        'processing_time': result['processing_time'],
        'description': denoiser.get_method_description(method)
    })
    
    return metrics, denoised_audio


def save_results(results: dict, output_dir: Path, plot: bool = False):
    """
    Сохраняет результаты оценки.
    
    Args:
        results: Результаты оценки
        output_dir: Директория для сохранения
        plot: Создать графики
    """
    # Создаем директорию
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Сохраняем JSON с результатами
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"evaluation_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"  💾 Результаты сохранены: {results_file}")
    
    # Создаем сводную таблицу
    summary_file = output_dir / f"summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("ОЦЕНКА КАЧЕСТВА ДЕНОЙЗИНГА\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Тестовый файл: {results['test_file']}\n")
        f.write(f"Чистый файл:   {results['clean_file']}\n")
        f.write(f"Дата оценки:   {results['evaluation_date']}\n")
        f.write(f"Частота дискр.: {results['sample_rate']} Гц\n")
        f.write(f"Длительность:  {results['duration']:.2f} сек\n\n")
        
        f.write("МЕТОДЫ ОЧИСТКИ:\n")
        f.write("-" * 70 + "\n")
        
        # Сортируем по SNR улучшению
        sorted_methods = sorted(
            results['methods'].items(),
            key=lambda x: x[1]['SNR_improvement_dB'],
            reverse=True
        )
        
        for method_name, metrics in sorted_methods:
            f.write(f"\n🔹 {method_name.upper()}:\n")
            f.write(f"   Описание:    {metrics['description']}\n")
            f.write(f"   SNR улучш.:  {metrics['SNR_improvement_dB']:6.2f} дБ\n")
            f.write(f"   SI-SNR:      {metrics['SI_SNR_dB']:6.2f} дБ\n")
            f.write(f"   PSNR:        {metrics['PSNR_dB']:6.2f} дБ\n")
            f.write(f"   Время обработки: {metrics['processing_time']:6.3f} сек\n")
    
    print(f"  📋 Сводка сохранена: {summary_file}")
    
    # Создаем графики
    if plot and 'plot_data' in results:
        try:
            create_comparison_plots(results['plot_data'], output_dir, timestamp)
        except:
            print("  ⚠  Не удалось создать графики")


def create_comparison_plots(plot_data: dict, output_dir: Path, timestamp: str):
    """
    Создает графики сравнения методов.
    
    Args:
        plot_data: Данные для графиков
        output_dir: Директория для сохранения
        timestamp: Метка времени
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    # 1. График сравнения метрик
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    methods = list(plot_data['metrics'].keys())
    metric_names = ['SNR_improvement_dB', 'SI_SNR_dB', 'PSNR_dB', 'processing_time']
    titles = ['SNR улучшение (дБ)', 'SI-SNR (дБ)', 'PSNR (дБ)', 'Время обработки (сек)']
    
    for idx, (ax, metric, title) in enumerate(zip(axes.flatten(), metric_names, titles)):
        values = [plot_data['metrics'][m][metric] for m in methods]
        
        bars = ax.bar(methods, values)
        ax.set_title(title)
        ax.set_ylabel(metric if 'дБ' not in title else 'дБ')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height + 0.05,
                   f'{value:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plot_file = output_dir / f"metrics_comparison_{timestamp}.png"
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  📈 График метрик сохранен: {plot_file}")


def main():
    """Основная функция."""
    args = parse_arguments()
    
    print("=" * 70)
    print("ОЦЕНКА КАЧЕСТВА ДЕНОЙЗИНГА")
    print("=" * 70)
    
    # Проверяем файлы
    clean_path = Path(args.clean)
    noisy_path = Path(args.noisy)
    
    if not clean_path.exists():
        print(f"❌ Чистый файл не найден: {clean_path}")
        return 1
    
    if not noisy_path.exists():
        print(f"❌ Зашумленный файл не найден: {noisy_path}")
        return 1
    
    # Загружаем аудио
    print(f"\n📁 Загрузка файлов...")
    clean_audio, sr_clean = AudioIO.load_audio(clean_path)
    noisy_audio, sr_noisy = AudioIO.load_audio(noisy_path)
    
    # Приводим к одинаковой частоте дискретизации
    if sr_clean != sr_noisy:
        print(f"⚠  Частоты дискретизации различаются: {sr_clean} Гц vs {sr_noisy} Гц")
        sr = min(sr_clean, sr_noisy)
        if sr_clean != sr:
            clean_audio = AudioIO.resample_audio(clean_audio, sr_clean, sr)
        if sr_noisy != sr:
            noisy_audio = AudioIO.resample_audio(noisy_audio, sr_noisy, sr)
    else:
        sr = sr_clean
    
    # Обрезаем до одинаковой длины
    min_len = min(len(clean_audio), len(noisy_audio))
    clean_audio = clean_audio[:min_len]
    noisy_audio = noisy_audio[:min_len]
    
    print(f"   Чистый файл:   {clean_path.name} ({len(clean_audio)/sr:.2f} сек)")
    print(f"   Зашумленный:   {noisy_path.name} ({len(noisy_audio)/sr:.2f} сек)")
    print(f"   Частота:       {sr} Гц")
    print(f"   Длительность:  {min_len/sr:.2f} сек")
    
    # Создаем денойзер
    denoiser = Denoiser(verbose=args.verbose)
    
    # Оцениваем каждый метод
    print(f"\n🔬 Оценка методов очистки...")
    
    results = {
        'test_file': str(noisy_path),
        'clean_file': str(clean_path),
        'sample_rate': sr,
        'duration': min_len / sr,
        'evaluation_date': datetime.now().isoformat(),
        'methods': {},
        'plot_data': {
            'metrics': {},
            'audios': {}
        }
    }
    
    all_denoised = {}
    
    for method in args.methods:
        if method not in denoiser.get_available_methods():
            print(f"  ⚠  Пропускаем неизвестный метод: {method}")
            continue
        
        try:
            metrics, denoised_audio = evaluate_method(
                clean_audio, noisy_audio, sr, method, denoiser
            )
            
            results['methods'][method] = metrics
            results['plot_data']['metrics'][method] = metrics
            all_denoised[method] = denoised_audio
            
            print(f"    ✓ SNR улучшение: {metrics['SNR_improvement_dB']:.2f} дБ")
            
        except Exception as e:
            print(f"    ❌ Ошибка при оценке {method}: {e}")
    
    # Определяем лучший метод
    if results['methods']:
        best_method = max(
            results['methods'].items(),
            key=lambda x: x[1]['SNR_improvement_dB']
        )
        
        print(f"\n🏆 Лучший метод: {best_method[0]}")
        print(f"   SNR улучшение: {best_method[1]['SNR_improvement_dB']:.2f} дБ")
        print(f"   SI-SNR: {best_method[1]['SI_SNR_dB']:.2f} дБ")
        
        # Сохраняем лучший результат
        best_audio = all_denoised[best_method[0]]
        output_dir = Path(args.output)
        best_output = output_dir / f"best_denoised_{best_method[0]}.wav"
        AudioIO.save_audio(best_audio, best_output, sr)
        print(f"   🎧 Лучший результат сохранен: {best_output}")
    
    # Сохраняем все результаты
    save_results(results, Path(args.output), args.plot)
    
    print(f"\n✅ Оценка завершена!")
    print(f"   Результаты сохранены в: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())