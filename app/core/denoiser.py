"""
Основной модуль для подавления шума в аудио.
Реализует несколько методов, включая лучший (полосовую фильтрацию).
"""
import numpy as np
import librosa
from scipy import signal
from typing import Union, Optional, Dict, Any
import noisereduce as nr
from pathlib import Path

from .audio_io import AudioIO
from .stft_utils import STFTUtils


class Denoiser:
    """
    Класс для подавления шума в аудиосигналах.
    Поддерживает несколько алгоритмов очистки.
    """
    
    # Константы для методов
    METHOD_BANDPASS = "bandpass"  # Полосовая фильтрация
    METHOD_SPECTRAL_SUBTRACTION = "spectral_subtraction"
    METHOD_WIENER = "wiener"
    METHOD_NOISEREDUCE = "noisereduce"
    METHOD_ADAPTIVE = "adaptive"  # Адаптивный (комбинированный)
    
    # Диапазоны частот для полосовой фильтрации (Гц)
    SPEECH_FREQ_RANGES = {
        'male': (80, 8000),      # Мужской голос
        'female': (100, 10000),  # Женский голос
        'broadband': (50, 12000) # Широкополосный
    }
    
    def __init__(
        self,
        default_method: str = METHOD_ADAPTIVE,
        target_sr: int = 16000,
        verbose: bool = False
    ):
        """
        Инициализация денойзера.
        
        Args:
            default_method: Метод по умолчанию
            target_sr: Целевая частота дискретизации
            verbose: Режим подробного вывода
        """
        self.default_method = default_method
        self.target_sr = target_sr
        self.verbose = verbose
        
        # Параметры методов
        self.method_params = {
            self.METHOD_BANDPASS: {
                'order': 5,
                'voice_type': 'broadband'
            },
            self.METHOD_SPECTRAL_SUBTRACTION: {
                'n_fft': 2048,
                'hop_length': 512,
                'over_subtraction': 1.5,
                'spectral_floor': 0.01,
                'noise_duration': 0.5
            },
            self.METHOD_WIENER: {
                'n_fft': 2048,
                'hop_length': 512,
                'smoothing': 0.98
            },
            self.METHOD_NOISEREDUCE: {
                'stationary': False,
                'prop_decrease': 0.9,
                'n_fft': 2048,
                'hop_length': 512
            },
            self.METHOD_ADAPTIVE: {
                'initial_method': self.METHOD_BANDPASS,
                'fallback_method': self.METHOD_NOISEREDUCE
            }
        }
        
        if self.verbose:
            print(f"Denoiser инициализирован. Метод по умолчанию: {default_method}")
    
    def denoise(
        self,
        audio: Union[np.ndarray, str, Path, bytes],
        sr: Optional[int] = None,
        method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Основной метод для очистки аудио от шума.
        
        Args:
            audio: Аудиоданные, путь к файлу или bytes
            sr: Частота дискретизации (если audio это массив)
            method: Метод очистки (если None, используется default_method)
            **kwargs: Дополнительные параметры для метода
            
        Returns:
            Словарь с результатами:
            {
                'audio': очищенный аудиосигнал,
                'sample_rate': частота дискретизации,
                'method': использованный метод,
                'processing_time': время обработки,
                'original_shape': исходная форма
            }
        """
        import time
        start_time = time.time()
        
        # Определяем метод
        method = method or self.default_method
        
        # Загружаем аудио, если нужно
        if isinstance(audio, (str, Path, bytes)):
            audio_data, orig_sr = AudioIO.load_audio(audio, sr=self.target_sr)
        else:
            audio_data = audio
            orig_sr = sr or self.target_sr
            
            # Ресемплируем, если нужно
            if orig_sr != self.target_sr:
                audio_data = AudioIO.resample_audio(audio_data, orig_sr, self.target_sr)
                orig_sr = self.target_sr
        
        # Сохраняем оригинальную форму
        original_shape = audio_data.shape
        
        # Применяем выбранный метод
        if method == self.METHOD_BANDPASS:
            denoised_audio = self._bandpass_filter(audio_data, orig_sr, **kwargs)
        
        elif method == self.METHOD_SPECTRAL_SUBTRACTION:
            denoised_audio = self._spectral_subtraction(audio_data, orig_sr, **kwargs)
        
        elif method == self.METHOD_WIENER:
            denoised_audio = self._wiener_filter(audio_data, orig_sr, **kwargs)
        
        elif method == self.METHOD_NOISEREDUCE:
            denoised_audio = self._noisereduce_filter(audio_data, orig_sr, **kwargs)
        
        elif method == self.METHOD_ADAPTIVE:
            denoised_audio = self._adaptive_denoise(audio_data, orig_sr, **kwargs)
        
        else:
            raise ValueError(f"Неизвестный метод: {method}")
        
        # Нормализуем результат
        denoised_audio = AudioIO.normalize_audio(denoised_audio)
        
        # Обрезаем тишину
        denoised_audio = AudioIO.trim_silence(denoised_audio, orig_sr)
        
        # Вычисляем метрики
        processing_time = time.time() - start_time
        
        if self.verbose:
            print(f"Обработка завершена. Метод: {method}, время: {processing_time:.2f} сек")
        
        return {
            'audio': denoised_audio,
            'sample_rate': orig_sr,
            'method': method,
            'processing_time': processing_time,
            'original_shape': original_shape,
            'denoised_shape': denoised_audio.shape
        }
    
    def _bandpass_filter(
        self,
        audio: np.ndarray,
        sr: int,
        lowcut: Optional[float] = None,
        highcut: Optional[float] = None,
        order: int = 5,
        voice_type: str = 'broadband'
    ) -> np.ndarray:
        """
        Полосовая фильтрация (лучший метод по тестам).
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            lowcut: Нижняя частота среза (Гц)
            highcut: Верхняя частота среза (Гц)
            order: Порядок фильтра
            voice_type: Тип голоса для выбора диапазона
            
        Returns:
            Отфильтрованный аудиосигнал
        """
        # Выбираем диапазон частот
        if lowcut is None or highcut is None:
            freq_range = self.SPEECH_FREQ_RANGES.get(voice_type, self.SPEECH_FREQ_RANGES['broadband'])
            lowcut = freq_range[0] if lowcut is None else lowcut
            highcut = freq_range[1] if highcut is None else highcut
        
        # Проверка параметров
        nyquist = 0.5 * sr
        lowcut = min(lowcut, nyquist - 1)
        highcut = min(highcut, nyquist - 1)
        
        if lowcut >= highcut:
            raise ValueError(f"lowcut ({lowcut}) должен быть меньше highcut ({highcut})")
        
        # Нормализация частот
        low = lowcut / nyquist
        high = highcut / nyquist
        
        # Создание фильтра Баттерворта
        b, a = signal.butter(order, [low, high], btype='band')
        
        # Применение фильтра с нулевой фазовой задержкой
        audio_filtered = signal.filtfilt(b, a, audio)
        
        # Дополнительно: применямем notch фильтр для удаления сетевой частоты (50 Гц)
        if 45 <= lowcut <= 55 or 45 <= highcut <= 55:
            # Пропускаем, чтобы не удалять речевые частоты
            pass
        else:
            # Удаляем сетевую частоту, если она не в речевом диапазоне
            audio_filtered = self._notch_filter(audio_filtered, sr, freq=50.0, Q=30.0)
        
        return audio_filtered
    
    def _notch_filter(
        self,
        audio: np.ndarray,
        sr: int,
        freq: float = 50.0,
        Q: float = 30.0
    ) -> np.ndarray:
        """
        Notch фильтр для удаления конкретной частоты (например, сетевой помехи).
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            freq: Частота для удаления (Гц)
            Q: Добротность фильтра
            
        Returns:
            Отфильтрованный аудиосигнал
        """
        # Нормализация частоты
        w0 = freq / (sr / 2)
        
        # Создание notch фильтра
        b, a = signal.iirnotch(w0, Q)
        
        # Применение фильтра
        return signal.filtfilt(b, a, audio)
    
    def _spectral_subtraction(
        self,
        audio: np.ndarray,
        sr: int,
        n_fft: int = 2048,
        hop_length: int = 512,
        over_subtraction: float = 1.5,
        spectral_floor: float = 0.01,
        noise_duration: float = 0.5
    ) -> np.ndarray:
        """
        Спектральное вычитание.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            over_subtraction: Коэффициент перевычитания
            spectral_floor: Минимальный уровень спектра
            noise_duration: Длительность сегмента для оценки шума
            
        Returns:
            Очищенный аудиосигнал
        """
        # Оценка профиля шума
        noise_profile = STFTUtils.estimate_noise_profile(
            audio, sr,
            noise_duration=noise_duration,
            n_fft=n_fft,
            hop_length=hop_length
        )
        
        # STFT преобразование
        stft_matrix = STFTUtils.stft(audio, n_fft=n_fft, hop_length=hop_length)
        
        # Спектральное вычитание
        stft_clean = STFTUtils.spectral_subtraction(
            stft_matrix,
            noise_profile,
            over_subtraction=over_subtraction,
            spectral_floor=spectral_floor
        )
        
        # Обратное STFT
        audio_clean = STFTUtils.istft(stft_clean, hop_length=hop_length, length=len(audio))
        
        return audio_clean
    
    def _wiener_filter(
        self,
        audio: np.ndarray,
        sr: int,
        n_fft: int = 2048,
        hop_length: int = 512,
        smoothing: float = 0.98
    ) -> np.ndarray:
        """
        Адаптивный фильтр Винера.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            smoothing: Коэффициент сглаживания
            
        Returns:
            Очищенный аудиосигнал
        """
        # STFT преобразование
        stft_matrix = STFTUtils.stft(audio, n_fft=n_fft, hop_length=hop_length)
        magnitude, phase = STFTUtils.get_magnitude_phase(stft_matrix)
        
        # Оценка PSD шума из первых кадров
        noise_frames = int(0.5 * sr / hop_length)
        if noise_frames < magnitude.shape[1]:
            noise_psd = np.mean(np.abs(stft_matrix[:, :noise_frames]) ** 2, axis=1)
        else:
            noise_psd = np.mean(np.abs(stft_matrix) ** 2, axis=1)
        
        # Адаптивный фильтр Винера
        magnitude_squared = magnitude ** 2
        signal_psd_est = np.maximum(magnitude_squared - noise_psd[:, np.newaxis], 0)
        prior_snr = signal_psd_est / (noise_psd[:, np.newaxis] + 1e-10)
        
        # Веса Винера
        wiener_weights = prior_snr / (prior_snr + 1)
        
        # Применение фильтра
        magnitude_clean = magnitude * wiener_weights
        
        # Обратное STFT
        stft_clean = STFTUtils.combine_magnitude_phase(magnitude_clean, phase)
        audio_clean = STFTUtils.istft(stft_clean, hop_length=hop_length, length=len(audio))
        
        return audio_clean
    
    def _noisereduce_filter(
        self,
        audio: np.ndarray,
        sr: int,
        stationary: bool = False,
        prop_decrease: float = 0.9,
        n_fft: int = 2048,
        hop_length: int = 512
    ) -> np.ndarray:
        """
        Использование библиотеки noisereduce.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            stationary: Тип шума (стационарный/нестационарный)
            prop_decrease: Степень уменьшения шума
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            
        Returns:
            Очищенный аудиосигнал
        """
        # Оценка шума из первых 0.5 секунд
        noise_clip = audio[:int(0.5 * sr)]
        
        # Применение noisereduce
        audio_clean = nr.reduce_noise(
            y=audio,
            sr=sr,
            y_noise=noise_clip,
            stationary=stationary,
            prop_decrease=prop_decrease,
            n_fft=n_fft,
            hop_length=hop_length,
            n_jobs=1
        )
        
        return audio_clean
    
    def _adaptive_denoise(
        self,
        audio: np.ndarray,
        sr: int,
        initial_method: str = METHOD_BANDPASS,
        fallback_method: str = METHOD_NOISEREDUCE
    ) -> np.ndarray:
        """
        Адаптивный метод: комбинирует несколько подходов.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            initial_method: Первичный метод
            fallback_method: Резервный метод
            
        Returns:
            Очищенный аудиосигнал
        """
        # 1. Сначала полосовая фильтрация для удаления внеполосных шумов
        audio_stage1 = self._bandpass_filter(audio, sr, voice_type='broadband')
        
        # 2. Оценка уровня шума
        noise_level = self._estimate_noise_level(audio_stage1)
        
        if self.verbose:
            print(f"Уровень шума: {noise_level:.4f}")
        
        # 3. Выбор метода в зависимости от уровня шума
        if noise_level < 0.05:  # Низкий уровень шума
            # Только полосовая фильтрация
            return audio_stage1
        
        elif noise_level < 0.15:  # Средний уровень шума
            # Добавляем спектральное вычитание
            audio_stage2 = self._spectral_subtraction(audio_stage1, sr)
            return audio_stage2
        
        else:  # Высокий уровень шума
            # Используем noisereduce
            audio_stage2 = self._spectral_subtraction(audio_stage1, sr)
            audio_stage3 = self._noisereduce_filter(audio_stage2, sr)
            return audio_stage3
    
    def _estimate_noise_level(self, audio: np.ndarray) -> float:
        """
        Оценивает уровень шума в сигнале.
        
        Args:
            audio: Аудиосигнал
            
        Returns:
            Уровень шума (0.0 - 1.0)
        """
        # Используем отношение энергии в высоких частотах к общей энергии
        # Шум обычно имеет больше высокочастотных компонент
        
        # FFT
        fft_result = np.fft.fft(audio)
        freqs = np.fft.fftfreq(len(audio))
        
        # Мощность в разных частотных диапазонах
        mask_low = np.abs(freqs) < 0.1  # Низкие частоты
        mask_high = np.abs(freqs) > 0.3  # Высокие частоты
        
        power_total = np.sum(np.abs(fft_result) ** 2)
        power_high = np.sum(np.abs(fft_result[mask_high]) ** 2)
        
        if power_total > 0:
            noise_ratio = power_high / power_total
        else:
            noise_ratio = 0.0
        
        return min(noise_ratio, 1.0)
    
    def get_available_methods(self) -> list:
        """Возвращает список доступных методов."""
        return [
            self.METHOD_BANDPASS,
            self.METHOD_SPECTRAL_SUBTRACTION,
            self.METHOD_WIENER,
            self.METHOD_NOISEREDUCE,
            self.METHOD_ADAPTIVE
        ]
    
    def get_method_description(self, method: str) -> str:
        """Возвращает описание метода."""
        descriptions = {
            self.METHOD_BANDPASS: "Полосовая фильтрация - удаляет частоты вне речевого диапазона",
            self.METHOD_SPECTRAL_SUBTRACTION: "Спектральное вычитание - классический метод",
            self.METHOD_WIENER: "Фильтр Винера - адаптивный статистический метод",
            self.METHOD_NOISEREDUCE: "Noisereduce - современная библиотека на основе ML",
            self.METHOD_ADAPTIVE: "Адаптивный метод - комбинация нескольких подходов"
        }
        
        return descriptions.get(method, "Неизвестный метод")


# Фабрика для удобного создания денойзера
def create_denoiser(method: str = "adaptive", **kwargs) -> Denoiser:
    """
    Создает экземпляр Denoiser с указанными параметрами.
    
    Args:
        method: Метод очистки
        **kwargs: Дополнительные параметры для Denoiser
        
    Returns:
        Экземпляр Denoiser
    """
    return Denoiser(default_method=method, **kwargs)


# Быстрая функция для обработки файла
def denoise_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    method: str = "adaptive",
    **kwargs
) -> Dict[str, Any]:
    """
    Быстрая обработка файла.
    
    Args:
        input_path: Путь к входному файлу
        output_path: Путь для сохранения результата
        method: Метод очистки
        **kwargs: Дополнительные параметры
        
    Returns:
        Результаты обработки
    """
    denoiser = create_denoiser(method=method, verbose=True)
    
    # Обработка
    result = denoiser.denoise(input_path, method=method, **kwargs)
    
    # Сохранение
    AudioIO.save_audio(result['audio'], output_path, result['sample_rate'])
    
    print(f"Файл сохранен: {output_path}")
    print(f"Метод: {result['method']}, время: {result['processing_time']:.2f} сек")
    
    return result