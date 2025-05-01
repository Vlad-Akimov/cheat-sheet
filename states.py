from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter
from aiogram import types

class CheatsheetStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_semester = State()
    waiting_for_type = State()
    waiting_for_file = State()
    waiting_for_price = State()

class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == message.bot.get('config').ADMIN_ID