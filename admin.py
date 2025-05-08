from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from config import config
from db import db
from text import texts

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


async def handle_balance_request(callback: types.CallbackQuery):
    try:
        # Разбираем callback data в формате "balance_[action]_[request_id]"
        parts = callback.data.split("_")
        if len(parts) != 3:
            await callback.answer("Неверный формат запроса")
            return
            
        action = parts[1]
        try:
            request_id = int(parts[2])
        except ValueError:
            await callback.answer("Неверный ID запроса")
            return
            
        admin_id = callback.from_user.id
        
        # Обновляем статус запроса
        success = db.update_request_status(
            request_id=request_id,
            status="approved" if action == "approve" else "rejected",
            admin_id=admin_id
        )
        
        if not success:
            await callback.answer("Не удалось обновить запрос")
            return
            
        # Получаем данные запроса
        db.cursor.execute(
            "SELECT user_id, amount FROM balance_requests WHERE id = ?", 
            (request_id,)
        )
        request = db.cursor.fetchone()
        
        if request:
            user_id, amount = request
            
            # Если одобрено - пополняем баланс
            if action == "approve":
                db.update_user_balance(user_id, amount)
                user_message = (
                    f"✅ Ваш запрос на пополнение {amount} руб. одобрен.\n"
                    f"Текущий баланс: {db.get_user_balance(user_id)} руб."
                )
            else:
                user_message = f"❌ Ваш запрос на пополнение {amount} руб. отклонен."
            
            # Уведомляем пользователя
            try:
                await callback.bot.send_message(user_id, user_message)
            except Exception as e:
                print(f"Ошибка уведомления пользователя: {e}")
                await callback.answer("Не удалось уведомить пользователя")
        
        await callback.message.edit_text(
            f"Запрос #{request_id} {'одобрен' if action == 'approve' else 'отклонен'}",
            reply_markup=None
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка обработки запроса баланса: {e}")
        await callback.answer("Произошла ошибка")
    

async def check_cheatsheets(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    # Проверяем все шпаргалки
    cheatsheets = db.cursor.execute("""
    SELECT 
        c.id, 
        s.name as subject, 
        c.semester, 
        c.type, 
        c.name, 
        c.is_approved,
        COUNT(*) as count
    FROM cheatsheets c
    JOIN subjects s ON c.subject_id = s.id
    GROUP BY s.name, c.semester, c.type
    """).fetchall()
    
    text = "Статистика шпаргалок:\n\n"
    for cs in cheatsheets:
        status = "✅ Одобрена" if cs[5] else "❌ На модерации"
        text += f"{cs[1]} | {cs[2]} семестр | {cs[3]} | {cs[4]} | {status}\n"
    
    text += f"\nВсего шпаргалок: {sum(cs[6] for cs in cheatsheets)}"
    await message.answer(text)


def register_admin_handlers(router: Router):
    router.callback_query.register(approve_cheatsheet, F.data.startswith("approve_"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("reject_"))
    router.message.register(view_all_cheatsheets, Command("all_cheatsheets"))
    router.message.register(check_cheatsheets, Command("check_cheatsheets"))