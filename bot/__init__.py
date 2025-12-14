"""
Telegram бот для очистки голосовых сообщений от шума.
"""

__version__ = "1.0.0"
__author__ = "Voice Denoiser Project"

import asyncio
import sys
import os

def setup_event_loop():
    """Настраивает event loop для Windows."""
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

setup_event_loop()
print(f"Voice Denoiser Bot v{__version__}")