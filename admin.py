import asyncio
import logging
from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from config import config
from db import db
from text import texts
from kb import *
from states import BroadcastStates, EditCheatsheetStates


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


async def view_withdraw_requests(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    requests = db.get_pending_withdraw_requests()
    
    if not requests:
        await message.answer("Нет ожидающих запросов на вывод средств.")
        return
    
    text = "Ожидающие запросы на вывод:\n\n"
    for req in requests:
        text += (
            f"ID: {req['id']}\n"
            f"Пользователь: @{req['username']} (ID: {req['user_id']})\n"
            f"Сумма: {req['amount']} руб.\n"
            f"Реквизиты: {req['details']}\n"
            f"Дата: {req['created_at']}\n\n"
        )
    
    await message.answer(text)


async def view_feedback(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    feedbacks = db.get_pending_feedback()
    
    if not feedbacks:
        await message.answer("Нет ожидающих отзывов.")
        return
    
    text = "Ожидающие отзывы:\n\n"
    for fb in feedbacks:
        text += (
            f"ID: {fb['id']}\n"
            f"Пользователь: @{fb['username']} (ID: {fb['user_id']})\n"
            f"Сообщение: {fb['message']}\n"
            f"Дата: {fb['created_at']}\n\n"
        )
    
    await message.answer(text)


async def start_edit_cheatsheet_price(callback: CallbackQuery, state: FSMContext):
    try:
        _, cheatsheet_id = callback.data.split(":")
        cheatsheet_id = int(cheatsheet_id)
        
        await state.update_data(
            cheatsheet_id=cheatsheet_id,
            original_message_id=callback.message.message_id,
            chat_id=callback.message.chat.id
        )
        
        await callback.message.edit_text(
            "Введите новую цену шпаргалки (в рублях):",
            reply_markup=admin_back_kb(cheatsheet_id)
        )
        await callback.answer()
        await state.set_state(EditCheatsheetStates.waiting_for_new_price)
    except Exception as e:
        logging.error(f"Error starting price edit: {e}")
        await callback.answer("Ошибка при изменении цены", show_alert=True)


async def process_new_price(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        cheatsheet_id = data.get("cheatsheet_id")
        
        try:
            price = float(message.text)
            if price < 0:
                raise ValueError
        except ValueError:
            await message.answer("Неверная цена. Введите положительное число.")
            return
        
        # Обновляем цену в БД
        db.cursor.execute(
            "UPDATE cheatsheets SET price = ? WHERE id = ?",
            (price, cheatsheet_id)
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
        
        await message.answer("✅ Цена успешно изменена!", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Error processing new price: {e}")
        await message.answer("Ошибка при изменении цены")
    finally:
        await state.clear()


def format_cheatsheet_for_admin(cheatsheet: dict) -> str:
    """Форматирует информацию о шпаргалке для админа"""
    return (
        f"📝 Редактирование шпаргалки:\n\n"
        f"🏷 Название: {cheatsheet['name']}\n"
        f"📚 Предмет: {cheatsheet['subject']}\n"
        f"🔢 Семестр: {cheatsheet['semester']}\n"
        f"📝 Тип: {cheatsheet['type']}\n"
        f"💰 Цена: {cheatsheet['price']} руб.\n"  # Добавляем отображение цены
        f"👤 Автор: {cheatsheet['author']}"
    )


async def start_broadcast(message: types.Message, state: FSMContext):
    """Начало создания рассылки"""
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    users = db.get_all_users()
    if not users:
        await message.answer(texts.BROADCAST_NO_USERS)
        return
    
    await state.update_data(users=users, users_count=len(users))
    await message.answer(texts.BROADCAST_START, reply_markup=cancel_kb())
    await state.set_state(BroadcastStates.waiting_for_content)


async def process_broadcast_content(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка контента для рассылки"""
    data = await state.get_data()
    
    # Сохраняем контент в зависимости от типа
    content = {
        'text': message.html_text if message.text else message.caption,
        'content_type': message.content_type,
    }
    
    if message.photo:
        content['file_id'] = message.photo[-1].file_id
    elif message.document:
        content['file_id'] = message.document.file_id
        content['file_name'] = message.document.file_name
    
    await state.update_data(content=content)
    
    # Формируем текст для подтверждения
    preview_text = content['text'] or "📷 Фото" if message.photo else "📄 Файл"
    await message.answer(
        texts.BROADCAST_CONFIRM.format(
            content=preview_text,
            users_count=data['users_count']
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")]
        ])
    )
    await state.set_state(BroadcastStates.waiting_for_confirmation)


async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка рассылки"""
    data = await state.get_data()
    users = data['users']
    content = data['content']
    
    await callback.message.edit_text("⏳ Начинаю рассылку...")
    
    success = 0
    failed = 0
    
    # Отправляем сообщения пачками
    for i in range(0, len(users), config.BROADCAST_CHUNK_SIZE):
        chunk = users[i:i + config.BROADCAST_CHUNK_SIZE]
        
        for user_id in chunk:
            try:
                if content['content_type'] == ContentType.TEXT:
                    await bot.send_message(
                        chat_id=user_id,
                        text=content['text'],
                        parse_mode="HTML"
                    )
                elif content['content_type'] == ContentType.PHOTO:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=content['file_id'],
                        caption=content.get('text'),
                        parse_mode="HTML"
                    )
                elif content['content_type'] == ContentType.DOCUMENT:
                    await bot.send_document(
                        chat_id=user_id,
                        document=content['file_id'],
                        caption=content.get('text'),
                        parse_mode="HTML"
                    )
                success += 1
            except Exception as e:
                logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
                failed += 1
            await asyncio.sleep(0.1)
    
    await callback.message.edit_text(
        texts.BROADCAST_SUCCESS.format(success=success, total=len(users))
    )
    await state.clear()


async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await callback.message.edit_text(texts.BROADCAST_CANCEL)
    await state.clear()


def register_admin_handlers(router: Router):
    router.callback_query.register(approve_cheatsheet, F.data.startswith("approve:"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("reject:"))
    router.callback_query.register(start_edit_cheatsheet_name, F.data.startswith("edit_name:"))
    router.callback_query.register(start_edit_cheatsheet_price, F.data.startswith("edit_price:"))
    router.callback_query.register(back_to_edit_menu, F.data.startswith("back_edit:"))
    router.message.register(process_new_name, EditCheatsheetStates.waiting_for_new_name)
    router.message.register(process_new_price, EditCheatsheetStates.waiting_for_new_price)
    router.callback_query.register(back_to_edit_menu, F.data.startswith("back_to_edit_"))
    router.message.register(view_withdraw_requests, Command("withdraws"))
    router.message.register(view_feedback, Command("feedback"))
    
    router.message.register(start_broadcast, Command("broadcast"))
    router.message.register(
        process_broadcast_content, 
        BroadcastStates.waiting_for_content,
        F.content_type.in_({ContentType.TEXT, ContentType.PHOTO, ContentType.DOCUMENT})
    )
    router.callback_query.register(confirm_broadcast, F.data == "broadcast_confirm", BroadcastStates.waiting_for_confirmation)
    router.callback_query.register(cancel_broadcast, F.data == "broadcast_cancel", BroadcastStates.waiting_for_confirmation)
