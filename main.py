import logging
from aiogram import Router
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from middlewares import UserMiddleware, DatabaseMiddleware
from handlers import register_handlers
from admin import register_admin_handlers
from db import db
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

router = Router()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Добавление конфига в бот для доступа из других модулей
dp["config"] = config

# Регистрация мидлварей
dp.update.outer_middleware(UserMiddleware())
dp.update.outer_middleware(DatabaseMiddleware(db))

# Регистрация хэндлеров
register_handlers(dp)
register_admin_handlers(dp)

# Запуск бота
if __name__ == "__main__":
    try:
        # Добавляем тестовые предметы
        db.add_subject("Математика")
        db.add_subject("Физика")
        db.add_subject("Программирование")
        db.add_subject("Английский язык")

        dp.run_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        db.close()
