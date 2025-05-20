import os
from config import config
from kb import main_menu
from typing import Union
from aiogram import types, Bot
from aiogram.types import message
import logging


async def save_file(
    bot: Bot,
    file: Union[types.Document, types.PhotoSize], 
    file_type: str,
    message: types.Message = None
) -> str:
    """Сохраняет файл на сервере и возвращает путь к нему"""
    try:
        os.makedirs(config.CHEATSHEETS_DIR, exist_ok=True)
        
        if file_type == "photo":
            file_id = message.photo[-1].file_id
            ext = ".jpg"
        elif file_type == "document":
            file_id = file.file_id
            ext = os.path.splitext(file.file_name)[1]
        else:
            return None
        
        file_path = os.path.join(config.CHEATSHEETS_DIR, f"{file_id}{ext}")
        
        # Получаем объект файла через бота и скачиваем
        file_object = await bot.get_file(file_id)
        await bot.download_file(file_object.file_path, destination=file_path)
        
        return file_path
    except Exception as e:
        logging.error(f"Error saving file: {e}")
        return None


def get_file_type(message: types.Message) -> str:
    """Определяет тип файла в сообщении"""
    if message.document:
        return "document"
    elif message.photo:
        return "photo"
    elif message.text:
        return "text"
    return None


def is_valid_file_type(message: types.Message) -> bool:
    """Проверяет, является ли файл допустимым"""
    file_type = get_file_type(message)
    if not file_type:
        return False
    
    if file_type == "document":
        ext = os.path.splitext(message.document.file_name)[1].lower()
        return ext in [".pdf", ".jpg", ".jpeg", ".png"]
    
    return file_type in ["photo", "text"]


async def delete_previous_messages(message: types.Message, count: int = 2):
    """Удаляет предыдущие сообщения в чате"""
    try:
        for i in range(1, count + 1):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - i)
            if message.message_id - i <= 1:
                break
    except Exception as e:
        pass


async def reply_with_menu(
    target: Union[types.Message, types.CallbackQuery], 
    text: str, 
    delete_prev: bool = True,
    delete_current: bool = False
):
    """
    Отправляет сообщение с главным меню
    :param target: Сообщение или callback
    :param text: Текст для отправки
    :param delete_prev: Удалять предыдущее сообщение
    :param delete_current: Удалять текущее сообщение (для callback)
    """
    if isinstance(target, types.CallbackQuery):
        chat_id = target.message.chat.id
        message_id = target.message.message_id
        await target.answer()  # закрываем callback
    else:
        chat_id = target.chat.id
        message_id = target.message_id
    
    try:
        if delete_prev:
            await target.bot.delete_message(chat_id=chat_id, message_id=message_id-1)
        if delete_current:
            await target.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение: {e}")
    
    await target.bot.send_message(chat_id, text, reply_markup=main_menu())
