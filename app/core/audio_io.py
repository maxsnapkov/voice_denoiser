"""
Модуль для работы с аудиофайлами: загрузка, сохранение, конвертация.
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Union, Tuple, Optional
import io
import warnings
warnings.filterwarnings('ignore')


class AudioIO:
    """Класс для операций ввода-вывода с аудиофайлами."""
    
    # Поддерживаемые форматы
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac'}
    
    @staticmethod
    def load_audio(
        filepath: Union[str, Path, bytes],
        sr: Optional[int] = 16000,
        mono: bool = True,
        duration: Optional[float] = None
    ) -> Tuple[np.ndarray, int]:
        """
        Загружает аудиофайл.
        
        Args:
            filepath: Путь к файлу или bytes
            sr: Частота дискретизации (если None - исходная)
            mono: Привести к моно
            duration: Максимальная длительность в секундах
            
        Returns:
            Tuple[audio_data, sample_rate]
            
        Raises:
            FileNotFoundError: Файл не найден
            ValueError: Неподдерживаемый формат
        """
        try:
            # Обработка bytes (например, из Telegram)
            if isinstance(filepath, bytes):
                audio, sr_orig = librosa.load(io.BytesIO(filepath), sr=sr, mono=mono, duration=duration)
            else:
                filepath = Path(filepath)
                if not filepath.exists():
                    raise FileNotFoundError(f"Файл {filepath} не найден")
                
                # Проверка формата
                if filepath.suffix.lower() not in AudioIO.SUPPORTED_FORMATS:
                    raise ValueError(f"Неподдерживаемый формат: {filepath.suffix}")
                
                audio, sr_orig = librosa.load(filepath, sr=sr, mono=mono, duration=duration)
            
            # Нормализация амплитуды
            audio = AudioIO.normalize_audio(audio)
            
            return audio, sr_orig if sr is None else sr
            
        except Exception as e:
            raise ValueError(f"Ошибка загрузки аудио: {str(e)}")
    
    @staticmethod
    def save_audio(
        audio: np.ndarray,
        filepath: Union[str, Path],
        sr: int = 16000,
        format: str = 'wav',
        subtype: str = 'PCM_16'
    ) -> Path:
        """
        Сохраняет аудио в файл.
        
        Args:
            audio: Аудиоданные
            filepath: Путь для сохранения
            sr: Частота дискретизации
            format: Формат файла
            subtype: Подтип (качество)
            
        Returns:
            Path: Путь к сохраненному файлу
        """
        filepath = Path(filepath)
        
        # Создаем директорию, если не существует
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Нормализация перед сохранением
        audio = AudioIO.normalize_audio(audio)
        
        # Сохранение
        sf.write(filepath, audio, sr, format=format, subtype=subtype)
        
        return filepath
    
    @staticmethod
    def normalize_audio(audio: np.ndarray, target_level: float = 0.9) -> np.ndarray:
        """
        Нормализует аудио по амплитуде.
        
        Args:
            audio: Входной аудиосигнал
            target_level: Целевой уровень (0.0 - 1.0)
            
        Returns:
            Нормализованный аудиосигнал
        """
        if len(audio) == 0:
            return audio
        
        # Текущий максимальный уровень
        current_max = np.max(np.abs(audio))
        
        if current_max > 0:
            # Коэффициент нормализации
            norm_factor = target_level / current_max
            
            # Применяем с ограничением
            audio_normalized = audio * norm_factor
            
            # Ограничиваем значения для избежания клиппинга
            audio_normalized = np.clip(audio_normalized, -1.0, 1.0)
            
            return audio_normalized
        
        return audio
    
    @staticmethod
    def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Изменяет частоту дискретизации аудио.
        
        Args:
            audio: Входной аудиосигнал
            orig_sr: Исходная частота дискретизации
            target_sr: Целевая частота дискретизации
            
        Returns:
            Передискретизированный сигнал
        """
        if orig_sr == target_sr:
            return audio
        
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    
    @staticmethod
    def get_audio_info(filepath: Union[str, Path]) -> dict:
        """
        Возвращает информацию об аудиофайле.
        
        Args:
            filepath: Путь к аудиофайлу
            
        Returns:
            Словарь с информацией
        """
        filepath = Path(filepath)
        
        # Используем soundfile для получения информации
        info = sf.info(filepath)
        
        # Основные характеристики
        duration = info.duration
        sr = info.samplerate
        channels = info.channels
        frames = info.frames
        
        # Статистики (загружаем для расчета)
        audio, _ = AudioIO.load_audio(filepath, sr=None, mono=False)
        
        if channels > 1:
            audio_mono = np.mean(audio, axis=0) if audio.ndim > 1 else audio
        else:
            audio_mono = audio
        
        return {
            'filepath': str(filepath),
            'filename': filepath.name,
            'duration': duration,
            'sample_rate': sr,
            'channels': channels,
            'frames': frames,
            'format': info.format,
            'bit_depth': info.subtype,
            'max_amplitude': float(np.max(np.abs(audio_mono))),
            'mean_amplitude': float(np.mean(np.abs(audio_mono))),
            'rms': float(np.sqrt(np.mean(audio_mono ** 2))),
            'size_bytes': filepath.stat().st_size
        }
    
    @staticmethod
    def convert_to_mono(audio: np.ndarray) -> np.ndarray:
        """
        Конвертирует многоканальный аудио в моно.
        
        Args:
            audio: Входной аудиосигнал (shape: [channels, samples] или [samples, channels])
            
        Returns:
            Моно аудиосигнал
        """
        if audio.ndim == 1:
            return audio
        
        # Если это многоканальный звук, усредняем
        return np.mean(audio, axis=0) if audio.shape[0] > audio.shape[1] else np.mean(audio, axis=1)
    
    @staticmethod
    def trim_silence(
        audio: np.ndarray,
        sr: int,
        top_db: int = 30,
        frame_length: int = 2048,
        hop_length: int = 512
    ) -> np.ndarray:
        """
        Обрезает тишину в начале и конце аудио.
        
        Args:
            audio: Входной аудиосигнал
            sr: Частота дискретизации
            top_db: Порог в dB для определения тишины
            frame_length: Длина кадра для анализа
            hop_length: Шаг для анализа
            
        Returns:
            Обрезанный аудиосигнал
        """
        # Используем librosa для обрезки тишины
        audio_trimmed, _ = librosa.effects.trim(
            audio,
            top_db=top_db,
            frame_length=frame_length,
            hop_length=hop_length
        )
        
        return audio_trimmed


# Алиасы для удобства
load_audio = AudioIO.load_audio
save_audio = AudioIO.save_audio
normalize_audio = AudioIO.normalize_audio
get_audio_info = AudioIO.get_audio_info