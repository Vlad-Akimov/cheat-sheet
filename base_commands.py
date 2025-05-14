import logging
from aiogram import Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from datetime import datetime

from config import config
from text import texts
from kb import *
from db import db
from admin_commands import notify_admin_about_request
from utils import is_valid_file_type, get_file_type, delete_previous_messages, reply_with_menu
from states import FeedbackStates, MyCheatsheetsStates, SearchCheatsheetStates, AddCheatsheetStates, BalanceRequestStates, WithdrawStates

# Создаем роутер
router = Router()

# Команды ----------------------------------------------------

async def cmd_start(message: types.Message):
    try:
        await delete_previous_messages(message, 1000)
        await reply_with_menu(message, texts.START, delete_prev=False)
    except Exception as e:
        logging.error(f"Ошибка в cmd_start: {e}")
        await message.answer("Произошла ошибка. Подождите немного, мы уже решаем эту проблему.")

async def cmd_help(message: types.Message):
    await reply_with_menu(message, texts.HELP)

# Меню  ------------------------------------------------------

async def search_cheatsheets(message: types.Message, state: FSMContext):
    await delete_previous_messages(message)
    subjects = db.get_subjects()
    if not subjects:
        await message.answer("Пока нет доступных предметов.")
        return
    await message.answer(texts.SELECT_SUBJECT, reply_markup=subjects_kb(subjects))
    await state.set_state(SearchCheatsheetStates.waiting_for_subject)

async def add_cheatsheet(message: types.Message, state: FSMContext):
    await delete_previous_messages(message)
    subjects = db.get_subjects()
    if not subjects:
        await message.answer("Пока нет доступных предметов.")
        return
    await message.answer(texts.SELECT_SUBJECT, reply_markup=subjects_kb(subjects))
    await state.set_state(AddCheatsheetStates.waiting_for_subject)

async def show_user_cheatsheets_menu(message: types.Message, state: FSMContext):
    """Показывает меню фильтрации для моих шпаргалок"""
    await delete_previous_messages(message)
    subjects = db.get_subjects()
    if not subjects:
        await message.answer("Пока нет доступных предметов.")
        return
    
    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=subject, callback_data=f"my_subject_{subject}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(
        text=texts.CANCEL_SEARCH,
        callback_data="back_to_menu"
    ))
    
    await message.answer(texts.FILTER_BY_SUBJECT, reply_markup=builder.as_markup())
    await state.set_state(MyCheatsheetsStates.waiting_for_subject)

async def process_my_subject(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.split("_")[2]  # my_subject_Математика → Математика
    await state.update_data(subject=subject)
    await callback.message.edit_text("Выберите семестр:", reply_markup=semesters_kb_for_my_cheatsheets())
    await state.set_state(MyCheatsheetsStates.waiting_for_semester)

async def process_my_semester(callback: types.CallbackQuery, state: FSMContext):
    semester = int(callback.data.split("_")[2])  # my_semester_1 → 1
    await state.update_data(semester=semester)
    await callback.message.edit_text("Выберите тип:", reply_markup=types_kb_for_my_cheatsheets())
    await state.set_state(MyCheatsheetsStates.waiting_for_type)

async def process_my_type(callback: types.CallbackQuery, state: FSMContext):
    type_ = callback.data.split("_")[2]  # my_type_formulas → formulas
    await state.update_data(type=type_)
    data = await state.get_data()
    
    cheatsheets = db.get_user_cheatsheets(
        callback.from_user.id,
        subject=data.get('subject'),
        semester=data.get('semester'),
        type_=type_
    )
    
    if not cheatsheets:
        await reply_with_menu(callback, texts.NO_CHEATSHEETS, delete_current=True)
        await state.clear()
        return
    
    for cs in cheatsheets:
        status = "🛒 Куплена" if cs.get("is_purchased", False) else ("✅ Одобрена" if cs["is_approved"] else "⏳ На модерации")
        text = (
            f"📌 {cs['name']}\n"
            f"📚 {cs['subject']}, {cs['semester']} семестр\n"
            f"📝 {'Формула' if cs['type'] == 'formulas' else 'Теория'}\n"
            f"💰 {cs['price']} руб. | {status}"
        )
        await callback.message.answer(text, reply_markup=my_cheatsheet_kb(cs))
    
    await callback.answer()
    await state.clear()

async def my_back_to_subject(callback: types.CallbackQuery, state: FSMContext):
    """Назад к выбору предмета в 'Мои шпаргалки'"""
    await state.set_state(MyCheatsheetsStates.waiting_for_subject)
    subjects = db.get_subjects()
    
    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=subject, callback_data=f"my_subject_{subject}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(
        text=texts.CANCEL_SEARCH,
        callback_data="back_to_menu"
    ))
    
    await callback.message.edit_text(
        texts.FILTER_BY_SUBJECT,
        reply_markup=builder.as_markup()
    )
    await callback.answer()

