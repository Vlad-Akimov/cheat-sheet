import os
from config import config
from typing import Union
from aiogram import types
import logging

def save_file(file: Union[types.Document, types.PhotoSize], file_type: str) -> str:
    """Сохраняет файл на сервере и возвращает путь к нему"""
    try:
        # Создаем папку, если ее нет
        os.makedirs(config.CHEATSHEETS_DIR, exist_ok=True)
        
        # Генерируем уникальное имя файла
        file_id = file.file_id
        ext = ""
        
        if file_type == "photo":
            ext = ".jpg"
        elif file_type == "document":
            ext = os.path.splitext(file.file_name)[1]
        
        file_path = os.path.join(config.CHEATSHEETS_DIR, f"{file_id}{ext}")
        
        # Скачиваем файл
        file.get_file().download(file_path)
        
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