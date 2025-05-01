from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from text import texts

# Главное меню
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.SEARCH_CHEATSHEET)],
            [KeyboardButton(text=texts.ADD_CHEATSHEET), KeyboardButton(text=texts.MY_CHEATSHEETS)],
            [KeyboardButton(text=texts.BALANCE), KeyboardButton(text=texts.DEPOSIT)]
        ],
        resize_keyboard=True
    )

# Клавиатура для выбора предмета
def subjects_kb(subjects: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for subject in subjects:
        builder.button(text=subject, callback_data=f"subject_{subject}")
    builder.adjust(2)  # 2 кнопки в ряду
    return builder.as_markup()

# Клавиатура для выбора семестра
def semesters_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 9):
        builder.button(text=str(i), callback_data=f"semester_{i}")
    builder.adjust(4)  # 4 кнопки в ряду
    return builder.as_markup()

# Клавиатура для выбора типа шпаргалки
def types_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Формулы", callback_data="type_formulas")
    builder.button(text="Теория", callback_data="type_theory")
    builder.adjust(2)  # 2 кнопки в ряду
    return builder.as_markup()

# Кнопка отмены
def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()

# Кнопки модерации для админа
def admin_review_kb(cheatsheet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.APPROVE_BUTTON, callback_data=f"approve_{cheatsheet_id}")
    builder.button(text=texts.REJECT_BUTTON, callback_data=f"reject_{cheatsheet_id}")
    builder.adjust(2)  # 2 кнопки в ряду
    return builder.as_markup()

# Кнопка покупки
def buy_kb(cheatsheet_id: int, price: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.BUY_BUTTON.format(price=price),
        callback_data=f"buy_{cheatsheet_id}"
    )
    return builder.as_markup()

# Кнопка для бесплатной шпаргалки
def free_kb(file_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=texts.FREE_ACCESS,
        callback_data=f"free_{file_id}"
    )
    return builder.as_markup()