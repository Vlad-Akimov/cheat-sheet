from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from config import config
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

async def view_all_cheatsheets(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    cheatsheets = db.cursor.execute("""
    SELECT c.id, s.name, c.semester, c.type, c.name, c.is_approved 
    FROM cheatsheets c
    JOIN subjects s ON c.subject_id = s.id
    """).fetchall()
    
    text = "Все шпаргалки:\n\n"
    for cs in cheatsheets:
        status = "✅ Одобрена" if cs[5] else "⏳ На модерации"
        text += f"ID: {cs[0]} | {cs[4]} ({cs[1]}, {cs[2]} семестр, {cs[3]}) - {status}\n"
    
    await message.answer(text)

def register_admin_handlers(router: Router):
    router.callback_query.register(approve_cheatsheet, F.data.startswith("approve_"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("reject_"))
    router.message.register(view_all_cheatsheets, Command("all_cheatsheets"))