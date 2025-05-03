import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton

from config import config
from text import texts
from kb import *
from db import db
from utils import is_valid_file_type, get_file_type, delete_previous_messages, reply_with_menu
from states import SearchCheatsheetStates, AddCheatsheetStates, AddBalanceStates

# Создаем роутер
router = Router()

async def cmd_start(message: types.Message):
    await delete_previous_messages(message, 1000)
    await reply_with_menu(message, texts.START, delete_prev=False)

async def cmd_help(message: types.Message):
    await reply_with_menu(message, texts.HELP)

async def search_cheatsheets(message: types.Message, state: FSMContext):
    await delete_previous_messages(message)
    subjects = db.get_subjects()
    if not subjects:
        await message.answer("Пока нет доступных предметов.")
        return
    await message.answer(texts.SELECT_SUBJECT, reply_markup=subjects_kb(subjects))
    await state.set_state(SearchCheatsheetStates.waiting_for_subject)

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
        type_=type_
    )
    
    if not cheatsheets:
        await reply_with_menu(callback, texts.NO_CHEATSHEETS, delete_current=True)
        await state.clear()
        return
    
    for cheatsheet in cheatsheets:
        # Проверяем наличие всех необходимых полей
        if not all(key in cheatsheet for key in ['subject', 'semester', 'type', 'name', 'author', 'price', 'file_id', 'file_type']):
            print(f"Неполные данные шпаргалки: {cheatsheet}")
            continue
            
        text = texts.CHEATSHEET_INFO.format(
            name=cheatsheet["name"],
            subject=cheatsheet["subject"],
            semester=cheatsheet["semester"],
            type=cheatsheet["type"],
            author=cheatsheet["author"],
            price=cheatsheet["price"]
        )
        
        if cheatsheet["price"] > 0:
            markup = buy_kb(cheatsheet["id"], cheatsheet["price"])
        else:
            markup = free_kb(cheatsheet["file_id"])
        
        await callback.message.answer(text, reply_markup=markup)
    
    await state.clear()

async def add_cheatsheet(message: types.Message, state: FSMContext):
    await delete_previous_messages(message)
    subjects = db.get_subjects()
    if not subjects:
        await message.answer("Пока нет доступных предметов.")
        return
    await message.answer(texts.SELECT_SUBJECT, reply_markup=subjects_kb(subjects))
    await state.set_state(AddCheatsheetStates.waiting_for_subject)

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
        price=price,
        author_id=message.from_user.id
    )
    
    user = message.from_user
    admin_text = texts.NEW_CHEATSHEET_FOR_REVIEW.format(
        name=data["name"],
        subject=data["subject"],
        semester=data["semester"],
        type=data["type"],
        price=price,
        author=f"{user.username} (ID: {user.id})"
    )
    
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
    await state.clear()

async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await reply_with_menu(callback, "Действие отменено.")
    await state.clear()

async def show_user_cheatsheets(message: types.Message):
    cheatsheets = db.get_user_cheatsheets(message.from_user.id)
    if not cheatsheets:
        await reply_with_menu(message, "У вас пока нет шпаргалок.")
        return
    
    text = "📚 Ваши шпаргалки:\n\n"
    for cs in cheatsheets:
        status = "✅ Одобрена" if cs["is_approved"] else "⏳ На модерации"
        text += f"📌 {cs['name']}\n{cs['subject']}, {cs['semester']} семестр, {cs['type']} - {cs['price']} руб. ({status})\n\n"
    
    await reply_with_menu(message, text)

