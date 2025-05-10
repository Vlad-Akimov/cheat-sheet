import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from config import config
from db import db
from text import texts
from kb import admin_back_kb, admin_edit_name_back_kb, admin_edit_name_kb, admin_review_kb, cancel_kb, main_menu
from states import EditCheatsheetStates

async def approve_cheatsheet(callback: CallbackQuery):
    try:
        _, cheatsheet_id = callback.data.split(":")
        cheatsheet_id = int(cheatsheet_id)
        
        db.approve_cheatsheet(cheatsheet_id)
        
        db.cursor.execute("SELECT datetime(approved_at, 'localtime') FROM cheatsheets WHERE id = ?", (cheatsheet_id,))
        approved_at = db.cursor.fetchone()[0]
        
        await callback.message.edit_text(
            f"{texts.CHEATSHEET_APPROVED}\n\nДата публикации: {approved_at} (МСК)",
            reply_markup=None
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error approving cheatsheet: {e}")
        await callback.answer("Ошибка при одобрении шпаргалки", show_alert=True)

async def reject_cheatsheet(callback: CallbackQuery):
    try:
        _, cheatsheet_id = callback.data.split(":")
        cheatsheet_id = int(cheatsheet_id)
        
        db.reject_cheatsheet(cheatsheet_id)
        
        db.cursor.execute("SELECT datetime('now', 'localtime')")
        rejected_at = db.cursor.fetchone()[0]
        
        await callback.message.edit_text(
            f"{texts.CHEATSHEET_REJECTED}\n\nДата отклонения: {rejected_at} (МСК)",
            reply_markup=None
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Error rejecting cheatsheet: {e}")
        await callback.answer("Ошибка при отклонении шпаргалки", show_alert=True)

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


async def start_edit_cheatsheet_name(callback: CallbackQuery, state: FSMContext):
    try:
        _, cheatsheet_id = callback.data.split(":")
        cheatsheet_id = int(cheatsheet_id)
        
        await state.update_data(
            cheatsheet_id=cheatsheet_id,
            original_message_id=callback.message.message_id,
            chat_id=callback.message.chat.id
        )
        
        await callback.message.edit_text(
            "Введите новое название шпаргалки (макс. 100 символов):",
            reply_markup=admin_back_kb(cheatsheet_id)
        )
        await callback.answer()
        await state.set_state(EditCheatsheetStates.waiting_for_new_name)
    except Exception as e:
        logging.error(f"Error starting name edit: {e}")
        await callback.answer("Ошибка при изменении названия", show_alert=True)

async def back_to_edit_menu(callback: CallbackQuery, state: FSMContext):
    try:
        _, cheatsheet_id = callback.data.split(":")
        cheatsheet_id = int(cheatsheet_id)
        
        data = await state.get_data()
        cheatsheet = db.get_cheatsheet(cheatsheet_id, callback.from_user.id)
        
        await callback.message.edit_text(
            format_cheatsheet_for_admin(cheatsheet),
            reply_markup=admin_review_kb(cheatsheet_id)
        )
        await callback.answer()
        await state.clear()
    except Exception as e:
        logging.error(f"Error returning to edit menu: {e}")
        await callback.answer("Ошибка при возврате", show_alert=True)

async def process_new_name(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        cheatsheet_id = data.get("cheatsheet_id")
        
        if len(message.text) > 100:
            await message.answer("Название слишком длинное (максимум 100 символов)")
            return
        
        # Обновляем название в БД
        db.cursor.execute(
            "UPDATE cheatsheets SET name = ? WHERE id = ?",
            (message.text, cheatsheet_id)
        )
        db.conn.commit()
        
        # Получаем обновленные данные
        cheatsheet = db.get_cheatsheet(cheatsheet_id, message.from_user.id)
        
        # Редактируем оригинальное сообщение
        await message.bot.edit_message_text(
            chat_id=data['chat_id'],
            message_id=data['original_message_id'],
            text=format_cheatsheet_for_admin(cheatsheet),
            reply_markup=admin_review_kb(cheatsheet_id)
        )
        
        await message.answer("✅ Название успешно изменено!", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Error processing new name: {e}")
        await message.answer("Ошибка при изменении названия")
    finally:
        await state.clear()

def format_cheatsheet_for_admin(cheatsheet: dict) -> str:
    """Форматирует информацию о шпаргалке для админа"""
    return (
        f"📝 Редактирование шпаргалки:\n\n"
        f"🏷 Текущее название: {cheatsheet['name']}\n"
        f"📚 Предмет: {cheatsheet['subject']}\n"
        f"🔢 Семестр: {cheatsheet['semester']}\n"
        f"📝 Тип: {cheatsheet['type']}\n"
        f"💰 Цена: {cheatsheet['price']} руб.\n"
        f"👤 Автор: {cheatsheet['author']}"
    )


def register_admin_handlers(router: Router):
    router.callback_query.register(approve_cheatsheet, F.data.startswith("approve:"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("reject:"))
    router.callback_query.register(start_edit_cheatsheet_name, F.data.startswith("edit_name:"))
    router.callback_query.register(back_to_edit_menu, F.data.startswith("back_edit:"))
    router.message.register(process_new_name, EditCheatsheetStates.waiting_for_new_name)
    router.callback_query.register(back_to_edit_menu, F.data.startswith("back_to_edit_"))
    router.message.register(process_new_name, EditCheatsheetStates.waiting_for_new_name)