"""
Пакет scripts - вспомогательные скрипты для работы с Voice Denoiser.
"""

import sys
from pathlib import Path

# Добавляем путь к корню проекта
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

__version__ = "1.0.0"
__all__ = []

print(f"Voice Denoiser Scripts v{__version__} загружены")