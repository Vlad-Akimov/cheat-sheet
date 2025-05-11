from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

def back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BACK_BUTTON, callback_data="back_to_menu")
    return builder.as_markup()

# Клавиатура для выбора предмета
def subjects_kb(subjects: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for subject in subjects:
        builder.button(text=subject, callback_data=f"subject_{subject}")
    builder.adjust(2)
    
    # Добавляем кнопку отмены отдельным рядом
    builder.row(InlineKeyboardButton(
        text=texts.CANCEL_SEARCH,
        callback_data="back_to_menu"
    ))
    
    return builder.as_markup()

# Клавиатура для выбора семестра
def semesters_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 9):
        builder.button(text=str(i), callback_data=f"semester_{i}")
    builder.button(text=texts.BACK_BUTTON, callback_data="back_to_subject")
    builder.button(text=texts.CANCEL_SEARCH, callback_data="back_to_menu")
    builder.adjust(4, 4, 2)  # 4 кнопки в первых двух рядах, затем кнопки "Назад" и "Отмена"
    return builder.as_markup()

def types_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Формулы", callback_data="type_formulas")
    builder.button(text="Теория", callback_data="type_theory")
    builder.button(text=texts.BACK_BUTTON, callback_data="back_to_semester")
    builder.button(text=texts.CANCEL_SEARCH, callback_data="back_to_menu")
    builder.adjust(2, 2)  # 2 кнопки в ряду
    return builder.as_markup()

# Кнопка отмены
def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()

# Кнопки модерации для админа
def admin_review_kb(cheatsheet_id: int) -> InlineKeyboardMarkup:
    print(cheatsheet_id)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Изменить название", 
        callback_data=f"edit_name:{cheatsheet_id}"
    )
    builder.button(
        text=texts.APPROVE_BUTTON, 
        callback_data=f"approve:{cheatsheet_id}"
    )
    builder.button(
        text=texts.REJECT_BUTTON, 
        callback_data=f"reject:{cheatsheet_id}"
    )
    builder.adjust(1, 2)
    return builder.as_markup()

def admin_back_kb(cheatsheet_id: int) -> InlineKeyboardMarkup:
    print(cheatsheet_id)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Назад к редактированию", 
        callback_data=f"back_edit:{cheatsheet_id}"
    )
    return builder.as_markup()

# Создадим клавиатуру для админа
def admin_balance_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts.CANCEL_BUTTON)],
        ],
        resize_keyboard=True
    )

def admin_edit_name_kb(cheatsheet_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Изменить название", 
        callback_data=f"edit_{cheatsheet_id}"
    )
    builder.button(
        text=texts.APPROVE_BUTTON, 
        callback_data=f"approve_{cheatsheet_id}"
    )
    builder.button(
        text=texts.REJECT_BUTTON, 
        callback_data=f"reject_{cheatsheet_id}"
    )
    builder.adjust(1, 2)
    return builder.as_markup()

def admin_edit_name_back_kb(cheatsheet_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад' при изменении названия"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Назад к редактированию", 
        callback_data=f"back_to_edit_{cheatsheet_id}"
    )
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

def my_cheatsheet_kb(cheatsheet: dict) -> InlineKeyboardMarkup:
    """Клавиатура для шпаргалки в разделе 'Мои шпаргалки'"""
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="📄 Открыть", 
        callback_data=f"open_{cheatsheet['id']}"
    )
    
    return builder.as_markup()

def types_kb_for_my_cheatsheets() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа в разделе 'Мои шпаргалки'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Формулы", callback_data="my_type_formulas")
    builder.button(text="Теория", callback_data="my_type_theory")
    builder.button(text=texts.BACK_BUTTON, callback_data="my_back_to_semester")
    builder.button(text=texts.CANCEL_SEARCH, callback_data="back_to_menu")
    builder.adjust(2, 2)
    return builder.as_markup()

def semesters_kb_for_my_cheatsheets() -> InlineKeyboardMarkup:
    """Клавиатура для выбора семестра в разделе 'Мои шпаргалки'"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 9):
        builder.button(text=str(i), callback_data=f"my_semester_{i}")
    builder.button(text=texts.BACK_BUTTON, callback_data="my_back_to_subject")
    builder.button(text=texts.CANCEL_SEARCH, callback_data="back_to_menu")
    builder.adjust(4, 4, 2)
    return builder.as_markup()