from aiogram import types
from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from db import db

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Проверяем, что это сообщение (не callback и т.д.)
        if isinstance(event, types.Message):
            user = event.from_user
            db.add_user(user.id, user.username)
        
        # Продолжаем обработку
        return await handler(event, data)

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db):
        super().__init__()
        self.db = db
    
    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["db"] = self.db
        return await handler(event, data)