async def my_back_to_semester(callback: types.CallbackQuery, state: FSMContext):
    """Назад к выбору семестра в 'Мои шпаргалки'"""
    await state.set_state(MyCheatsheetsStates.waiting_for_semester)
    await callback.message.edit_text(
        "Выберите семестр:",
        reply_markup=semesters_kb_for_my_cheatsheets()
    )
    await callback.answer()

async def open_my_cheatsheet(callback: types.CallbackQuery):
    try:
        cheatsheet_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Получаем шпаргалку с проверкой прав доступа
        cheatsheet = db.get_cheatsheet(cheatsheet_id, user_id)
        
        if not cheatsheet:
            await callback.answer("Шпаргалка не найдена или у вас нет доступа", show_alert=True)
            return
        
        # Отправляем содержимое шпаргалки
        if cheatsheet["file_type"] == "photo":
            await callback.message.answer_photo(
                cheatsheet["file_id"],
                caption=f"📄 {cheatsheet['name']}"
            )
        elif cheatsheet["file_type"] == "document":
            await callback.message.answer_document(
                cheatsheet["file_id"],
                caption=f"📄 {cheatsheet['name']}"
            )
        else:
            await callback.message.answer(
                f"📄 {cheatsheet['name']}\n\n{cheatsheet['file_id']}"
            )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error opening cheatsheet: {e}")
        await callback.answer("Произошла ошибка при открытии шпаргалки", show_alert=True)

async def show_balance(message: types.Message):
    balance = db.get_user_balance(message.from_user.id)
    await message.answer(
        f"💰 Ваш баланс: {balance} руб.",
        reply_markup=withdraw_kb()  # Показываем кнопку вывода после просмотра баланса
    )

async def request_feedback(message: types.Message, state: FSMContext):
    """Запрашивает отзыв у пользователя"""
    await message.answer(
        texts.FEEDBACK_PROMPT,
        reply_markup=cancel_kb()
    )
    await state.set_state(FeedbackStates.waiting_for_feedback)

async def process_feedback(message: types.Message, state: FSMContext):
    """Обрабатывает полученный отзыв"""
    if len(message.text) > 1000:
        await message.answer(texts.FEEDBACK_TOO_LONG)
        return
    
    # Сохраняем отзыв
    feedback_id = db.add_feedback(message.from_user.id, message.text)
    
    if feedback_id:
        # Уведомляем админа
        await notify_admin_about_feedback(
            message.bot,
            feedback_id,
            message.from_user,
            message.text
        )
        await message.answer(texts.FEEDBACK_SENT, reply_markup=main_menu())
    else:
        await message.answer(texts.ERROR, reply_markup=main_menu())
    
    await delete_previous_messages(message, 3)
    await state.clear()

