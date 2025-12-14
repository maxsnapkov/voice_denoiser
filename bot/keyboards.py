"""
Клавиатуры для Telegram бота.
"""

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton
)
from typing import List, Tuple


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру.
    
    Returns:
        ReplyKeyboardMarkup
    """
    keyboard = [
        [KeyboardButton("🎤 Очистить голосовое")],
        [KeyboardButton("📁 Отправить аудиофайл")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("📋 Методы")],
        [KeyboardButton("❓ Помощь"), KeyboardButton("📊 Статус")]
    ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_methods_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для выбора метода очистки.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton("🔄 Adaptive", callback_data="method_adaptive"),
            InlineKeyboardButton("🎚️ Bandpass", callback_data="method_bandpass")
        ],
        [
            InlineKeyboardButton("📉 Spectral", callback_data="method_spectral_subtraction"),
            InlineKeyboardButton("🔧 Wiener", callback_data="method_wiener")
        ],
        [
            InlineKeyboardButton("🤖 Noisereduce", callback_data="method_noisereduce"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel")
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


def get_voice_type_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для выбора типа голоса.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton("👨 Мужской", callback_data="voice_male"),
            InlineKeyboardButton("👩 Женский", callback_data="voice_female")
        ],
        [
            InlineKeyboardButton("🔊 Широкополосный", callback_data="voice_broadband"),
            InlineKeyboardButton("↩️ Назад", callback_data="back_to_methods")
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для настроек.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton("🎵 Частота 16кГц", callback_data="rate_16000"),
            InlineKeyboardButton("🎵 Частота 22кГц", callback_data="rate_22050")
        ],
        [
            InlineKeyboardButton("🎵 Частота 44кГц", callback_data="rate_44100"),
            InlineKeyboardButton("🎵 Частота 48кГц", callback_data="rate_48000")
        ],
        [
            InlineKeyboardButton("📁 Формат WAV", callback_data="format_wav"),
            InlineKeyboardButton("📁 Формат MP3", callback_data="format_mp3")
        ],
        [
            InlineKeyboardButton("✅ Сохранить", callback_data="save_settings"),
            InlineKeyboardButton("↩️ Отмена", callback_data="cancel_settings")
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру с кнопкой отмены.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(buttons)


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для подтверждения.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру для администратора.
    
    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [InlineKeyboardButton("📊 Статистика API", callback_data="admin_stats")],
        [InlineKeyboardButton("🧹 Очистить кеш", callback_data="admin_cleanup")],
        [InlineKeyboardButton("🔄 Перезагрузить", callback_data="admin_reload")]
    ]
    
    return InlineKeyboardMarkup(buttons)