async def show_balance(message: types.Message):
    balance = db.get_user_balance(message.from_user.id)
    await reply_with_menu(message, f"💰 Ваш баланс: {balance} руб.")

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
        cheatsheet = db.get_cheatsheet(cheatsheet_id)

        if not cheatsheet:
            await callback.answer("Шпаргалка не найдена", show_alert=True)
            return

        # Проверяем наличие всех необходимых полей
        required_fields = ['price', 'author_id', 'file_id', 'file_type']
        if not all(field in cheatsheet for field in required_fields):
            await callback.answer("Ошибка данных шпаргалки", show_alert=True)
            return

        # Проверка баланса
        user_balance = db.get_user_balance(user_id)
        if user_balance < cheatsheet["price"]:
            await callback.answer(
                f"Недостаточно средств. Нужно: {cheatsheet['price']} руб. Ваш баланс: {user_balance} руб.",
                show_alert=True
            )
            return

        # Начинаем транзакцию
        try:
            # Списание средств у покупателя
            if not db.update_user_balance(user_id, -cheatsheet["price"]):
                raise Exception("Не удалось списать средства")

            # Начисление автору (если это не админ)
            if cheatsheet["author_id"] != config.ADMIN_ID:
                author_amount = round(cheatsheet["price"] * (1 - config.ADMIN_PERCENT), 2)
                if not db.update_user_balance(cheatsheet["author_id"], author_amount):
                    raise Exception("Не удалось начислить средства автору")

            # Начисление администратору
            admin_amount = round(cheatsheet["price"] * config.ADMIN_PERCENT, 2)
            if not db.update_user_balance(config.ADMIN_ID, admin_amount):
                raise Exception("Не удалось начислить средства администратору")

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

async def deposit_balance(message: types.Message):
    await reply_with_menu(
        message,
        "Для пополнения баланса:\n\n"
        "1. Переведите средства на наш счет\n"
        "2. Отправьте скриншот перевода администратору @Vld251\n"
        "3. После проверки ваш баланс будет пополнен"
    )

# Создадим клавиатуру для админа
def admin_balance_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True
    )

# Обработчик запроса на пополнение от пользователя
async def request_balance(message: types.Message):
    await message.answer(
        "Для пополнения баланса:\n"
        "1. Переведите средства\n"
        "2. Отправьте скриншот перевода и сумму администратору @Vld251",
        reply_markup=main_menu()
    )

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

def register_handlers(dp):
    # Команды
    router.message.register(cmd_start, Command("start"))
    router.message.register(cmd_help, Command("help"))
    
    # Меню
    router.message.register(search_cheatsheets, F.text == texts.SEARCH_CHEATSHEET)
    router.message.register(add_cheatsheet, F.text == texts.ADD_CHEATSHEET)
    router.message.register(show_user_cheatsheets, F.text == texts.MY_CHEATSHEETS)
    router.message.register(show_balance, F.text == texts.BALANCE)
    router.message.register(deposit_balance, F.text == texts.DEPOSIT)
    
    # Поиск шпаргалок
    router.callback_query.register(process_subject, F.data.startswith("subject_"), SearchCheatsheetStates.waiting_for_subject)
    router.callback_query.register(process_semester, F.data.startswith("semester_"), SearchCheatsheetStates.waiting_for_semester)
    router.callback_query.register(process_type, F.data.startswith("type_"), SearchCheatsheetStates.waiting_for_type)
    
    # Добавление шпаргалок
    router.callback_query.register(process_add_subject, F.data.startswith("subject_"), AddCheatsheetStates.waiting_for_subject)
    router.callback_query.register(process_add_semester, F.data.startswith("semester_"), AddCheatsheetStates.waiting_for_semester)
    router.callback_query.register(process_add_type, F.data.startswith("type_"), AddCheatsheetStates.waiting_for_type)
    router.message.register(process_name, AddCheatsheetStates.waiting_for_name)
    router.message.register(process_file, F.content_type.in_({'photo', 'document', 'text'}), AddCheatsheetStates.waiting_for_file)
    router.message.register(process_price, AddCheatsheetStates.waiting_for_price)
    
    # Пополнение баланса
    router.message.register(request_balance, F.text == texts.DEPOSIT)
    
    # Отмена
    router.callback_query.register(cancel_handler, F.data == "cancel", StateFilter('*'))
    
    # Покупка
    router.callback_query.register(buy_cheatsheet, F.data.startswith("buy_"))
    router.callback_query.register(buy_cheatsheet, F.data.startswith("free_"))
    
    # Админские команды
    router.message.register(admin_add_balance, Command("addbalance"))
    router.message.register(process_user_id, AddBalanceStates.waiting_for_user_id)
    router.message.register(process_amount, AddBalanceStates.waiting_for_amount)
    
    # Включаем роутер в диспетчер
    dp.include_router(router)