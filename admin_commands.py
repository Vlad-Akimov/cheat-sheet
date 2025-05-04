import logging
from aiogram import Bot, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, InputFile, InlineKeyboardButton

from config import config
from text import texts
from kb import *
from db import db
from utils import is_valid_file_type, get_file_type, delete_previous_messages, reply_with_menu
from states import SearchCheatsheetStates, AddCheatsheetStates, AddBalanceStates, BalanceRequestStates

# Создаем роутер
router = Router()

async def notify_admin_about_request(bot: Bot, request_id: int, user: types.User, amount: float, 
                                   file_id: str = None, file_type: str = None, proof_text: str = None):
    text = (
        f"🆕 Запрос на пополнение #{request_id}\n"
        f"👤 Пользователь: @{user.username} (ID: {user.id})\n"
        f"💰 Сумма: {amount} руб.\n"
    )
    
    if proof_text:
        text += f"📝 Комментарий: {proof_text}\n"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"balance_approve_{request_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"balance_reject_{request_id}")]
    ])
    
    try:
        if file_id:
            if file_type == "photo":
                await bot.send_photo(
                    chat_id=config.ADMIN_ID,
                    photo=file_id,
                    caption=text,
                    reply_markup=markup
                )
            else:
                await bot.send_document(
                    chat_id=config.ADMIN_ID,
                    document=file_id,
                    caption=text,
                    reply_markup=markup
                )
        else:
            await bot.send_message(
                chat_id=config.ADMIN_ID,
                text=text,
                reply_markup=markup
            )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

# Админ: начало процесса пополнения баланса
async def admin_add_balance(message: types.Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    await message.answer(
        "Введите ID пользователя для пополнения баланса:",
        reply_markup=admin_balance_kb()
    )
    await state.set_state(AddBalanceStates.waiting_for_user_id)


# Получение ID пользователя
async def process_user_id(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Действие отменено", reply_markup=main_menu())
        await state.clear()
        return
    
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.answer(
            "Теперь введите сумму для пополнения:",
            reply_markup=admin_balance_kb()
        )
        await state.set_state(AddBalanceStates.waiting_for_amount)
    except ValueError:
        await message.answer("Неверный формат ID. Введите число:")


# Админ обрабатывает запрос
async def handle_balance_request(callback: types.CallbackQuery):
    try:
        # Разбираем callback data
        parts = callback.data.split('_')
        if len(parts) != 3:
            await callback.answer("Неверный формат запроса", show_alert=True)
            return

        action, request_id = parts[1], parts[2]
        
        try:
            request_id = int(request_id)
        except ValueError:
            await callback.answer("Неверный ID запроса", show_alert=True)
            return

        # Получаем полные данные запроса
        db.cursor.execute("""
        SELECT user_id, amount, file_id, file_type, proof_text 
        FROM balance_requests 
        WHERE id = ? AND status = 'pending'
        """, (request_id,))
        request = db.cursor.fetchone()

        if not request:
            await callback.answer("Запрос не найден или уже обработан", show_alert=True)
            return

        user_id, amount, file_id, file_type, proof_text = request

        # Обновляем статус запроса
        success = db.update_request_status(
            request_id=request_id,
            status="approved" if action == "approve" else "rejected",
            admin_id=callback.from_user.id
        )

        if not success:
            await callback.answer("Ошибка обновления статуса", show_alert=True)
            return

        # Если одобрено - пополняем баланс
        if action == "approve":
            if not db.update_user_balance(user_id, amount):
                await callback.answer("Ошибка пополнения баланса", show_alert=True)
                return

        # Формируем сообщение для пользователя
        if action == "approve":
            new_balance = db.get_user_balance(user_id)
            user_message = (
                f"✅ Ваш запрос на пополнение {amount} руб. одобрен.\n"
                f"Текущий баланс: {new_balance} руб."
            )
        else:
            user_message = f"❌ Ваш запрос на пополнение {amount} руб. отклонен."

        # Отправляем уведомление пользователю
        try:
            await callback.bot.send_message(user_id, user_message)
        except Exception as e:
            print(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение админа
        try:
            if file_id:  # Если был файл
                if file_type == "photo":
                    await callback.message.edit_caption(
                        caption=f"Запрос #{request_id} {'одобрен' if action == 'approve' else 'отклонен'}",
                        reply_markup=None
                    )
                else:  # document
                    await callback.message.edit_caption(
                        caption=f"Запрос #{request_id} {'одобрен' if action == 'approve' else 'отклонен'}",
                        reply_markup=None
                    )
            else:  # Если был только текст
                await callback.message.edit_text(
                    f"Запрос #{request_id} {'одобрен' if action == 'approve' else 'отклонен'}",
                    reply_markup=None
                )
        except Exception as e:
            print(f"Ошибка редактирования сообщения: {e}")
            await callback.answer(f"Запрос обработан, но не удалось обновить сообщение: {e}")

        await callback.answer()

    except Exception as e:
        print(f"Ошибка обработки запроса баланса: {e}")
        await callback.answer("Произошла ошибка при обработке", show_alert=True)


# Получение суммы и пополнение баланса
async def process_amount(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("Действие отменено", reply_markup=main_menu())
        await state.clear()
        return
    
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("Сумма должна быть больше 0")
            return
            
        data = await state.get_data()
        user_id = data["user_id"]
        
        # Пополняем баланс
        db.update_user_balance(user_id, amount)
        
        # Получаем текущий баланс
        new_balance = db.get_user_balance(user_id)
        
        await message.answer(
            f"✅ Баланс пользователя {user_id} пополнен на {amount} руб.\n"
            f"Новый баланс: {new_balance} руб.",
            reply_markup=main_menu()
        )
        
        # Уведомляем пользователя
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"💰 Ваш баланс пополнен на {amount} руб.\n"
                     f"Текущий баланс: {new_balance} руб."
            )
        except Exception as e:
            await message.answer(f"Не удалось уведомить пользователя: {e}")
        
        await state.clear()
        
    except ValueError:
        await message.answer("Неверный формат суммы. Введите число:")