from aiogram import Router, F
from aiogram.filters import Command, StateFilter

from admin import approve_cheatsheet, reject_cheatsheet
from text import texts
from kb import *
from base_commands import *
from admin_commands import *
from states import *

# Создаем роутер
router = Router()


def register_handlers(dp):
    # Основные команды
    router.message.register(cmd_start, Command("start"))
    router.message.register(cmd_help, Command("help"))
    
    # Меню
    router.message.register(search_cheatsheets, F.text == texts.SEARCH_CHEATSHEET)
    router.message.register(add_cheatsheet, F.text == texts.ADD_CHEATSHEET)
    router.message.register(show_balance, F.text == texts.BALANCE)
    
    # Обратная связь
    router.message.register(request_feedback, F.text == texts.FEEDBACK)
    router.message.register(process_feedback, FeedbackStates.waiting_for_feedback)
    router.callback_query.register(handle_feedback_request, F.data.startswith("feedback_approve_"))
    router.callback_query.register(handle_feedback_request, F.data.startswith("feedback_reject_"))
    
    # Мои шпаргалки
    router.message.register(show_user_cheatsheets_menu, F.text == texts.MY_CHEATSHEETS)
    router.callback_query.register(process_my_subject, F.data.startswith("my_subject_"), MyCheatsheetsStates.waiting_for_subject)
    router.callback_query.register(process_my_semester, F.data.startswith("my_semester_"), MyCheatsheetsStates.waiting_for_semester)
    router.callback_query.register(process_my_type, F.data.startswith("my_type_"), MyCheatsheetsStates.waiting_for_type)
    
    # Обработчики "Назад" для "Моих шпаргалок"
    router.callback_query.register(my_back_to_subject, F.data == "my_back_to_subject")
    router.callback_query.register(my_back_to_semester, F.data == "my_back_to_semester")
    
    # Запросы на пополнение баланса
    router.message.register(request_balance, F.text == texts.DEPOSIT)
    router.message.register(process_balance_amount, BalanceRequestStates.waiting_for_amount)
    router.message.register(process_balance_proof, 
                            BalanceRequestStates.waiting_for_proof,
                            F.content_type.in_({'photo', 'document', 'text'}))
    
    # Вывод средств
    router.message.register(start_withdraw, F.text == texts.WITHDRAW)
    router.message.register(process_withdraw_amount, WithdrawStates.waiting_for_amount)
    router.message.register(process_withdraw_details, WithdrawStates.waiting_for_details)
    router.callback_query.register(handle_withdraw_request, F.data.startswith("withdraw_approve_"))
    router.callback_query.register(handle_withdraw_request, F.data.startswith("withdraw_reject_"))
    router.message.register(handle_balance_back, F.text == texts.BACK_BUTTON)
    
    # Поиск шпаргалок
    router.callback_query.register(process_subject, F.data.startswith("subject_"), SearchCheatsheetStates.waiting_for_subject)
    router.callback_query.register(process_semester, F.data.startswith("semester_"), SearchCheatsheetStates.waiting_for_semester)
    router.callback_query.register(process_type, F.data.startswith("type_"), SearchCheatsheetStates.waiting_for_type)
    
    router.callback_query.register(back_to_menu, F.data == "back_to_menu")
    router.callback_query.register(back_to_subject, F.data == "back_to_subject")
    router.callback_query.register(back_to_semester, F.data == "back_to_semester")
    
    # Добавление шпаргалок
    router.callback_query.register(process_add_subject, F.data.startswith("subject_"), AddCheatsheetStates.waiting_for_subject)
    router.callback_query.register(process_add_semester, F.data.startswith("add_semester_"), AddCheatsheetStates.waiting_for_semester)
    router.callback_query.register(process_add_type, F.data.startswith("add_type_"), AddCheatsheetStates.waiting_for_type)
    router.message.register(process_name, AddCheatsheetStates.waiting_for_name)
    router.message.register(process_file, F.content_type.in_({'photo', 'document', 'text'}), AddCheatsheetStates.waiting_for_file)
    router.message.register(process_price, AddCheatsheetStates.waiting_for_price)
    
    # Обработчики "Назад" для добавления шпаргалок
    router.callback_query.register(add_back_to_subject, F.data == "add_back_to_subject")
    router.callback_query.register(add_back_to_semester, F.data == "add_back_to_semester")
    router.callback_query.register(handle_cancel_balance, F.data.startswith("cancel_balance"), StateFilter(BalanceRequestStates))
    
    # Отмена
    router.callback_query.register(cancel_handler, F.data == "cancel", StateFilter('*'))
    router.callback_query.register(cancel_balance_request, F.data == "cancel", StateFilter(BalanceRequestStates))
    
    # Покупка
    router.callback_query.register(open_cheatsheet, F.data.startswith("open_"))
    router.callback_query.register(buy_cheatsheet, F.data.startswith("buy_"))
    router.callback_query.register(buy_cheatsheet, F.data.startswith("free_"))
    
    # Обработка запросов админом
    router.callback_query.register(handle_balance_request, F.data.startswith("balance_approve_"))
    router.callback_query.register(handle_balance_request, F.data.startswith("balance_reject_"))
    
    # Админские команды
    router.message.register(admin_add_balance, Command("addbalance"))
    router.message.register(process_user_id, AddBalanceStates.waiting_for_user_id)
    router.message.register(process_amount, AddBalanceStates.waiting_for_amount)
    
    router.callback_query.register(approve_cheatsheet, F.data.startswith("admin_approve:"))
    router.callback_query.register(reject_cheatsheet, F.data.startswith("admin_reject:"))
    
    # Включаем роутер в диспетчер
    dp.include_router(router)
