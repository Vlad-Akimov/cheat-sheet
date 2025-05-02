from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from text import texts
from kb import *
from db import db
from utils import is_valid_file_type, get_file_type, delete_previous_messages, reply_with_menu
from states import SearchCheatsheetStates, AddCheatsheetStates

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
    
    cheatsheets = db.get_cheatsheets(subject=data["subject"], semester=data["semester"], type_=type_)
    
    if not cheatsheets:
        await reply_with_menu(callback, texts.NO_CHEATSHEETS, delete_current=True)
        await state.clear()
        return
    
    for cheatsheet in cheatsheets:
        text = texts.CHEATSHEET_INFO.format(
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
            caption=f"Название: {data['name']}\n\n{admin_text}",
            reply_markup=admin_review_kb(cheatsheet_id)
        )
    elif data["file_type"] == "document":
        await message.bot.send_document(
            chat_id=config.ADMIN_ID,
            document=data["file_id"],
            caption=f"Название: {data['name']}\n\n{admin_text}",
            reply_markup=admin_review_kb(cheatsheet_id)
        )
    else:
        await message.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=f"Название: {data['name']}\n\n{admin_text}\n\nТекст шпаргалки:\n\n{data['file_id']}",
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
    cheatsheet_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    cheatsheet = db.get_cheatsheet(cheatsheet_id)
    if not cheatsheet:
        await reply_with_menu(callback, "Шпаргалка не найдена.", delete_current=True)
        return
    
    user_balance = db.get_user_balance(user_id)
    if user_balance < cheatsheet["price"]:
        await callback.answer(texts.NOT_ENOUGH_MONEY)
        return
    
    if cheatsheet["price"] == 0:
        if cheatsheet["file_type"] == "photo":
            await callback.message.answer_photo(cheatsheet["file_id"])
        elif cheatsheet["file_type"] == "document":
            await callback.message.answer_document(cheatsheet["file_id"])
        else:
            await callback.message.answer(cheatsheet["file_id"])
        
        await callback.answer()
        return
    
    db.update_user_balance(user_id, -cheatsheet["price"])
    author_amount = cheatsheet["price"] * (1 - config.ADMIN_PERCENT)
    db.update_user_balance(cheatsheet["author_id"], author_amount)
    admin_amount = cheatsheet["price"] * config.ADMIN_PERCENT
    db.update_user_balance(config.ADMIN_ID, admin_amount)
    db.add_purchase(user_id, cheatsheet_id, cheatsheet["price"])
    
    if cheatsheet["file_type"] == "photo":
        await callback.message.answer_photo(
            cheatsheet["file_id"],
            caption=texts.PURCHASE_SUCCESS,
            reply_markup=main_menu()
        )
    elif cheatsheet["file_type"] == "document":
        await callback.message.answer_document(
            cheatsheet["file_id"],
            caption=texts.PURCHASE_SUCCESS,
            reply_markup=main_menu()
        )
    else:
        await callback.message.answer(
            f"{texts.PURCHASE_SUCCESS}\n\n{cheatsheet['file_id']}",
            reply_markup=main_menu()
        )
    
    await callback.message.delete()
    await callback.answer()

async def deposit_balance(message: types.Message):
    await reply_with_menu(
        message,
        "Для пополнения баланса:\n\n"
        "1. Переведите средства на наш счет\n"
        "2. Отправьте скриншот перевода администратору @Vld251\n"
        "3. После проверки ваш баланс будет пополнен"
    )

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
    
    # Отмена
    router.callback_query.register(cancel_handler, F.data == "cancel", StateFilter('*'))
    
    # Покупка
    router.callback_query.register(buy_cheatsheet, F.data.startswith("buy_"))
    router.callback_query.register(buy_cheatsheet, F.data.startswith("free_"))
    
    # Включаем роутер в диспетчер
    dp.include_router(router)