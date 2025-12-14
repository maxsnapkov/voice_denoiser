"""
Модуль для работы со спектрограммами и STFT преобразованиями.
"""
import numpy as np
import librosa
from typing import Tuple, Optional
import matplotlib.pyplot as plt
from scipy import signal


class STFTUtils:
    """Утилиты для работы с STFT и спектрограммами."""
    
    DEFAULT_N_FFT = 2048
    DEFAULT_HOP_LENGTH = 512
    DEFAULT_WINDOW = 'hann'
    
    @staticmethod
    def stft(
        audio: np.ndarray,
        n_fft: int = DEFAULT_N_FFT,
        hop_length: int = DEFAULT_HOP_LENGTH,
        window: str = DEFAULT_WINDOW,
        center: bool = True
    ) -> np.ndarray:
        """
        Вычисляет Short-Time Fourier Transform.
        
        Args:
            audio: Входной аудиосигнал
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            window: Тип окна
            center: Центрирование
            
        Returns:
            Комплексная спектрограмма
        """
        return librosa.stft(
            audio,
            n_fft=n_fft,
            hop_length=hop_length,
            window=window,
            center=center
        )
    
    @staticmethod
    def istft(
        stft_matrix: np.ndarray,
        hop_length: int = DEFAULT_HOP_LENGTH,
        window: str = DEFAULT_WINDOW,
        center: bool = True,
        length: Optional[int] = None
    ) -> np.ndarray:
        """
        Обратное STFT преобразование.
        
        Args:
            stft_matrix: Комплексная спектрограмма
            hop_length: Шаг между окнами
            window: Тип окна
            center: Центрирование
            length: Желаемая длина выходного сигнала
            
        Returns:
            Аудиосигнал
        """
        return librosa.istft(
            stft_matrix,
            hop_length=hop_length,
            window=window,
            center=center,
            length=length
        )
    
    @staticmethod
    def get_magnitude_phase(stft_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Разделяет спектрограмму на амплитуду и фазу.
        
        Args:
            stft_matrix: Комплексная спектрограмма
            
        Returns:
            Tuple[магнитуда, фаза]
        """
        magnitude = np.abs(stft_matrix)
        phase = np.angle(stft_matrix)
        
        return magnitude, phase
    
    @staticmethod
    def combine_magnitude_phase(magnitude: np.ndarray, phase: np.ndarray) -> np.ndarray:
        """
        Объединяет амплитуду и фазу в комплексную спектрограмму.
        
        Args:
            magnitude: Амплитудная спектрограмма
            phase: Фазовая спектрограмма
            
        Returns:
            Комплексная спектрограмма
        """
        return magnitude * np.exp(1j * phase)
    
    @staticmethod
    def power_to_db(spectrogram: np.ndarray, ref: float = 1.0, amin: float = 1e-10) -> np.ndarray:
        """
        Конвертирует спектрограмму в децибелы.
        
        Args:
            spectrogram: Амплитудная или мощностная спектрограмма
            ref: Референсное значение
            amin: Минимальное значение для логарифма
            
        Returns:
            Спектрограмма в dB
        """
        return librosa.amplitude_to_db(spectrogram, ref=ref, amin=amin)
    
    @staticmethod
    def db_to_power(spectrogram_db: np.ndarray, ref: float = 1.0) -> np.ndarray:
        """
        Конвертирует спектрограмму из децибелов в мощность.
        
        Args:
            spectrogram_db: Спектрограмма в dB
            ref: Референсное значение
            
        Returns:
            Амплитудная спектрограмма
        """
        return librosa.db_to_amplitude(spectrogram_db, ref=ref)
    
    @staticmethod
    def compute_mel_spectrogram(
        audio: np.ndarray,
        sr: int,
        n_fft: int = DEFAULT_N_FFT,
        hop_length: int = DEFAULT_HOP_LENGTH,
        n_mels: int = 128,
        fmin: float = 0.0,
        fmax: Optional[float] = None
    ) -> np.ndarray:
        """
        Вычисляет мел-спектрограмму.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            n_mels: Количество мел-банков
            fmin: Минимальная частота
            fmax: Максимальная частота
            
        Returns:
            Мел-спектрограмма
        """
        return librosa.feature.melspectrogram(
            y=audio,
            sr=sr,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            fmin=fmin,
            fmax=fmax
        )
    
    @staticmethod
    def compute_mfcc(
        audio: np.ndarray,
        sr: int,
        n_mfcc: int = 13,
        n_fft: int = DEFAULT_N_FFT,
        hop_length: int = DEFAULT_HOP_LENGTH,
        n_mels: int = 128
    ) -> np.ndarray:
        """
        Вычисляет MFCC (Mel-Frequency Cepstral Coefficients).
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            n_mfcc: Количество MFCC коэффициентов
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            n_mels: Количество мел-банков
            
        Returns:
            MFCC матрица
        """
        return librosa.feature.mfcc(
            y=audio,
            sr=sr,
            n_mfcc=n_mfcc,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels
        )
    
    @staticmethod
    def estimate_noise_profile(
        audio: np.ndarray,
        sr: int,
        noise_duration: float = 0.5,
        n_fft: int = DEFAULT_N_FFT,
        hop_length: int = DEFAULT_HOP_LENGTH
    ) -> np.ndarray:
        """
        Оценивает профиль шума из первых N секунд аудио.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            noise_duration: Длительность сегмента для оценки шума (сек)
            n_fft: Размер окна FFT
            hop_length: Шаг между окнами
            
        Returns:
            Профиль шума (спектральная маска)
        """
        # Количество семплов для шума
        noise_samples = int(noise_duration * sr)
        
        if noise_samples >= len(audio):
            noise_segment = audio
        else:
            noise_segment = audio[:noise_samples]
        
        # STFT шумового сегмента
        noise_stft = STFTUtils.stft(noise_segment, n_fft=n_fft, hop_length=hop_length)
        
        # Средняя амплитуда по времени
        noise_profile = np.mean(np.abs(noise_stft), axis=1, keepdims=True)
        
        return noise_profile
    
    @staticmethod
    def plot_spectrogram(
        spectrogram: np.ndarray,
        sr: int,
        hop_length: int = DEFAULT_HOP_LENGTH,
        title: str = "Спектрограмма",
        y_axis: str = "log",
        ax=None,
        save_path: Optional[str] = None
    ):
        """
        Визуализирует спектрограмму.
        
        Args:
            spectrogram: Спектрограмма (амплитуда или dB)
            sr: Частота дискретизации
            hop_length: Шаг между окнами
            title: Заголовок графика
            y_axis: Тип оси Y ('log' или 'linear')
            ax: Ось matplotlib (если None, создается новая)
            save_path: Путь для сохранения графика
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 6))
        
        # Определяем, является ли спектрограмма в dB
        if np.min(spectrogram) < 0:
            # Уже в dB
            spectrogram_display = spectrogram
        else:
            # Конвертируем в dB
            spectrogram_display = STFTUtils.power_to_db(spectrogram)
        
        # Отображение
        img = librosa.display.specshow(
            spectrogram_display,
            sr=sr,
            hop_length=hop_length,
            x_axis='time',
            y_axis=y_axis,
            ax=ax
        )
        
        ax.set_title(title)
        ax.set_xlabel('Время (сек)')
        ax.set_ylabel('Частота (Гц)')
        
        if ax is None:
            plt.colorbar(img, ax=ax, format="%+2.0f dB")
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.show()
        else:
            return img
    
    @staticmethod
    def spectral_subtraction(
        stft_matrix: np.ndarray,
        noise_profile: np.ndarray,
        over_subtraction: float = 1.5,
        spectral_floor: float = 0.01
    ) -> np.ndarray:
        """
        Применяет спектральное вычитание.
        
        Args:
            stft_matrix: Комплексная спектрограмма
            noise_profile: Профиль шума
            over_subtraction: Коэффициент перевычитания
            spectral_floor: Минимальный уровень спектра
            
        Returns:
            Очищенная спектрограмма
        """
        magnitude, phase = STFTUtils.get_magnitude_phase(stft_matrix)
        
        # Спектральное вычитание
        magnitude_clean = np.maximum(
            magnitude - over_subtraction * noise_profile,
            spectral_floor * magnitude
        )
        
        # Восстановление комплексной спектрограммы
        return STFTUtils.combine_magnitude_phase(magnitude_clean, phase)


# Алиасы для удобства
stft = STFTUtils.stft
istft = STFTUtils.istft
get_magnitude_phase = STFTUtils.get_magnitude_phase
combine_magnitude_phase = STFTUtils.combine_magnitude_phase