async def notify_admin_about_feedback(bot: Bot, feedback_id: int, user: types.User, message: str):
    """Уведомляет админа о новом отзыве"""
    text = texts.FEEDBACK_NOTIFICATION.format(
        id=feedback_id,
        username=user.username,
        user_id=user.id,
        message=message,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    markup = feedback_review_kb(feedback_id)
    
    try:
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

async def handle_feedback_request(callback: types.CallbackQuery):
    """Обрабатывает действия админа с отзывами"""
    try:
        parts = callback.data.split("_")
        if len(parts) != 3:
            await callback.answer("Неверный формат запроса")
            return
            
        action = parts[1]
        try:
            feedback_id = int(parts[2])
        except ValueError:
            await callback.answer("Неверный ID отзыва")
            return
            
        admin_id = callback.from_user.id
        
        # Обновляем статус отзыва
        success = db.update_feedback_status(
            feedback_id=feedback_id,
            status="approved" if action == "approve" else "rejected",
            admin_id=admin_id
        )
        
        if not success:
            await callback.answer("Не удалось обновить отзыв")
            return
            
        # Получаем данные отзыва
        db.cursor.execute(
            "SELECT user_id, message FROM feedback WHERE id = ?", 
            (feedback_id,)
        )
        feedback = db.cursor.fetchone()
        
        if feedback:
            user_id, message = feedback
            
            # Уведомляем пользователя
            user_message = texts.FEEDBACK_APPROVED if action == "approve" else texts.FEEDBACK_REJECTED
            try:
                await callback.bot.send_message(user_id, user_message)
            except Exception as e:
                print(f"Ошибка уведомления пользователя: {e}")
                await callback.answer("Не удалось уведомить пользователя")
        
        await callback.message.edit_text(
            f"Отзыв #{feedback_id} {'одобрен' if action == 'approve' else 'отклонен'}",
            reply_markup=None
        )
        await callback.answer()
        
    except Exception as e:
        print(f"Ошибка обработки отзыва: {e}")
        await callback.answer("Произошла ошибка")

# Поиск шпаргалок ---------------------------------------------

async def process_subject(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.split("_")[1]
    await state.update_data(subject=subject)
    await callback.message.edit_text(texts.SELECT_SEMESTER, reply_markup=semesters_kb())
    await state.set_state(SearchCheatsheetStates.waiting_for_semester)

async def process_semester(callback: types.CallbackQuery, state: FSMContext):
    semester = int(callback.data.split("_")[1])
    await state.update_data(semester=semester)
    await callback.message.edit_text(texts.SELECT_TYPE, reply_markup=types_kb())
    await state.set_state(SearchCheatsheetStates.waiting_for_type)

async def process_type(callback: types.CallbackQuery, state: FSMContext):
    type_ = callback.data.split("_")[1]
    data = await state.get_data()
    
    cheatsheets = db.get_cheatsheets(
        subject=data.get("subject"),
        semester=data.get("semester"),
        type_=type_,
        user_id=callback.from_user.id
    )
    
    if not cheatsheets:
        builder = InlineKeyboardBuilder()
        builder.button(text=texts.BACK_BUTTON, callback_data="back_to_semester")
        builder.button(text=texts.CANCEL_SEARCH, callback_data="back_to_menu")
        builder.adjust(2)
        
        await callback.message.edit_text(
            texts.NO_CHEATSHEETS,
            reply_markup=builder.as_markup()
        )
        return
    
    for cheatsheet in cheatsheets:
        # Форматируем дату публикации
        pub_date = cheatsheet.get("approved_at", cheatsheet.get("created_at", "неизвестно"))
        
        text = texts.CHEATSHEET_INFO.format(
            name=cheatsheet["name"],
            subject=cheatsheet["subject"],
            semester=cheatsheet["semester"],
            type='Формула' if cheatsheet['type'] == 'formulas' else 'Теория',
            author=cheatsheet["author"],
            price=cheatsheet["price"],
            approved_at=pub_date
        )
        
        # Остальной код остается без изменений
        if cheatsheet["author_id"] == callback.from_user.id:
            markup = free_kb(cheatsheet["file_id"])
        else:
            db.cursor.execute("SELECT 1 FROM purchases WHERE user_id = ? AND cheatsheet_id = ?", 
                            (callback.from_user.id, cheatsheet["id"]))
            if db.cursor.fetchone():
                markup = free_kb(cheatsheet["file_id"])
            else:
                if cheatsheet["price"] > 0:
                    markup = buy_kb(cheatsheet["id"], cheatsheet["price"])
                else:
                    markup = free_kb(cheatsheet["file_id"])
        
        await callback.message.answer(text, reply_markup=markup)
    
    await state.clear()

# Добавление шпаргалок ----------------------------------------

async def process_add_subject(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data.split("_")[1]
    await state.update_data(subject=subject)
    await callback.message.edit_text(texts.SELECT_SEMESTER, reply_markup=semesters_kb())
    await state.set_state(AddCheatsheetStates.waiting_for_semester)

async def process_add_semester(callback: types.CallbackQuery, state: FSMContext):
    semester = int(callback.data.split("_")[1])
    await state.update_data(semester=semester)
    await callback.message.edit_text(texts.SELECT_TYPE, reply_markup=types_kb())
    await state.set_state(AddCheatsheetStates.waiting_for_type)

async def process_add_type(callback: types.CallbackQuery, state: FSMContext):
    type_ = callback.data.split("_")[1]
    await state.update_data(type=type_)
    await callback.message.edit_text("Введите название шпаргалки:", reply_markup=cancel_kb())
    await state.set_state(AddCheatsheetStates.waiting_for_name)

async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("Название слишком длинное (максимум 100 символов)")
        return
    
    await state.update_data(name=message.text)
    await message.answer(texts.SEND_FILE, reply_markup=cancel_kb())
    await state.set_state(AddCheatsheetStates.waiting_for_file)

async def process_file(message: types.Message, state: FSMContext):
    if not is_valid_file_type(message):
        await message.answer(texts.INVALID_FILE)
        return
    
    file_type = get_file_type(message)
    file_id = None
    
    if file_type == "photo":
        file_id = message.photo[-1].file_id
    elif file_type == "document":
        file_id = message.document.file_id
    elif file_type == "text":
        file_id = message.text
    
    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer(texts.SET_PRICE, reply_markup=cancel_kb())
    await state.set_state(AddCheatsheetStates.waiting_for_price)

async def process_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer(texts.INVALID_PRICE)
        return
    
    try:
        # Увеличиваем цену на фиксированный процент ADMIN_PERCENT
        final_price = round(price * (1 + config.ADMIN_PERCENT), 2)
        
        data = await state.get_data()
        
        # Проверяем наличие всех необходимых полей
        required_fields = ['subject', 'semester', 'type', 'name', 'file_id', 'file_type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            await message.answer(f"Ошибка: отсутствуют данные ({', '.join(missing_fields)}). Начните заново.")
            await state.clear()
            return
        
        subject_id = db.cursor.execute("SELECT id FROM subjects WHERE name = ?", (data["subject"],)).fetchone()
        if not subject_id:
            db.add_subject(data["subject"])
            subject_id = db.cursor.execute("SELECT id FROM subjects WHERE name = ?", (data["subject"],)).fetchone()[0]
        else:
            subject_id = subject_id[0]
        
        cheatsheet_id = db.add_cheatsheet(
            subject_id=subject_id,
            semester=data["semester"],
            type_=data["type"],
            name=data["name"],
            file_id=data["file_id"],
            file_type=data["file_type"],
            price=final_price,
            author_id=message.from_user.id
        )
        
        user = message.from_user
        admin_text = texts.NEW_CHEATSHEET_FOR_REVIEW.format(
            name=data["name"],
            subject=data["subject"],
            semester=data["semester"],
            type='Формула' if data["type"] == 'formulas' else 'Теория',
            price=f"{final_price} (исходная цена: {price} ₽, наценка: {config.ADMIN_PERCENT}%)",
            author=f"{user.username} (ID: {user.id})"
        )
        
        try:
            if data["file_type"] == "photo":
                await message.bot.send_photo(
                    chat_id=config.ADMIN_ID,
                    photo=data["file_id"],
                    caption=admin_text,
                    reply_markup=admin_review_kb(cheatsheet_id)
                )
            elif data["file_type"] == "document":
                await message.bot.send_document(
                    chat_id=config.ADMIN_ID,
                    document=data["file_id"],
                    caption=admin_text,
                    reply_markup=admin_review_kb(cheatsheet_id)
                )
            else:
                await message.bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=f"{admin_text}\n\nТекст шпаргалки:\n\n{data['file_id']}",
                    reply_markup=admin_review_kb(cheatsheet_id)
                )
            
            await message.answer(texts.CHEATSHEET_SENT_FOR_REVIEW, reply_markup=main_menu())
        except Exception as e:
            await message.answer("Произошла ошибка при отправке шпаргалки администратору. Пожалуйста, попробуйте позже.")
            logging.error(f"Error sending cheatsheet to admin: {e}")
        
    except Exception as e:
        await message.answer("Произошла непредвиденная ошибка. Пожалуйста, попробуйте снова.")
        logging.error(f"Error in process_price: {e}")
    
    await state.clear()
    
# Отмена -----------------------------------------------------

async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await reply_with_menu(callback, "Действие отменено.")
    await state.clear()

# Покупка ----------------------------------------------------

async def buy_cheatsheet(callback: types.CallbackQuery):
    try:
        # Разбираем callback data
        if not callback.data:
            await callback.answer("Неверный запрос")
            return

        data_parts = callback.data.split("_")
        if len(data_parts) != 2:
            await callback.answer("Неверный формат запроса")
            return

        action, identifier = data_parts

        # Обработка бесплатных шпаргалок
        if action == "free":
            await callback.message.answer(
                f"📄 Ваша шпаргалка:\n\n{identifier}",
                reply_markup=main_menu()
            )
            await callback.answer()
            return

        # Обработка платных шпаргалок
        try:
            cheatsheet_id = int(identifier)
        except ValueError:
            await callback.answer("Неверный ID шпаргалки")
            return

        user_id = callback.from_user.id
        cheatsheet = db.get_cheatsheet(cheatsheet_id, user_id)

        if not cheatsheet:
            await callback.answer("Шпаргалка не найдена", show_alert=True)
            return

        # Проверяем наличие всех необходимых полей
        required_fields = ['price', 'author_id', 'file_id', 'file_type']
        if not all(field in cheatsheet for field in required_fields):
            await callback.answer("Ошибка данных шпаргалки", show_alert=True)
            return

        # Если шпаргалка принадлежит пользователю - сразу выдаем
        if cheatsheet["author_id"] == user_id:
            if cheatsheet["file_type"] == "photo":
                await callback.message.answer_photo(
                    cheatsheet["file_id"],
                    caption="✅ Ваша шпаргалка:",
                    reply_markup=main_menu()
                )
            elif cheatsheet["file_type"] == "document":
                await callback.message.answer_document(
                    cheatsheet["file_id"],
                    caption="✅ Ваша шпаргалка:",
                    reply_markup=main_menu()
                )
            else:
                await callback.message.answer(
                    f"✅ Ваша шпаргалка:\n\n{cheatsheet['file_id']}",
                    reply_markup=main_menu()
                )
            await callback.message.delete()
            await callback.answer()
            return

        # Проверяем, не куплена ли уже шпаргалка
        db.cursor.execute("SELECT 1 FROM purchases WHERE user_id = ? AND cheatsheet_id = ?", 
                         (user_id, cheatsheet_id))
        if db.cursor.fetchone():
            if cheatsheet["file_type"] == "photo":
                await callback.message.answer_photo(
                    cheatsheet["file_id"],
                    caption="✅ Ваша шпаргалка:",
                    reply_markup=main_menu()
                )
            elif cheatsheet["file_type"] == "document":
                await callback.message.answer_document(
                    cheatsheet["file_id"],
                    caption="✅ Ваша шпаргалка:",
                    reply_markup=main_menu()
                )
            else:
                await callback.message.answer(
                    f"✅ Ваша шпаргалка:\n\n{cheatsheet['file_id']}",
                    reply_markup=main_menu()
                )
            await callback.message.delete()
            await callback.answer()
            return

        # Проверка баланса
        user_balance = db.get_user_balance(user_id)
        if user_balance < cheatsheet["price"]:
            await callback.answer(texts.NOT_ENOUGH_MONEY, show_alert=True)
            await reply_with_menu(callback, 
                                f"Недостаточно средств. Ваш баланс: {user_balance} руб.\n"
                                f"Требуется: {cheatsheet['price']} руб.\n\n"
                                "Пополните баланс и попробуйте снова.")
            return

        # Начинаем транзакцию
        try:
            # Списание средств у покупателя
            if not db.update_user_balance(user_id, -cheatsheet["price"]):
                raise Exception("Не удалось списать средства")
            """
            # Начисление автору (если это не админ)
            if cheatsheet["author_id"] != config.ADMIN_ID:
                author_amount = round(cheatsheet["price"] * (1 - config.ADMIN_PERCENT), 2)
                if not db.update_user_balance(cheatsheet["author_id"], author_amount):
                    raise Exception("Не удалось начислить средства автору")
            
            # Начисление администратору
            admin_amount = round(cheatsheet["price"] * config.ADMIN_PERCENT, 2)
            if not db.update_user_balance(config.ADMIN_ID, admin_amount):
                raise Exception("Не удалось начислить средства администратору")
            """

            # Запись о покупке
            if not db.add_purchase(user_id, cheatsheet_id, cheatsheet["price"]):
                raise Exception("Не удалось записать покупку")

            # Отправка шпаргалки пользователю
            if cheatsheet["file_type"] == "photo":
                await callback.message.answer_photo(
                    cheatsheet["file_id"],
                    caption=f"✅ {texts.PURCHASE_SUCCESS}",
                    reply_markup=main_menu()
                )
            elif cheatsheet["file_type"] == "document":
                await callback.message.answer_document(
                    cheatsheet["file_id"],
                    caption=f"✅ {texts.PURCHASE_SUCCESS}",
                    reply_markup=main_menu()
                )
            else:  # Текстовые шпаргалки
                await callback.message.answer(
                    f"✅ {texts.PURCHASE_SUCCESS}\n\n{cheatsheet['file_id']}",
                    reply_markup=main_menu()
                )

            await callback.message.delete()
            await callback.answer()

        except Exception as e:
            # Откатываем изменения в случае ошибки
            db.conn.rollback()
            await callback.answer("Ошибка при обработке покупки", show_alert=True)
            print(f"Ошибка транзакции: {e}")
            return

    except Exception as e:
        await callback.answer("Произошла ошибка", show_alert=True)
        print(f"Неожиданная ошибка в buy_cheatsheet: {e}")


# Пользователь запрашивает пополнение
async def request_balance(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправьте сумму пополнения цифрами (например: 500):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(BalanceRequestStates.waiting_for_amount)

# Пользователь вводит сумму
async def process_balance_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("Сумма должна быть больше 0")
            return
            
        await state.update_data(amount=amount)
        await message.answer(
            "Теперь отправьте скриншот подтверждения платежа (фото или документ PDF/JPG/PNG),\n"
            "или текстовое описание платежа (номер транзакции и т.д.):",
            reply_markup=cancel_kb()
        )
        await state.set_state(BalanceRequestStates.waiting_for_proof)
    except ValueError:
        await message.answer("Пожалуйста, введите сумму цифрами (например: 500)")

# Пользователь отправляет подтверждение
async def process_balance_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Проверяем сумму
    if 'amount' not in data or data['amount'] <= 0:
        await message.answer("Ошибка: неверная сумма", reply_markup=main_menu())
        await state.clear()
        return

    # Сохраняем файл или текст
    file_id = None
    file_type = None
    proof_text = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    elif message.text:
        proof_text = message.text
    else:
        await message.answer("Неверный формат подтверждения", reply_markup=main_menu())
        await state.clear()
        return

    # Сохраняем запрос
    request_id = db.add_balance_request(
        user_id=message.from_user.id,
        amount=data['amount'],
        proof_text=proof_text,
        file_id=file_id,
        file_type=file_type
    )

    if not request_id:
        await message.answer("Ошибка при создании запроса", reply_markup=main_menu())
        await state.clear()
        return

    # Отправляем уведомление админу
    await notify_admin_about_request(message.bot, request_id, message.from_user, data['amount'], file_id, file_type, proof_text)
    
    await message.answer("✅ Ваш запрос отправлен на рассмотрение", reply_markup=main_menu())
    await state.clear()


async def process_balance_request(message: types.Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    try:
        user_id, amount = message.text.split()
        user_id = int(user_id)
        amount = float(amount)
        
        if amount <= 0:
            await message.answer("Сумма должна быть больше 0")
            return
            
        db.update_user_balance(user_id, amount)
        await message.answer(
            f"Баланс пользователя {user_id} пополнен на {amount} руб.",
            reply_markup=main_menu()
        )
        await state.clear()
        
        # Уведомляем пользователя
        await message.bot.send_message(
            chat_id=user_id,
            text=f"Ваш баланс пополнен на {amount} руб. Текущий баланс: {db.get_user_balance(user_id)} руб."
        )
    except ValueError:
        await message.answer("Неверный формат. Введите ID и сумму через пробел")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()

# Обработчик кнопки "Назад" в главное меню
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await reply_with_menu(callback, "Поиск отменён.", delete_current=True)

# Обработчик кнопки "Назад" к выбору предмета
async def back_to_subject(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchCheatsheetStates.waiting_for_subject)
    subjects = db.get_subjects()
    await callback.message.edit_text(
        texts.SELECT_SUBJECT,
        reply_markup=subjects_kb(subjects)
    )
    await callback.answer()

# Обработчик кнопки "Назад" к выбору семестра
async def back_to_semester(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору семестра"""
    await state.set_state(SearchCheatsheetStates.waiting_for_semester)
    await callback.message.edit_text(
        texts.SELECT_SEMESTER,
        reply_markup=semesters_kb()
    )
    await callback.answer()

async def start_withdraw(message: types.Message, state: FSMContext):
    balance = db.get_user_balance(message.from_user.id)
    if balance <= 0:
        await message.answer("На вашем балансе нет средств для вывода.", reply_markup=main_menu())
        return
    
    await message.answer(
        texts.ENTER_WITHDRAW_AMOUNT,
        reply_markup=cancel_kb()
    )
    await state.set_state(WithdrawStates.waiting_for_amount)

async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        balance = db.get_user_balance(message.from_user.id)
        
        if amount <= 0 or amount > balance:
            await message.answer(texts.INVALID_WITHDRAW_AMOUNT)
            return
            
        await state.update_data(amount=amount)
        await message.answer(
            texts.ENTER_WITHDRAW_DETAILS,
            reply_markup=cancel_kb()
        )
        await state.set_state(WithdrawStates.waiting_for_details)
    except ValueError:
        await message.answer(texts.INVALID_AMOUNT_FORMAT)

async def process_withdraw_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    details = message.text
    
    # Создаем запрос на вывод
    request_id = db.add_withdraw_request(
        user_id=message.from_user.id,
        amount=amount,
        details=details
    )
    
    if not request_id:
        await message.answer(texts.ERROR, reply_markup=main_menu())
        await state.clear()
        return
    
    # Уведомляем пользователя
    await message.answer(
        texts.WITHDRAW_REQUEST_SENT.format(
            amount=amount,
            admin_username=config.ADMIN_USERNAME
        ),
        reply_markup=main_menu()
    )
    
    # Уведомляем админа
    await notify_admin_about_withdraw(
        message.bot, 
        request_id,
        message.from_user,
        amount,
        details
    )
    
    await state.clear()

async def handle_back_button(message: types.Message, state: FSMContext):
    await state.clear()

async def notify_admin_about_withdraw(bot: Bot, request_id: int, user: types.User, amount: float, details: str):
    text = texts.WITHDRAW_REQUEST.format(
        id=request_id,
        username=user.username,
        user_id=user.id,
        amount=amount,
        details=details,
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"withdraw_approve_{request_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"withdraw_reject_{request_id}")]
    ])
    
    try:
        await bot.send_message(
            chat_id=config.ADMIN_ID,
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Ошибка уведомления админа: {e}")

async def handle_withdraw_request(callback: types.CallbackQuery):
    try:
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

        # Получаем данные запроса
        db.cursor.execute("""
        SELECT user_id, amount 
        FROM withdraw_requests 
        WHERE id = ? AND status = 'pending'
        """, (request_id,))
        request = db.cursor.fetchone()

        if not request:
            await callback.answer("Запрос не найден или уже обработан", show_alert=True)
            return

        user_id, amount = request

        # Обновляем статус
        success = db.update_withdraw_status(
            request_id=request_id,
            status="approved" if action == "approve" else "rejected",
            admin_id=callback.from_user.id
        )

        if not success:
            await callback.answer("Ошибка обновления статуса", show_alert=True)
            return

        # Если одобрено - списываем средства
        if action == "approve":
            if not db.update_user_balance(user_id, -amount):
                await callback.answer("Ошибка списания средств", show_alert=True)
                return

        # Формируем сообщение для пользователя
        if action == "approve":
            new_balance = db.get_user_balance(user_id)
            user_message = (
                f"✅ Ваш запрос на вывод {amount} руб. одобрен.\n"
                f"Средства будут переведены на указанные реквизиты в течение 24 часов.\n"
                f"Текущий баланс: {new_balance} руб."
            )
        else:
            user_message = f"❌ Ваш запрос на вывод {amount} руб. отклонен."

        # Отправляем уведомление пользователю
        try:
            await callback.bot.send_message(user_id, user_message)
        except Exception as e:
            print(f"Ошибка уведомления пользователя: {e}")

        # Обновляем сообщение админа
        try:
            await callback.message.edit_text(
                f"Запрос на вывод #{request_id} {'одобрен' if action == 'approve' else 'отклонен'}",
                reply_markup=None
            )
        except Exception as e:
            print(f"Ошибка редактирования сообщения: {e}")
            await callback.answer(f"Запрос обработан, но не удалось обновить сообщение: {e}")

        await callback.answer()

    except Exception as e:
        print(f"Ошибка обработки запроса на вывод: {e}")
        await callback.answer("Произошла ошибка при обработке", show_alert=True)