"""
Пакет core - ядро обработки аудио для подавления шума.
"""

from .audio_io import AudioIO, load_audio, save_audio, normalize_audio, get_audio_info
from .stft_utils import STFTUtils, stft, istft, get_magnitude_phase, combine_magnitude_phase
from .denoiser import Denoiser, create_denoiser, denoise_file

__version__ = "1.0.0"
__author__ = "Voice Denoiser Project"

__all__ = [
    # Основные классы
    'AudioIO',
    'STFTUtils',
    'Denoiser',
    
    # Функции
    'load_audio',
    'save_audio',
    'normalize_audio',
    'get_audio_info',
    'stft',
    'istft',
    'get_magnitude_phase',
    'combine_magnitude_phase',
    'create_denoiser',
    'denoise_file'
]

print(f"Voice Denoiser Core v{__version__} успешно загружен")