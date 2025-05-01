from aiogram import Router
from aiogram import F
from aiogram.types import CallbackQuery
from db import db
from text import texts
from kb import main_menu

async def approve_cheatsheet(callback: CallbackQuery):
    cheatsheet_id = int(callback.data.split("_")[1])
    db.approve_cheatsheet(cheatsheet_id)
    await callback.message.edit_text(texts.CHEATSHEET_APPROVED)
    await callback.answer()

async def reject_cheatsheet(callback: CallbackQuery):
    cheatsheet_id = int(callback.data.split("_")[1])
    db.reject_cheatsheet(cheatsheet_id)
    await callback.message.edit_text(texts.CHEATSHEET_REJECTED)
    await callback.answer()

def register_admin_handlers(router: Router):
    router.callback_query.register(approve_cheatsheet, F.data.startswith("approve_"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("reject_"))