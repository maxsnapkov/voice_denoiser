#!/usr/bin/env python3
"""
Настройка логирования для Windows (исправление кодировки).
"""

import logging
import sys

def setup_logging():
    """Настраивает логирование с правильной кодировкой для Windows."""
    
    # Для Windows исправляем кодировку вывода
    if sys.platform == 'win32':
        # Создаем обработчик с UTF-8 кодировкой
        class UTF8StreamHandler(logging.StreamHandler):
            def __init__(self, stream=None):
                super().__init__(stream)
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    stream = self.stream
                    stream.write(msg + self.terminator)
                    self.flush()
                except UnicodeEncodeError:
                    # Пытаемся заменить проблемные символы
                    try:
                        msg = self.format(record)
                        # Заменяем эмодзи и другие символы на ASCII
                        msg = msg.encode('ascii', 'replace').decode('ascii')
                        stream = self.stream
                        stream.write(msg + self.terminator)
                        self.flush()
                    except:
                        pass
                except Exception:
                    self.handleError(record)
        
        # Настраиваем корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Удаляем существующие обработчики
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Добавляем наш обработчик
        handler = UTF8StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    return logging.getLogger(__name__)