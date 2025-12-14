#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота.
"""

import sys
import asyncio
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.bot import VoiceDenoiserBot

async def run_bot():
    bot = VoiceDenoiserBot()
    await bot.run()

if __name__ == "__main__":
    # Настраиваем event loop для Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)