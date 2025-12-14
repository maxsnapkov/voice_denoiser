"""
Основной файл Telegram бота.
"""

import logging
import asyncio
from pathlib import Path
import signal
import sys

from telegram.ext import Application
from telegram import BotCommand

from . import handlers, utils
from .config import settings

# Добавляем путь для импорта setup_logging
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования
try:
    from setup_logging import setup_logging
    setup_logging()
except ImportError:
    # Если файла нет, используем стандартное логирование
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

from . import handlers, utils
from .config import settings

logger = logging.getLogger(__name__)


class VoiceDenoiserBot:
    """Основной класс бота для очистки аудио."""
    
    def __init__(self):
        """Инициализация бота."""
        self.application = None
        self.is_running = False
        self._shutting_down = False  # Флаг для предотвращения повторного shutdown
        
    async def setup(self):
        """Настройка бота."""
        logger.info("Настройка бота...")
        
        # Создаем приложение
        self.application = Application.builder() \
            .token(settings.BOT_TOKEN) \
            .build()
        
        # Настраиваем команды бота
        await self.setup_commands()
        
        # Настраиваем обработчики
        handlers.setup_handlers(self.application)
        
        # Настраиваем обработку сигналов
        self.setup_signal_handlers()
        
        logger.info("Бот настроен")
    
    async def setup_commands(self):
        """Настраивает команды меню бота."""
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Показать справку"),
            BotCommand("methods", "Показать доступные методы очистки"),
            BotCommand("settings", "Настройки очистки"),
            BotCommand("status", "Статус работы бота"),
            BotCommand("cancel", "Отменить текущую операцию"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Команды бота настроены")

    
    def setup_signal_handlers(self):
        """Настраивает обработчики сигналов."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self.signal_handler)

    async def shutdown(self):
        """Graceful shutdown бота."""
        #if self._shutting_down:
        #    return
        
        self._shutting_down = True
        logger.info("Завершение работы бота...")
        
        try:
            # Останавливаем polling если запущен
            if self.application:
                if hasattr(self.application, 'updater') and self.application.updater.running:
                    logger.info("Останавливаю polling...")
                    await self.application.updater.stop()
                
                # Останавливаем приложение
                logger.info("Останавливаю приложение...")
                await self.application.stop()
                await self.application.shutdown()
            
            # Очищаем временные файлы
            logger.info("Очищаю временные файлы...")
            utils.cleanup_temp_files()
        
        except Exception as e:
            logger.error(f"Ошибка при завершении работы: {e}")
        finally:
            logger.info("Бот остановлен")
            print("👋 Бот остановлен")
            raise KeyboardInterrupt()

    def signal_handler(self, signum, frame):
        """Обработчик сигналов для Unix-систем."""
        print(f"\n🛑 Получен сигнал {signum}, планирую graceful shutdown...")
        
        # Создаем асинхронную задачу для shutdown
        loop = asyncio.get_event_loop()
        self._shutting_down = True
        if loop.is_running():
            asyncio.create_task(self.shutdown())
        else:
            # Если loop не запущен, запускаем shutdown синхронно
            loop.run_until_complete(self.shutdown())
    
    async def run(self):
        """Запускает бота."""
        if not self.application:
            await self.setup()
        
        logger.info("Запуск бота...")
        
        # Проверяем доступность API
        from .api_client import check_api_health
        api_available, api_message = await check_api_health()
        
        if not api_available:
            logger.warning(f"API недоступен: {api_message}")
            print(f"⚠  Внимание: {api_message}")
            print("   Проверьте, запущен ли FastAPI сервер.")
            print("   Для запуска: python run_api.py")
            # Не останавливаемся, бот может работать в офлайн режиме
        else:
            logger.info("API доступен")
        
        # Очищаем старые временные файлы
        utils.cleanup_temp_files()
        
        # Устанавливаем флаг запуска
        self.is_running = True
        
        logger.info(f"Бот запущен как @{settings.BOT_USERNAME}")
        print(f"\n🤖 Бот запущен: @{settings.BOT_USERNAME}")
        print("   Используйте /start для начала работы")
        print("   Ctrl+C для остановки\n")
        
        try:
            # Инициализируем приложение
            await self.application.initialize()
            await self.application.start()
            
            # Запускаем polling
            await self.application.updater.start_polling()
            
            # Основной цикл работы бота
            while self.is_running:
                try:
                    # Проверяем, работает ли polling
                    if not self.application.updater.running:
                        logger.error("Polling остановился, перезапускаем...")
                        await self.application.updater.start_polling()
                    
                    # Ждем 1 секунду
                    await asyncio.sleep(1)
                    
                    # Периодическая очистка временных файлов
                    utils.cleanup_temp_files()
                    
                except Exception as e:
                    logger.error(f"Ошибка в основном цикле: {e}")
                    await asyncio.sleep(5)  # Ждем перед повторной попыткой
                    
        except asyncio.CancelledError:
            logger.info("Работа бота отменена")
        except Exception as e:
            logger.error(f"Критическая ошибка в работе бота: {e}")
            raise
        finally:
            # Гарантированная очистка
            await self.shutdown()

def main():
    """Точка входа для запуска бота."""
    bot = VoiceDenoiserBot()
    
    try:
        # Запускаем бота
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())