from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Filter
from aiogram import types

class SearchCheatsheetStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_semester = State()
    waiting_for_type = State()

class AddCheatsheetStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_semester = State()
    waiting_for_type = State()
    waiting_for_name = State()
    waiting_for_file = State()
    waiting_for_price = State()

class AddBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class BalanceRequestStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_proof = State()

class MyCheatsheetsStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_semester = State()
    waiting_for_type = State()

class EditCheatsheetStates(StatesGroup):
    waiting_for_new_name = State()

class WithdrawStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_details = State()

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()

class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == message.bot.get('config').ADMIN_ID