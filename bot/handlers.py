"""
Обработчики сообщений для Telegram бота.
"""

import logging
from pathlib import Path
from typing import Optional
import asyncio

from telegram import Update, Message
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from telegram.constants import ParseMode

from . import keyboards, utils
from .api_client import (
    process_audio_with_progress,
    get_methods_list,
    check_api_health
)
from .config import settings

logger = logging.getLogger(__name__)

# Состояния пользователей
USER_STATES = {}


def get_user_state(user_id: int) -> dict:
    """
    Получает состояние пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Состояние пользователя
    """
    if user_id not in USER_STATES:
        USER_STATES[user_id] = {
            "waiting_for_audio": False,
            "processing": False,
            "current_file": None,
            "settings": utils.get_user_settings(user_id)
        }
    return USER_STATES[user_id]


def set_user_state(user_id: int, key: str, value):
    """
    Устанавливает состояние пользователя.
    
    Args:
        user_id: ID пользователя
        key: Ключ состояния
        value: Значение
    """
    state = get_user_state(user_id)
    state[key] = value


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"{settings.WELCOME_MESSAGE}"
    )
    
    # Отправляем приветственное сообщение с клавиатурой
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboards.get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"User {user.id} started the bot")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    await update.message.reply_text(
        settings.HELP_MESSAGE,
        reply_markup=keyboards.get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


async def methods_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /methods."""
    try:
        import asyncio
        # Показываем индикатор загрузки
        await utils.show_typing_indicator(update, context)
        
        # Получаем список методов
        methods_text = await get_methods_list()
        
        await update.message.reply_text(
            methods_text,
            reply_markup=keyboards.get_methods_keyboard(),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in methods_command: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить список методов. Проверьте, запущен ли API сервер.",
            reply_markup=keyboards.get_main_keyboard()
        )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /settings."""
    user_id = update.effective_user.id
    user_settings = get_user_state(user_id)["settings"]
    
    settings_text = (
        "⚙️ <b>Настройки очистки</b>\n\n"
        f"• Метод: <b>{user_settings.get('method', 'noisereduce')}</b>\n"
        f"• Частота: <b>{user_settings.get('sample_rate', 16000)} Гц</b>\n"
        f"• Тип голоса: <b>{user_settings.get('voice_type', 'broadband')}</b>\n"
        f"• Формат: <b>{user_settings.get('format', 'wav').upper()}</b>\n\n"
        "Выберите параметры ниже:"
    )
    
    await update.message.reply_text(
        settings_text,
        reply_markup=keyboards.get_settings_keyboard(),
        parse_mode=ParseMode.HTML
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status."""
    try:
        # Показываем индикатор загрузки
        await utils.show_typing_indicator(update, context)
        
        # Проверяем доступность API
        api_available, api_message = await check_api_health()
        
        # Формируем сообщение
        status_text = "📊 <b>Статус системы</b>\n\n"
        status_text += f"{api_message}\n\n"
        
        # Добавляем информацию о боте
        status_text += f"🤖 <b>Бот:</b> работает\n"
        status_text += f"📁 <b>Временные файлы:</b> {len(list(settings.TEMP_DIR.iterdir()))}\n"
        
        if api_available:
            # Пробуем получить статистику
            try:
                from .api_client import api_client
                async with api_client as client:
                    stats = await client.get_stats()
                    if stats:
                        uptime = stats.get("uptime_seconds", 0)
                        status_text += f"⏱️ <b>Время работы API:</b> {utils.format_duration(uptime)}\n"
            except:
                pass
        
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить статус системы.",
            reply_markup=keyboards.get_main_keyboard()
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel."""
    user_id = update.effective_user.id
    
    # Сбрасываем состояние пользователя
    if user_id in USER_STATES:
        USER_STATES[user_id] = {
            "waiting_for_audio": False,
            "processing": False,
            "current_file": None,
            "settings": USER_STATES[user_id].get("settings", {})
        }
    
    await update.message.reply_text(
        "✅ Операция отменена.",
        reply_markup=keyboards.get_main_keyboard()
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений."""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🎤 Очистить голосовое":
        await update.message.reply_text(
            "🎤 Отправьте голосовое сообщение для очистки.\n"
            "Или используйте /cancel для отмены.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        set_user_state(user_id, "waiting_for_audio", True)
        
    elif text == "📁 Отправить аудиофайл":
        await update.message.reply_text(
            "📁 Отправьте аудиофайл (WAV, MP3, OGG, FLAC, M4A, AAC).\n"
            "Максимальный размер: 50 MB.\n"
            "Используйте /cancel для отмены.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        set_user_state(user_id, "waiting_for_audio", True)
        
    elif text == "⚙️ Настройки":
        await settings_command(update, context)
        
    elif text == "📋 Методы":
        await methods_command(update, context)
        
    elif text == "❓ Помощь":
        await help_command(update, context)
        
    elif text == "📊 Статус":
        await status_command(update, context)
        
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Используйте /help для справки.",
            reply_markup=keyboards.get_main_keyboard()
        )


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик аудио сообщений."""
    user_id = update.effective_user.id
    user_state = get_user_state(user_id)
    
    # Проверяем, не обрабатывается ли уже файл
    if user_state.get("processing"):
        await update.message.reply_text(
            "⏳ Пожалуйста, дождитесь завершения текущей обработки.",
            reply_markup=keyboards.get_main_keyboard()
        )
        return
    
    # Скачиваем файл
    await utils.show_uploading_indicator(update, context)
    
    result = await utils.download_file_from_message(update, context)
    if not result:
        await update.message.reply_text(
            "❌ Не удалось загрузить файл. Пожалуйста, попробуйте еще раз.",
            reply_markup=keyboards.get_main_keyboard()
        )
        return
    
    file_path, filename = result
    
    # Проверяем расширение файла
    is_valid_ext, ext_error = utils.validate_file_extension(filename)
    if not is_valid_ext:
        await update.message.reply_text(
            ext_error,
            reply_markup=keyboards.get_main_keyboard()
        )
        file_path.unlink()
        return
    
    # Проверяем размер файла
    is_valid_size, size_error = utils.validate_file_size(file_path)
    if not is_valid_size:
        await update.message.reply_text(
            size_error,
            reply_markup=keyboards.get_main_keyboard()
        )
        file_path.unlink()
        return
    
    # Сохраняем информацию о файле
    set_user_state(user_id, "current_file", str(file_path))
    set_user_state(user_id, "processing", True)
    
    # Получаем настройки пользователя
    user_settings = user_state["settings"]
    
    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text(
        "⏳ Начинаю обработку аудио...\n"
        f"Метод: <b>{user_settings.get('method', 'noisereduce')}</b>\n"
        "Это может занять несколько секунд.",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Обрабатываем аудио
        await utils.show_processing_indicator(update, context)
        
        audio_data, info_message = await process_audio_with_progress(
            file_path,
            filename,
            method=user_settings.get("method", "noisereduce"),
            sample_rate=user_settings.get("sample_rate"),
            voice_type=user_settings.get("voice_type", "broadband")
        )
        
        if audio_data:
            # Отправляем результат
            await processing_msg.edit_text(info_message)
            
            # Отправляем аудиофайл
            output_filename = f"cleaned_{Path(filename).stem}.wav"
            
            await update.message.reply_audio(
                audio=audio_data,
                filename=output_filename,
                caption="✅ Очищенное аудио",
                reply_markup=keyboards.get_main_keyboard()
            )
            
        else:
            await processing_msg.edit_text(
                f"❌ Ошибка обработки:\n{info_message}",
                reply_markup=keyboards.get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Processing error: {e}")
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при обработке:\n{str(e)}",
            reply_markup=keyboards.get_main_keyboard()
        )
        
    finally:
        # Очищаем состояние
        set_user_state(user_id, "processing", False)
        set_user_state(user_id, "current_file", None)
        
        # Удаляем временный файл
        if file_path.exists():
            file_path.unlink()


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик инлайн-кнопок."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    try:
        print(data)
        if data.startswith("method_"):
            # Выбор метода очистки
            method = data.replace('method_', '')
            user_state = get_user_state(user_id)
            user_state["settings"]["method"] = method
            
            if method == "bandpass":
                # Для bandpass метода нужно выбрать тип голоса
                await query.edit_message_text(
                    "🎚️ Выбран метод: <b>Bandpass фильтрация</b>\n"
                    "Выберите тип голоса:",
                    reply_markup=keyboards.get_voice_type_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            else:
                # Для других методов просто уведомляем и оставляем старую клавиатуру
                await query.edit_message_text(
                    f"✅ Выбран метод: <b>{method}</b>\n\n"
                    "Теперь отправьте аудиофайл для очистки.",
                    reply_markup=keyboards.get_methods_keyboard(),  # Оставляем ту же клавиатуру
                    parse_mode=ParseMode.HTML
                )
        
        elif data.startswith("voice_"):
            # Выбор типа голоса
            voice_type = data.split("_")[1]
            user_state = get_user_state(user_id)
            user_state["settings"]["voice_type"] = voice_type
            
            voice_names = {
                "male": "👨 Мужской",
                "female": "👩 Женский",
                "broadband": "🔊 Широкополосный"
            }
            
            # Убираем инлайн-клавиатуру и показываем сообщение
            await query.edit_message_text(
                f"✅ Настройки сохранены:\n"
                f"• Метод: <b>bandpass</b>\n"
                f"• Тип голоса: <b>{voice_names.get(voice_type, voice_type)}</b>\n\n"
                "Теперь отправьте аудиофайл для очистки.",
                reply_markup=None,  # Убираем инлайн-клавиатуру
                parse_mode=ParseMode.HTML
            )
            
            # Отправляем основную клавиатуру в новом сообщении
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Используйте кнопки ниже:",
                reply_markup=keyboards.get_main_keyboard()
            )
        
        elif data.startswith("rate_"):
            # Выбор частоты дискретизации
            rate = int(data.split("_")[1])
            user_state = get_user_state(user_id)
            user_state["settings"]["sample_rate"] = rate
            
            await query.edit_message_text(
                f"✅ Частота дискретизации установлена: <b>{rate} Гц</b>",
                reply_markup=keyboards.get_settings_keyboard(),  # Возвращаем клавиатуру настроек
                parse_mode=ParseMode.HTML
            )
        
        elif data.startswith("format_"):
            # Выбор формата
            fmt = data.split("_")[1]
            user_state = get_user_state(user_id)
            user_state["settings"]["format"] = fmt
            
            await query.edit_message_text(
                f"✅ Формат установлен: <b>{fmt.upper()}</b>",
                reply_markup=keyboards.get_settings_keyboard(),
                parse_mode=ParseMode.HTML
            )
        
        elif data == "save_settings":
            # Сохранение настроек
            user_state = get_user_state(user_id)
            utils.save_user_settings(user_id, user_state["settings"])
            
            await query.edit_message_text(
                "✅ Настройки сохранены!",
                reply_markup=None
            )
            
            # Отправляем основную клавиатуру
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Используйте кнопки ниже:",
                reply_markup=keyboards.get_main_keyboard()
            )
        
        elif data == "cancel_settings":
            # Отмена настроек
            await query.edit_message_text(
                "❌ Настройки не сохранены.",
                reply_markup=None
            )
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Возвращаюсь в главное меню:",
                reply_markup=keyboards.get_main_keyboard()
            )
        
        elif data == "back_to_methods":
            # Возврат к выбору метода
            await methods_command(update, context)
        
        elif data == "cancel":
            # Отмена операции
            await cancel_command(update, context)
        
        elif data == "admin_stats":
            # Статистика для администратора
            if not utils.is_admin(user_id):
                await query.edit_message_text("⛔ Доступ запрещен.")
                return
            
            from .api_client import api_client
            async with api_client as client:
                stats = await client.get_stats()
            
            stats_text = "📊 <b>Статистика API</b>\n\n"
            if stats:
                for key, value in stats.items():
                    stats_text += f"• {key}: <b>{value}</b>\n"
            else:
                stats_text += "❌ Не удалось получить статистику"
            
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
        
        elif data == "admin_cleanup":
            # Очистка кеша
            if not utils.is_admin(user_id):
                await query.edit_message_text("⛔ Доступ запрещен.")
                return
            
            utils.cleanup_temp_files()
            file_count = len(list(settings.TEMP_DIR.iterdir()))
            
            await query.edit_message_text(
                f"✅ Кеш очищен. Файлов осталось: {file_count}",
                reply_markup=None
            )
    
    except Exception as e:
        logger.error(f"Error in callback query handler: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=None
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Отправляем сообщение об ошибке пользователю
    if update and update.effective_chat:
        error_message = (
            "❌ Произошла непредвиденная ошибка.\n"
            "Пожалуйста, попробуйте еще раз или свяжитесь с администратором."
        )
        
        try:
            await update.effective_chat.send_message(
                error_message,
                reply_markup=keyboards.get_main_keyboard()
            )
        except:
            pass  # Не удалось отправить сообщение


def setup_handlers(application):
    """
    Настраивает обработчики для приложения.
    
    Args:
        application: Экземпляр Application
    """
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("methods", methods_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    ))
    
    # Обработчик аудио сообщений
    audio_filters = filters.VOICE | filters.AUDIO | (
        filters.Document.MimeType("audio/*")
    )
    application.add_handler(MessageHandler(
        audio_filters,
        handle_audio_message
    ))
    
    # Обработчик инлайн-кнопок
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем периодическую очистку временных файлов
    asyncio.create_task(periodic_cleanup())


async def periodic_cleanup():
    """Периодическая очистка временных файлов."""
    import asyncio
    
    while True:
        await asyncio.sleep(3600)  # Каждый час
        utils.cleanup_temp_files()