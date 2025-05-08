from aiogram.types import TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from db import db

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Проверяем, что это сообщение или callback (везде, где есть from_user)
        if hasattr(event, 'from_user'):
            user = event.from_user
            # Добавляем пользователя с полной информацией
            db.add_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
        
        # Продолжаем обработку
        return await handler(event, data)

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db):
        super().__init__()
        self.db = db
    
    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["db"] = self.db
        return await handler(event, data)